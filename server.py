import TrackNet_pb2
import TrackNet_pb2 as proto
import logging
import socket
import signal
import threading
from utils import *
from  classes.enums import *
from classes.railway import Railway
from classes.train import Train
import traceback
from datetime import datetime, timedelta
import time
import threading
from utils import initial_config, proxy_details
from message_converter import MessageConverter
from classes.conflict_analyzer import ConflictAnalyzer
import argparse
import traceback


# Global Variables
proxy1_address = None
proxy2_address = None
proxy1_port_num = None
proxy2_port_num = None
listening_port_num = None

proxyDetailsProvided = False
cmdLineProxyDetails = {}

setup_logging() ## only need to call at main entry point of application

LOGGER = logging.getLogger("Server")


#signal.signal(signal.SIGTERM, exit_gracefully)
#signal.signal(signal.SIGINT, exit_gracefully)

# Slave server
class Server():

	def __init__(self, host: str ="localhost", port: int =5555):
		"""A server class that manages train objects and handles network connections.

		:param host: The hostname or IP address to listen on.
		:param port: The port number to listen on.
		:ivar host: Hostname or IP address of the server.
		:ivar port: Port number on which the server listens.
		:ivar sock: Socket object for the server. Initially set to None.
		:ivar trains: A list of Train objects managed by the server.
		:ivar train_counter: A counter to assign unique IDs to trains.
		"""

		self.railway = Railway(
			trains=None,
			junctions=initial_config["junctions"],
			tracks=initial_config["tracks"]
		)

		self.host = socket.gethostname()
		self.port = port

		self.connected_to_master = False
		self.is_master = False
		self.slave_sockets = {}
		self.proxy_sockets = {}
		self.socks_for_communicating_to_slaves = []

		self.isMaster = False
		self.proxy_host = "csx1.ucalgary.ca"
		self.proxy_port = 5555

		self.conflict_analysis_interval = 1
		
		self.previous_conflict_analysis_time = datetime.now()
		self.client_commands = {}

		self.connect_to_proxy()

		# Warning: this section of code is unreachable because self.connect_to_proxy() does not exit


	def serialize_route(self, route_obj, route_pb):
		"""Fills in the details of a Protobuf Route message from a Route object."""
		for junction in route_obj.junctions:
			junction_pb = route_pb.junctions.add()
			junction_pb.id = junction.name
		route_pb.current_junction_index = route_obj.current_junction_index
		if route_obj.destination:
			route_pb.destination.id = route_obj.destination.name

	def serialize_location(self, location_obj, location_pb):
		"""Fills in the details of a Protobuf Location message from a Location object."""
		if location_obj.front_cart["track"]:
			location_pb.front_track_id = location_obj.front_cart["track"].name
		if location_obj.front_cart["junction"]:
			location_pb.front_junction_id = location_obj.front_cart["junction"].name
		location_pb.front_position = location_obj.front_cart["position"]

		if location_obj.back_cart["track"]:
			location_pb.back_track_id = location_obj.back_cart["track"].name
		if location_obj.back_cart["junction"]:
			location_pb.back_junction_id = location_obj.back_cart["junction"].name
		location_pb.back_position = location_obj.back_cart["position"]

	def serialize_train(self, train_obj, train_pb):
		"""Fills in the details of a Protobuf Train message from a Train object."""
		train_pb.id = train_obj.name
		train_pb.length = train_obj.length
		train_pb.state = train_obj.state.value
		train_pb.speed = train_obj.current_speed

		# Serialize the train's Location
		if train_obj.location:
			self.serialize_location(train_obj.location, train_pb.location)

		# Serialize the train's Route
		if train_obj.route:
			self.serialize_route(train_obj.route, train_pb.route)

	def create_railway_update_message(self) -> TrackNet_pb2.RailwayUpdate:
		railway_update = TrackNet_pb2.RailwayUpdate()
		railway_update.timestamp = datetime.utcnow().isoformat()

		# Serialize the state of Junctions and Tracks in the RailMap
		for junction_name, junction_obj in self.railway.map.junctions.items():
			junction_pb = railway_update.railway.map.junctions[junction_name]
			junction_pb.id = junction_name
			# Note: You may need to serialize other properties of the Junction here

		for track_id, track_obj in self.railway.map.tracks.items():
			track_pb = railway_update.railway.map.tracks[track_id]
			track_pb.id = track_id
			track_pb.junction_a = track_obj.junctions[0].name
			track_pb.junction_b = track_obj.junctions[1].name
			track_pb.condition = track_obj.condition.value
			track_pb.speed = track_obj.speed
			# Note: You may need to serialize other properties of the Track here

		# Serialize Trains
		for train_name, train_obj in self.railway.trains.items():
			train_pb = railway_update.railway.trains[train_name]
			self.serialize_train(train_obj, train_pb)

		railway_update.railway.train_counter = self.railway.train_counter

		LOGGER.debug("Railway update message created")
		return railway_update

	def get_train(self, train: TrackNet_pb2.Train, origin_id: str):
		"""Retrieves a Train object based on its ID. If the train does not exist, it creates a new Train object.

		:param train: The train identifier or a Train object with an unset ID to create a new Train.
		:return: Returns the Train object matching the given ID, or a new Train object if the ID is not set.
		:raises Exception: Logs an error if the train ID does not exist in the list of trains.
		"""
		if not train.HasField("id"):
			trainObject =  self.railway.create_new_train(train.length, origin_id)
			train.id = trainObject.name
			return trainObject
		else:
			try:
				train = self.railway.trains[train.id]
			except:
				LOGGER.error(f"Train {train.id} does not exits in list of trains. Creating new train...")
				return self.railway.create_new_train(train.length, origin_id)

			return train

	def apply_client_state(self, client_state, train):
		# assume client_state location is set
		
		# check train condition
		if client_state.location.HasField("front_track_id"):
			self.railway.map.set_track_condition(client_state.location.front_track_id, TrackCondition(client_state.condition))

		# update train location
		location_obj = MessageConverter.location_msg_to_obj(client_state.location)
		route_obj = MessageConverter.route_msg_to_obj(client_state.route)
		self.railway.update_train(train, TrainState(client_state.train.state), location_obj, route_obj)

		# print map
		self.railway.print_map()


	def issue_client_command(self, client_state, train):
		
		resp = TrackNet_pb2.ServerResponse()
		resp.train.id            = train.name
		resp.train.length        = train.length
		resp.client.CopyFrom(client_state.client)
		LOGGER.debug(f"trains speed being set to {TrainSpeed.FAST.value}")
		resp.speed = TrainSpeed.FAST.value
		resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR

		if (datetime.now() - self.previous_conflict_analysis_time) > timedelta(seconds=self.conflict_analysis_interval):
			self.client_commands = ConflictAnalyzer.resolve_conflicts(self.railway, self.client_commands)
			self.previous_conflict_analysis_time = datetime.now()

		command = self.client_commands[train.name]
		resp.status = command.status
		if command.HasField("new_route"):
			resp.new_route = command.new_route
		if command.HasField("speed"):
			resp.speed = command.speed
		
		LOGGER.debug(f"speed command {resp.train.id}: {resp.speed}")

		return resp
		
		
	def set_slave_identification_msg(self, slave_identification_msg: TrackNet_pb2.InitConnection):
		slave_identification_msg.sender = TrackNet_pb2.InitConnection.SERVER_SLAVE
		slave_identification_msg.slave_details.host = self.host
		slave_identification_msg.slave_details.port = slave_to_master_port


	def talk_to_slaves_old(self):
		"""Sends railway update  message to slaves """
		LOGGER.info(f"Sending backups to slaves")
		LOGGER.debug(f"number of slaves: {len(self.slave_sockets)}")
		for _ , slave_socket in self.slave_sockets.items():
			# Prepare the client state message
			print("HERE")
			master_resp = TrackNet_pb2.InitConnection()
			master_resp.sender = TrackNet_pb2.InitConnection.SERVER_MASTER
			master_resp.railway_update.CopyFrom(MessageConverter.railway_obj_and_ts_to_railway_update_msg(self.railway,datetime.utcnow().isoformat()))
			print(master_resp)

			if not send(slave_socket, master_resp.SerializeToString()):
				LOGGER.warning(f"Railway update message failed to sent to slave")

	def connect_to_slave_old(self, slave_host, slave_port):
		LOGGER.info("Master connecting to the new slave")
		try:
			# for each slave create client sockets
			slave_sock = create_client_socket(slave_host, slave_port)
			self.slave_sockets[f"{slave_host}:{slave_port}"] = slave_sock
			LOGGER.debug (f"Added slave server {slave_host}:{slave_port}")
			# Start a new thread dedicated to this slave for communication
			# threading.Thread(target=self.handle_slave_communication, args=(slave_sock,), daemon=True).start()

		except Exception as e:
			LOGGER.error(f"Could not connect to slave {slave_host}:{slave_port}: {e}")

	def listen_for_master(self, host, port):
		slave_to_master_sock = create_server_socket(host, port)
		LOGGER.debug("Slave created listening socket, waiting for master backups")

		if slave_to_master_sock is None:
			LOGGER.warning("Slave failed to create listening socket for master.")
			return

		while not exit_flag:
			try:
				conn, addr = slave_to_master_sock.accept()
				self.connected_to_master = True
				LOGGER.debug("Master has connected to slave server, listening for updates...")
				threading.Thread(target=self.handle_master_communication, args=(conn,), daemon=True).start()

			except socket.timeout:
				continue  # Just continue listening without taking action

			except Exception as exc:
				LOGGER.error("listen_to_master: " + str(exc))
				slave_to_master_sock.shutdown(socket.SHUT_RDWR)
				slave_to_master_sock.close()
				LOGGER.info("Restarting listening socket...")
				slave_to_master_sock = create_server_socket(self.host, self.port)

	def handle_master_communication(self, conn):
		try:
			while self.connected_to_master:
				try:
					data = receive(conn)  # Adjust buffer size as needed
					if data:
						master_resp = TrackNet_pb2.InitConnection()
						master_resp.ParseFromString(data)
						# Check if sender is master
						if master_resp.sender == TrackNet_pb2.InitConnection.SERVER_MASTER and master_resp.HasField("railway_update"):
							LOGGER.debug(f"Slave received a backup form the master: {master_resp.railway_update}")
							# need to store the backup
							LOGGER.debug(f"Received railway update from master at {master_resp.railway_update.timestamp}")
				except socket.timeout:
					continue  # No data received within the timeout, continue loop
				except Exception as e:
					LOGGER.error(f"Error communicating with master: {e}")
					print ("Setting connected to master to false")
					self.connected_to_master = False # Reset the flag to allow for a new connection
					break  # Break out of the loop on any other exception
		finally:
			LOGGER.debug("Closing connection to master")
			conn.close()


	def slave_proxy_communication(self, data):
		LOGGER.debug("slave recieved message from proxy")
		proxy_resp = TrackNet_pb2.ServerAssignment()
		proxy_resp.ParseFromString(data)
		LOGGER.debug(f"Slave received role assignment from proxy: {proxy_resp}")

		# Determine if this server has been assigned as the master
		if proxy_resp.HasField("is_master"):
			if proxy_resp.is_master:
				LOGGER.info(f"{self.host}:{self.port} promoted to the MASTER")
				#self.promote_to_master()
				self.is_master = True

				for slave in proxy_resp.servers:
					slave_host = slave.host
					slave_port = slave.port
					LOGGER.debug ( f"Slave host: {slave_host}, Slave port: {slave_port}")
					# connect to slave in separate thread
					LOGGER.debug ("Connecting to slave")
					self.connect_to_slave(slave_host, slave_port)

			else:
				LOGGER.info(f"{self.host}:{self.port} designated as a SLAVE.")
				self.is_master = False
				# Connect to master if not already
				if not self.connected_to_master:
					# listen to master instead of initiating connection
					#self.listen_for_master(self.host, 4444)
					threading.Thread(target=self.listen_for_master, args=(self.host, 4444)).start()

	def master_proxy_communication(self, sock, data):
		# Data also needs to include an update of a new slave
		proxy_resp = TrackNet_pb2.InitConnection()
		proxy_resp.ParseFromString(data)
		#LOGGER.debug(f"Master server received response from proxy\n{proxy_resp}")

		# Receive updates on new slaves connecting to the proxy
		#if len(proxy_resp.slave_details) > 0:
		#    for slave_details in proxy_resp.slave_details:
		#        slave_key = f"{slave_details.ip}:{slave_details.port}"
		#        # check if connection to slave already exists
		#        if slave_key not in self.slave_sockets or self.slave_sockets[slave_key] is None:
		#            self.connect_to_slave(slave_details.ip, slave_details.port)

		if proxy_resp.HasField("slave_details"):
			LOGGER.debug ("Received slave server details from proxy")
			slave_host = proxy_resp.slave_details.host
			slave_port = proxy_resp.slave_details.port
			LOGGER.debug ( f"Slave host: {slave_host}, Slave port: {slave_port}")
			# connect to slave in separate thread
			self.connect_to_slave(slave_host, slave_port)


		# listen on proxy sock for client states
		elif proxy_resp.HasField("client_state"):
			resp = self.handle_client_state(proxy_resp.client_state)
			master_response = TrackNet_pb2.InitConnection()
			master_response.sender = TrackNet_pb2.InitConnection.Sender.SERVER_MASTER
			master_response.server_response.CopyFrom(resp)
			print(master_response)

			if not send(sock, master_response.SerializeToString()):
				LOGGER.warning(f"ServerResponse message failed to send to proxy.")
			else:
				print("sent server response to proxy")

			# Create a separate thread for talking to slaves
			threading.Thread(target=self.talk_to_slaves, daemon=True).start()


		#CHECK FOR HEARTBEAT HERE
		elif proxy_resp.HasField("is_heartbeat"):
			#LOGGER.debug(f"Received heartbeat from proxy: {proxy_resp.is_heartbeat}")
			heartbeat_message = proto.InitConnection()
			heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.SERVER_MASTER
			heartbeat_message.is_heartbeat = True
			if not send(sock, heartbeat_message.SerializeToString()):
				LOGGER.warning("Failed to send heartbeat message to main proxy.")

		else:
			LOGGER.warning(f"Server received msg from proxy with missing content: {proxy_resp}")

	def listen_to_proxy(self, proxy_sock):
		try:
			while True:
				data = receive(proxy_sock)
				if data: # split data into 3 difrerent types of messages, a heartbeat, a clientstate or a ServerAssignment
					# Master server responsibilitites
					if self.is_master:
						self.master_proxy_communication(proxy_sock, data)

					# Slave server responsibilities
					else:
						self.slave_proxy_communication(data)

		except Exception as e:
			LOGGER.error(f"Error communicating with proxy: {e}, {traceback.format_exc()}")
			proxy_sock.shutdown(socket.SHUT_RDWR)
			proxy_sock.close()


	def connect_to_proxy(self):
		while not exit_flag:
			if proxyDetailsProvided:
				for proxy_host, proxy_port in cmdLineProxyDetails.items():
					key = f"{proxy_host}:{proxy_port}"
					if key not in self.proxy_sockets or self.proxy_sockets[key] is None:
						LOGGER.info(f"Connecting to proxy at {proxy_host}:{proxy_port}")
						proxy_sock = create_client_socket(proxy_host, proxy_port)

						if proxy_sock:
							LOGGER.info(f"Connected to proxy at {proxy_host}:{proxy_port}")
							self.proxy_sockets[key] = cmdLineProxyDetails
							# Send proxy init message to identify itself as a slave
							slave_identification_msg = TrackNet_pb2.InitConnection()
							self.set_slave_identification_msg(slave_identification_msg)

							if send(proxy_sock, slave_identification_msg.SerializeToString()):
								LOGGER.debug("Sent slave identification message to proxy")
								threading.Thread(target=self.listen_to_proxy, args=(proxy_sock,), daemon=True).start()
						else:
							LOGGER.warning(f"Couldn't connect to proxy at {proxy_host}:{proxy_port}")
				time.sleep(10)
			else:
				for proxy_host, proxy_port in proxy_details.items():
					key = f"{proxy_host}:{proxy_port}"
					if key not in self.proxy_sockets or self.proxy_sockets[key] is None:
						LOGGER.info(f"Connecting to proxy at {proxy_host}:{proxy_port}")
						proxy_sock = create_client_socket(proxy_host, proxy_port)

						if proxy_sock:
							LOGGER.info(f"Connected to proxy at {proxy_host}:{proxy_port}")
							self.proxy_sockets[key] = proxy_details
							# Send proxy init message to identify itself as a slave
							slave_identification_msg = TrackNet_pb2.InitConnection()
							self.set_slave_identification_msg(slave_identification_msg)

							if send(proxy_sock, slave_identification_msg.SerializeToString()):
								LOGGER.debug("Sent slave identification message to proxy")
								threading.Thread(target=self.listen_to_proxy, args=(proxy_sock,), daemon=True).start()
						else:
							LOGGER.warning(f"Couldn't connect to proxy at {proxy_host}:{proxy_port}")
				time.sleep(10)

	def connect_to_slave (self, slave_host, slave_port):
		try:
			# for each slave create client sockets
			print ("Before creating client socket, host: ", slave_host)
			slave_sock = create_client_socket(slave_host, 4444)
			print ("Type of slave sock: ", type(slave_sock))
			self.socks_for_communicating_to_slaves.append(slave_sock)
			LOGGER.debug (f"Added slave server {slave_host}:{slave_port}")
			# Start a new thread dedicated to this slave for communication
			# threading.Thread(target=self.handle_slave_communication, args=(slave_sock,), daemon=True).start()
		except Exception as e:
			LOGGER.error(f"Could not connect to slave {slave_host}:{slave_port}: {e}")


	def serialize_train(self, train_obj, train_pb):
		"""
		Fills in the details of a Protobuf Train message from a Train object.
		"""
		train_pb.id = train_obj.name
		train_pb.length = train_obj.length
		train_pb.state = train_obj.state.value
		train_pb.speed = train_obj.current_speed

		# Serialize the train's Location
		if train_obj.location:
			self.serialize_location(train_obj.location, train_pb.location)

		# Serialize the train's Route
		if train_obj.route:
			self.serialize_route(train_obj.route, train_pb.route)

	def serialize_location(self, location_obj, location_pb):
		"""
		Fills in the details of a Protobuf Location message from a Location object.
		"""
		if location_obj.front_cart["track"]:
			location_pb.front_track_id = location_obj.front_cart["track"].name
		if location_obj.front_cart["junction"]:
			location_pb.front_junction_id = location_obj.front_cart["junction"].name
		location_pb.front_position = location_obj.front_cart["position"]

		if location_obj.back_cart["track"]:
			location_pb.back_track_id = location_obj.back_cart["track"].name
		if location_obj.back_cart["junction"]:
			location_pb.back_junction_id = location_obj.back_cart["junction"].name
		location_pb.back_position = location_obj.back_cart["position"]

	def serialize_route(self, route_obj, route_pb):
		"""
		Fills in the details of a Protobuf Route message from a Route object.
		"""
		for junction in route_obj.junctions:
			junction_pb = route_pb.junctions.add()
			junction_pb.id = junction.name
		route_pb.current_junction_index = route_obj.current_junction_index
		if route_obj.destination:
			route_pb.destination.id = route_obj.destination.name

	def create_railway_update_message(self):
		railway_update = TrackNet_pb2.RailwayUpdate()
		railway_update.timestamp = datetime.utcnow().isoformat()

		# Serialize the state of Junctions and Tracks in the RailMap
		for junction_name, junction_obj in self.railway.map.junctions.items():
			junction_pb = railway_update.railway.map.junctions[junction_name]
			junction_pb.id = junction_name
			# Note: You may need to serialize other properties of the Junction here

		for track_id, track_obj in self.railway.map.tracks.items():
			track_pb = railway_update.railway.map.tracks[track_id]
			track_pb.id = track_id
			track_pb.junction_a = track_obj.junctions[0].name
			track_pb.junction_b = track_obj.junctions[1].name
			track_pb.condition = track_obj.condition.value
			track_pb.speed = track_obj.speed
			# Note: You may need to serialize other properties of the Track here

		# Serialize Trains
		for train_name, train_obj in self.railway.trains.items():
			train_pb = railway_update.railway.trains[train_name]
			self.serialize_train(train_obj, train_pb)

		railway_update.railway.train_counter = self.railway.train_counter


		return railway_update

	def talk_to_slaves(self): # needs to send railway update to slaves
		print(f"number of slaves: {len(self.socks_for_communicating_to_slaves)}")
		for slave_socket in self.socks_for_communicating_to_slaves:
			# Prepare the client state message
			master_resp = TrackNet_pb2.InitConnection()
			master_resp.sender = TrackNet_pb2.InitConnection.SERVER_MASTER
			#master_resp.railway_update.CopyFrom(self.create_railway_update_message())
			print("Railway update message created")
			print ("type of slave socket: ", type(slave_socket))
			success = send(slave_socket, master_resp.SerializeToString())
			print(f"Railway update message sent to slave successfully: {success}")

	def listen_to_master (self, host, port):
		self.sock_for_communicating_to_master = create_server_socket(host, port)
		LOGGER.debug ("Created server socket for slave, waiting for master backups ")

		while not exit_flag and self.sock_for_communicating_to_master:
			try:
				conn, addr = self.sock_for_communicating_to_master.accept()
				self.connected_to_master = True
				LOGGER.debug("Master has connected to slave server, listening for updates...")
				threading.Thread(target=self.handle_master_communication, args=(conn,), daemon=True).start()

			except socket.timeout:
				continue  # Just continue listening without taking action

			except Exception as exc:
				LOGGER.error("listen_to_master: " + str(exc))
				self.sock_for_communicating_to_master.close()
				LOGGER.info("Restarting listening socket...")
				self.sock_for_communicating_to_master = create_server_socket(self.host, self.port)


	def handle_master_communication (self, conn):
		try:
			while self.connected_to_master:
				data = receive(conn)
				if data:
					master_resp = TrackNet_pb2.InitConnection()
					master_resp.ParseFromString(data)
					print("data received at slave")
					#Check if sender is master
					if master_resp.sender == TrackNet_pb2.InitConnection.SERVER_MASTER and master_resp.HasField("railway_update"):
						print(f"Received a backup form the master: {master_resp.railway_update}")
						# need to store the backup
						LOGGER.debug(f"Received railway update from master at {master_resp.railway_update.timestamp}")
		except Exception as e:
			LOGGER.error(f"Error communicating with master: {e}")
		finally:
			conn.close()
			self.connected_to_master = False #Reset the flag to allow for a new connection


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Process Server args")

	parser.add_argument('-proxy1', type=str, help='Address for proxy1')
	parser.add_argument('-proxy2', type=str, help='Address for proxy2')
	parser.add_argument('-proxyPort1', type=int, help='Proxy 1 port number')
	parser.add_argument('-proxyPort2', type=int, help='Proxy 2 port number')
	parser.add_argument('-listeningPort', type=int, help='Listening port number', default=4444)

	args = parser.parse_args()

	proxy1_address = args.proxy1
	proxy2_address = args.proxy2
	proxy1_port_num = args.proxyPort1
	proxy2_port_num = args.proxyPort2
	listening_port_num = args.listeningPort

	LOGGER.debug(f"Proxy 1 address {proxy1_address}")
	LOGGER.debug(f"Proxy 2 address {proxy2_address}")
	LOGGER.debug(f"Proxy 1 port number {proxy1_port_num}")
	LOGGER.debug(f"Proxy 2 port number {proxy2_port_num}")
	LOGGER.debug(f"Listening port {listening_port_num}")

	if proxy1_port_num == None:
		proxy1_port_num =5555
	
	if proxy2_port_num == None:
		proxy2_port_num = 5555 

	if proxy1_address == None and proxy2_address == None:
		#use proxydetails
		proxyDetailsProvided = False
		LOGGER.debug(f"Proxy details not provided, will use util values")
	else:
		proxyDetailsProvided = True
		LOGGER.debug(f"Proxy details provided, Proxy 1: {proxy1_address}:{proxy1_port_num} and Proxy 2: {proxy2_address}:{proxy2_port_num}")
		if proxy1_address != None:
			cmdLineProxyDetails[proxy1_address] = proxy1_port_num
		if proxy2_address != None:
			cmdLineProxyDetails[proxy2_address] = proxy2_port_num

	Server(port=listening_port_num)
