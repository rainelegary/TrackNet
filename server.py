import hashlib
import os
import TrackNet_pb2
import TrackNet_pb2 as proto
import logging
import socket
import signal
import threading
from utils import *
from classes.enums import *
from classes.railway import Railway
from classes.train import Train
import traceback
from datetime import datetime, timedelta
import time
import threading
from utils import initial_config, proxy_details
import utils
from classes.conflict_analyzer import ConflictAnalyzer
import argparse
from converters.railway_converter import RailwayConverter
from message_converter import MessageConverter
import sys
from queue import Queue

from google.protobuf.message import Message
# Global Variables
proxy1_address = None
proxy2_address = None
proxy1_port_num = None
proxy2_port_num = None
listening_port_num = None

proxyDetailsProvided = False
cmdLineProxyDetails = []

setup_logging()  ## only need to call at main entry point of application

LOGGER = logging.getLogger("UnAssignedServer")


signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)


class Server:
	""" Manages train objects and network connections for a railway simulation server. This class is responsible for handling incoming client connections, processing train state updates, and managing the railway network's state.

	Attributes
    ----------
   	host : str
      The hostname or IP address the server listens on. Defaults to the machine's hostname.

   	port : int
      The port number the server listens on. Defaults to 5555.

   	sock : socket.socket
      The main socket object for the server. Used to accept incoming connections.

	railway : Railway
      An instance of the Railway class, representing the server's simulation of the railway network.

  	is_master : bool
      A flag indicating whether this server instance is operating as the master server.
	"""

	def __init__(self, host: str = "localhost", port: int = 5555):
		"""Initializes the server instance with the specified host and port. 
		Sets up the railway simulation and starts threads for managing network 
		connections and processing client updates.

      	:param host: The hostname or IP address to listen on.
      	:param port: The port number to listen on.
		"""
		self.railway = Railway(
			trains=None,
			junctions=initial_config["junctions"],
			tracks=initial_config["tracks"],
		)

		self.host = socket.gethostname()
		self.port = port
		

		self.lock = threading.Lock()

		self.connected_to_master = False
		self.is_master = False
		self.slave_sockets = {}
		self.proxy_sockets = {}
		self.socks_for_communicating_to_slaves = []
		
		self.connecting_to_proxies = False
		self.isMaster = False
		self.proxy_host = "csx1.ucalgary.ca"
		self.proxy_port = 5555

		self.conflict_analysis_interval = 1
		self.previous_conflict_analysis_time = datetime.now() - timedelta(seconds=self.conflict_analysis_interval)
		self.client_commands = {}

		self.backup_railway_timestamp = None
		self.backup_railway = None
		self.handled_client_states = {}
		
		self.client_state_queue = Queue()

		self.listening_for_backups = threading.Thread(target=self.listen_for_master, args=(self.host, self.port), daemon=True)
		self.listening_for_backups.start() # will start thread for listening for master backup

		threading.Thread(target=self.connect_to_proxy, daemon=True).start()
		threading.Thread(target=self.printRailwayMapold, daemon=True).start()

		#self.window = None
		# LOGGER.debug(f" Time {time.time()} ")
		# timeobj = time.time()
		# LOGGER.debug(f" Time {timeobj} conversion to readable: { datetime.fromtimestamp(timeobj).strftime('%Y-%m-%d %H:%M:%S') }")
		
		
		self.handle_client_states()

	def printRailwayMapold(self):
		while not utils.exit_flag:
			time.sleep(5)
			if self.is_master == True:
				text = "----------------------------------------------------------------------\n"
				text += "Printing State of Railway: \n"
				text += self.railway.get_map_string()
				text += "----------------------------------------------------------------------\n"
				LOGGER.debug(text)

			
	def create_railway_update_message(self) -> TrackNet_pb2.RailwayUpdate:
		"""Creates and returns a RailwayUpdate message containing the current 
		state of the railway network.

      	:return: A RailwayUpdate protobuf message.
		"""
		railway_update = TrackNet_pb2.RailwayUpdate()
		railway_update.timestamp = time.time()
		railway_update.railway.CopyFrom(RailwayConverter.convert_railway_obj_to_pb(self.railway))
		
		for train_id, (client_state_hash, server_response) in self.handled_client_states.items():
			# Creating a new LastHandledClientState protobuf message
			last_handled_client_state = TrackNet_pb2.LastHandledClientState()
			last_handled_client_state.train_id = train_id
			last_handled_client_state.client_state_hash = client_state_hash
			last_handled_client_state.serverResponse.CopyFrom(server_response)
			
			# Adding the LastHandledClientState to the list in RailwayUpdate
			railway_update.last_handled_client_states.add().CopyFrom(last_handled_client_state)
		
		return railway_update

	def get_train(self, train: TrackNet_pb2.Train, origin_id: str):
		"""Retrieves or creates a Train object based on the provided protobuf Train message.

		:param train: A protobuf message representing the train.
		:param origin_id: The ID of the train's origin junction.
		:return: A TrainMovement object representing the train.
		"""
		if not train.HasField("id"):
			LOGGER.debug("No id in client state, will create a new train: ")
			trainObject = self.railway.create_new_train(train.length, origin_id)
			train.id = trainObject.name

			return trainObject
		
		else:
			try:
				train = self.railway.trains[train.id]
			except:
				LOGGER.error(f"Train {train.id} does not exits in list of trains. Creating new train...")
				return self.railway.create_new_train(train.length, origin_id)

			return train

	def computeHash(self, clienstate: Message):
		"""Computes and returns a SHA256 hash of the given protobuf message.

		:param clientstate: A protobuf message to hash.
		:return: A hexadecimal string representing the hash of the message.
		"""
		serialized_obj = clienstate.SerializeToString()
		hash_obj = hashlib.sha256(serialized_obj)
		return hash_obj.hexdigest()
	
	def handle_client_states(self):
		"""Processes queued client state updates in a background thread. Applies state 
		updates to the railway simulation and generates server responses."""
		LOGGER.debug(F"Handling client states thread has been started")
		while not utils.exit_flag:
			if self.client_state_queue.qsize() != 0:
				(client_state, sock) = self.client_state_queue.get_nowait()
				clientStateHash = self.computeHash(client_state)

				try:
					train = self.get_train(client_state.train, client_state.location.front_junction_id)
					LOGGER.debugv(f" train name: {train.name} \n train location={train.location} \n new location={client_state.location}")
				except Exception as e:
					LOGGER.error(f"Error getting train: {e}")

				resp = TrackNet_pb2.ServerResponse()
				value = self.handled_client_states.get(train.name)

				if value is not None and clientStateHash == value[0]:
					#last_master_response = value[1]
					resp.CopyFrom(self.handle_client_state(client_state, train, apply_state=False))
				else:
					resp.CopyFrom(self.handle_client_state(client_state, train))
				
				master_response = TrackNet_pb2.InitConnection()
				master_response.sender = TrackNet_pb2.InitConnection.Sender.SERVER_MASTER
				master_response.server_response.CopyFrom(resp)

				LOGGER.debugv(f"master_response: {master_response}")
				train_id = resp.train.id
				self.handled_client_states[train_id] = (clientStateHash,master_response.server_response)
				
				# Create a separate thread for talking to slaves
				threading.Thread(target=self.talk_to_slaves, daemon=True).start()

				if not send(sock, master_response.SerializeToString()):
					LOGGER.warning(f"ServerResponse message failed to send to proxy.")
				else:
					LOGGER.debug("Sent server response to proxy successfully")
		
		LOGGER.debug("exit flag was set, will now shutdown")
		for (slave_socket) in self.socks_for_communicating_to_slaves:
			try:
				slave_socket.shutdown(socket.SHUT_RDWR)
				slave_socket.close()
			except Exception as e:
				pass
		
		for proxy_sock in self.proxy_sockets.values():
			try:
				proxy_sock.shutdown(socket.SHUT_RDWR)
				proxy_sock.close()
			except Exception as e:
				pass

	def handle_client_state(self, client_state, train, apply_state=True):
		if apply_state:
			self.apply_client_state(client_state, train)
		resp = self.issue_client_command(client_state, train)
		return resp

	def apply_client_state(self, client_state, train):
		"""Applies the given client state update to the specified train in the railway simulation.

		:param client_state: A protobuf message containing the client's state update.
		:param train: The TrainMovement object to update.
		"""
		# assume client_state location is set
		# set train info

		# check train condition
		if client_state.location.HasField("front_track_id"):
			self.railway.map.set_track_condition(
				client_state.location.front_track_id,
				TrackCondition(client_state.condition),
			)

		# update train location
		location = MessageConverter.location_msg_to_obj(
			client_state.location, 
			junction_refs=self.railway.map.junctions,
			track_refs=self.railway.map.tracks
		)
		route = MessageConverter.route_msg_to_obj(
			client_state.route,
			junction_refs=self.railway.map.junctions
		)
		train_done = self.railway.update_train(
			train,
			TrainState(client_state.train.state),
			location,
			route,
		)

		if train_done and (train.name in self.client_commands):
			del self.client_commands[train.name]

		#self.railway.print_map()

	def issue_client_command(self, client_state, train):
		"""Generates a server response based on the client's current 
		state and the specified train's needs.

		:param client_state: A protobuf message containing the client's state update.
		:param train: The TrainMovement object to consider in the response.
		:return: A ServerResponse protobuf message.
		"""
		resp = TrackNet_pb2.ServerResponse()
		resp.train.id = train.name
		resp.train.length = train.length
		resp.client.CopyFrom(client_state.client)
		#LOGGER.debug(f"trains speed being set to {TrainSpeed.FAST.value}")
		#resp.speed = TrainSpeed.FAST.value
		#resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR

		if (
			(datetime.now() - self.previous_conflict_analysis_time > timedelta(seconds=self.conflict_analysis_interval))
			or (train.name not in self.client_commands)
		):
			self.client_commands = ConflictAnalyzer.resolve_conflicts_simple(self.railway, self.client_commands)
			self.previous_conflict_analysis_time = datetime.now()
		else:
			LOGGER.debugv(f"No new commands: {self.previous_conflict_analysis_time} {self.conflict_analysis_interval}")
		LOGGER.debugv(f"client commands: {self.client_commands}")
		command = self.client_commands[train.name]
		resp.status = command.status
		if command.HasField("new_route"):
			resp.new_route = command.new_route
		if command.HasField("speed"):
			resp.speed = command.speed
		else:
			LOGGER.warning("NO SPEED!!!!")

		return resp

	def set_slave_identification_msg(self, slave_identification_msg: TrackNet_pb2.InitConnection):
		"""Populates a ``InitConnection`` protobuf message with identification details for a 
		slave server, indicating that the message sender is a server acting in a slave capacity.

   		:param slave_identification_msg: The ``InitConnection`` protobuf message to be populated with slave server details.
		"""
		slave_identification_msg.sender = TrackNet_pb2.InitConnection.SERVER_SLAVE
		slave_identification_msg.slave_details.host = self.host
		# slave_identification_msg.slave_details.port = slave_to_master_port
		slave_identification_msg.slave_details.port = self.port

	def listen_for_master(self, host, port):
		"""Sets up a server socket to listen for connections from a master server. When a 
		connection is established, it starts a new thread to handle communication with the master.

		:param host: The hostname or IP address the slave server listens on for master connections.
		:param port: The port number the slave server listens on for master connections.
		"""
		slave_to_master_sock = create_server_socket(host, port)
		LOGGER.debug("Slave created listening socket, waiting for master backups")

		if slave_to_master_sock is None:
			LOGGER.warning("Slave failed to create listening socket for master.")
			return

		while (not self.is_master) and (not utils.exit_flag):
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
		
		LOGGER.debug(f"No longer wating for master to connect")
		try:
			slave_to_master_sock.shutdown(socket.SHUT_RDWR)
			slave_to_master_sock.close()
		except:
			pass


	def handle_master_communication(self, conn):
		"""Handles communication with a connected master server. It listens for updates 
		from the master and processes them as necessary. This includes updating the local 
		state based on master's railway updates and keeping track of last handled client 
		states.

   		:param conn: The socket connection to the master server.
		"""
		try:
			while self.connected_to_master and (not self.is_master):
				try:
					data = receive(conn)  # Adjust buffer size as needed
					if data:
						master_resp = TrackNet_pb2.InitConnection()
						master_resp.ParseFromString(data)
						# Check if sender is master
						if (master_resp.sender== TrackNet_pb2.InitConnection.SERVER_MASTER and master_resp.HasField("railway_update")):
							#LOGGER.debug(f"Slave received a backup form the master: {master_resp.railway_update}")
							# need to store the backup
							dt_obj = datetime.fromtimestamp(master_resp.railway_update.timestamp)
							
							readable_date = dt_obj.strftime('%Y-%m-%d %H:%M:%S') # Format datetime object to string in a readable format

							LOGGER.debug(f"Received railway update from master. Time given by master server: {master_resp.railway_update.timestamp}")
							LOGGER.debugv(f"Backup Railway: {master_resp.railway_update.railway}")

							self.backup_railway_timestamp = (master_resp.railway_update.timestamp) 
							self.backup_railway = master_resp.railway_update.railway

							for last_handled_client_state in master_resp.railway_update.last_handled_client_states:
								# Extract the train_id, client_state_hash, and serverResponse
								train_id = last_handled_client_state.train_id
								client_state_hash = last_handled_client_state.client_state_hash
								server_response = last_handled_client_state.serverResponse  

								self.handled_client_states[train_id] = (client_state_hash, server_response)
							
				except socket.timeout:
					continue  # No data received within the timeout, continue loop
				except Exception as e:
					LOGGER.error(f"Error communicating with master: {e}")
					LOGGER.debug("Setting connected to master to false")
					self.connected_to_master = (False)# Reset the flag to allow for a new connection
					break  # Break out of the loop on any other exception
		finally:
			LOGGER.debug("Closing connection to master")
			conn.close()

	def slave_proxy_communication(self, sock, data):
		global LOGGER
		"""Handles messages received from a proxy server when operating as a slave server. 
		This includes processing server assignment messages and responding to heartbeat 
		checks from the proxy.

		:param sock: The socket connection to the proxy server.
		:param data: The raw data received from the proxy server.
		"""
		LOGGER.debugv("slave recieved message from proxy")
		proxy_resp = TrackNet_pb2.InitConnection()
		try:
			proxy_resp.ParseFromString(data)
		except Exception as e:
			LOGGER.error(f"In slave_proxy_communication: Error parsing proxy message: {e}"           )

		if proxy_resp.HasField("server_assignment"):
			# Determine if this server has been assigned as the master
			LOGGER.debug(f"Slave received role assignment from proxy: {proxy_resp}")

			# Determine if this server has been assigned as the master
			if proxy_resp.server_assignment.HasField("is_master"):
				if proxy_resp.server_assignment.is_master:
					LOGGER.info(f"{self.host}:{self.port} promoted to the MASTER")
					# self.promote_to_master()
					self.is_master = True
					
					LOGGER = logging.getLogger("MasterServer")
					if self.backup_railway != None:
						RailwayConverter.update_railway_with_pb(
							self.backup_railway, self.railway
						)
						# self.railway.map.print_map()
						#self.railway.print_map()
					else:
						LOGGER.info(f"no backup railway")

					for slave in proxy_resp.server_assignment.servers:
						slave_host = slave.host
						slave_port = slave.port
						LOGGER.debug(
							f"Slave host: {slave_host}, Slave port: {slave_port}"
						)
						# connect to slave in separate thread
						LOGGER.debug("Connecting to slave")
						self.connect_to_slave(slave_host, slave_port)

				else:
					LOGGER.info(f"{self.host}:{self.port} designated as a SLAVE.")
					self.is_master = False
					LOGGER = logging.getLogger("SlaveServer")

					if self.listening_for_backups.is_alive():
						LOGGER.debug(f"Thread for listening for master servers already running")

					# Connect to master if not already
					# if not self.connected_to_master and (not self.listening_for_backups.is_alive()):
					# 	# listen to master instead of initiating connection
					# 	# self.listen_for_master(self.host, 4444)
					# 	#threading.Thread(target=self.listen_for_master, args=(self.host, self.port)).start()
					# 	self.listening_for_backups.start()

		elif proxy_resp.HasField("is_heartbeat"):

			if proxy_resp.is_heartbeat:
				LOGGER.debug(
					f"Proxy requested heartbeat from slave. proxy_resp: {proxy_resp} Sending backup_railway_timestamp as a response."
				)
				response = proto.InitConnection()
				response.sender = proto.InitConnection.SERVER_SLAVE
				backup_timestamp_message = proto.SlaveBackupTimestamp()
				if self.backup_railway_timestamp:
					backup_timestamp_message.timestamp = self.backup_railway_timestamp
				else:
					backup_timestamp_message.timestamp = 0
				backup_timestamp_message.host = socket.gethostbyname(self.host) 
				backup_timestamp_message.port = self.port
				response.slave_backup_timestamp.CopyFrom(backup_timestamp_message)

				if not send(sock, response.SerializeToString()):
					LOGGER.warning("Failed to send SlaveBackupTimestamp response to proxy.")
				else:
					LOGGER.debug(
						f"Sent SlaveBackupTimestamp response to proxy. Response message: {response}"
					)
			else:
				LOGGER.debug(f"proxy_resp has heatbeat feild but set to false: {proxy_resp}")

		else:
			LOGGER.warning(f"Slave received msg from prox. slave_proxy_communication couldn't handle content: {proxy_resp}")

	def master_proxy_communication(self, sock, data):
		"""Handles messages received from a proxy server when operating as a master server. 
		This method processes information such as slave server details, client state updates 
		from proxies, and heartbeat messages.

		:param sock: The socket connection to the proxy server.
		:param data: The raw data received from the proxy server.
		"""
		# Data also needs to include an update of a new slave
		proxy_resp = TrackNet_pb2.InitConnection()
		proxy_resp.ParseFromString(data)
		# LOGGER.debug(f"Master server received response from proxy\n{proxy_resp}")

		if proxy_resp.HasField("slave_details"):
			LOGGER.debug("Received slave server details from proxy")
			slave_host = proxy_resp.slave_details.host
			slave_port = proxy_resp.slave_details.port
			LOGGER.debug(f"Slave host: {slave_host}, Slave port: {slave_port}")
			# connect to slave in separate thread
			self.connect_to_slave(slave_host, slave_port)

		# listen on proxy sock for client states
		elif proxy_resp.HasField("client_state"):
			LOGGER.debug(F"Master server received client state, will put it in queue")
			try:
				self.client_state_queue.put((proxy_resp.client_state, sock))
				# resp = self.handle_client_state(proxy_resp.client_state)
			except Exception as e:
				LOGGER.error(
					f"Error handling client state: {e} traceback: {traceback.print_exception(e)} "
				)

		# CHECK FOR HEARTBEAT HERE
		elif proxy_resp.HasField("is_heartbeat"):
			LOGGER.debugv(f"Received heartbeat from proxy: {proxy_resp.is_heartbeat}")
			
			heartbeat_message = proto.InitConnection()
			heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.SERVER_MASTER
			heartbeat_message.is_heartbeat = True
			if send(sock, heartbeat_message.SerializeToString()):
				LOGGER.debugv(f"Sent heartbeat message to main proxy {heartbeat_message}")
			else:
				LOGGER.warning("Failed to send heartbeat message to main proxy.")
		else:
			LOGGER.warning(f"Server received msg from proxy with missing content: {proxy_resp}")

	def listen_to_proxy(self, proxy_sock, key):
		"""Listens for messages from a proxy server in a background thread 
		and processes them accordingly.

		:param proxy_sock: The socket connected to the proxy server.
		:param key: A unique identifier for the proxy connection.
		"""
		try:
			while not utils.exit_flag:
				try:
					data = receive(proxy_sock,timeout=5, returnException=True)
				except socket.timeout:
					data = None

				if (data):  # split data into 3 difrerent types of messages, a heartbeat, a clientstate or a ServerAssignment
					# Master server responsibilitites
					if self.is_master:
						try:
							self.master_proxy_communication(proxy_sock, data)
						except KeyboardInterrupt:
							LOGGER.error(f"KeyBoard Interupt")
							proxy_sock.shutdown(socket.SHUT_RDWR)
							proxy_sock.close()
							sys.exit(1)
						except Exception as e:
							LOGGER.error(f"Error in master proxy communication: {e}")
							traceback.print_exc()
							proxy_sock.shutdown(socket.SHUT_RDWR)
							proxy_sock.close()

					# Slave server responsibilities
					else:
						try:
							self.slave_proxy_communication(proxy_sock, data)
						except KeyboardInterrupt:
							LOGGER.error(f"KeyBoard Interupt")
							proxy_sock.shutdown(socket.SHUT_RDWR)
							proxy_sock.close()
							sys.exit(1)
						except Exception as e:
							LOGGER.error(f"Error in slave proxy communication: {e}")
							traceback.print_exc()
							proxy_sock.shutdown(socket.SHUT_RDWR)
							proxy_sock.close()

		except KeyboardInterrupt:
			LOGGER.error(f"KeyBoard Interupt")
			proxy_sock.shutdown(socket.SHUT_RDWR)
			proxy_sock.close()
			sys.exit(1)
		except Exception as e:
			LOGGER.error(f"Error communicating with proxy, will reconnect to proxy, exception: {e}")
			proxy_sock.shutdown(socket.SHUT_RDWR)
			proxy_sock.close()
			self.proxy_sockets[key] = None
			# if self.connecting_to_proxies == False:
			# 	threading.Thread(target=self.connect_to_proxy(), daemon=True).start()

	def connect_to_proxy(self):
		"""Establishes connections to proxy servers and maintains them. 
		Manages the reconnection process if connections are lost."""
		#all_connected = False
		# Determine the source of proxy details
		proxies_to_connect = cmdLineProxyDetails if proxyDetailsProvided else proxy_details.items()

		while not utils.exit_flag:
			try:
				all_connected = all(
						f"{proxy_host}:{proxy_port}" in self.proxy_sockets and
						self.proxy_sockets[f"{proxy_host}:{proxy_port}"] is not None
						for proxy_host, proxy_port in proxies_to_connect)
				
				while not all_connected:
					self.connecting_to_proxies = True
					#LOGGER.debug(f"!!!-------Connect to proxy called in thread: {threading.current_thread().name}")
				
					
					# Attempt to connect to each proxy
					for proxy_host, proxy_port in proxies_to_connect:
						key = f"{proxy_host}:{proxy_port}"
						if key not in self.proxy_sockets or self.proxy_sockets[key] is None:
							self.attempt_proxy_connection(proxy_host, proxy_port, key)

					all_connected = all(
						f"{proxy_host}:{proxy_port}" in self.proxy_sockets and
						self.proxy_sockets[f"{proxy_host}:{proxy_port}"] is not None
						for proxy_host, proxy_port in proxies_to_connect)

					if all_connected:
						LOGGER.info("Connected to all proxies. Stopping connection attempts.")
						pass

					time.sleep(5)  # Sleep between connection attempts
				self.connecting_to_proxies = False
				#LOGGER.debug(f"done connecting to proxies")
			except Exception:
				LOGGER.debug("Exception occur while trying to connect to all the proxies")
		


	def attempt_proxy_connection(self, proxy_host, proxy_port, key):
		"""Attempts to establish a connection to a proxy server. If successful, 
		it sends a slave identification message to the proxy and starts a thread to 
		listen to messages from this proxy.

		:param proxy_host: The hostname or IP address of the proxy server.
		:param proxy_port: The port number of the proxy server.
		:param key: A unique identifier for the proxy connection, typically combining host and port.
		"""
		LOGGER.info(f"Connecting to proxy at {proxy_host}:{proxy_port}")
		proxy_sock = create_client_socket(proxy_host, proxy_port)

		if proxy_sock:
			LOGGER.info(f"Connected to proxy at {proxy_host}:{proxy_port}")
			self.proxy_sockets[key] = proxy_sock
			# Send proxy init message to identify itself
			slave_identification_msg = TrackNet_pb2.InitConnection()
			self.set_slave_identification_msg(slave_identification_msg)

			if send(proxy_sock, slave_identification_msg.SerializeToString()):
				LOGGER.debug("Sent slave identification message to proxy")
				threading.Thread(target=self.listen_to_proxy, args=(proxy_sock,key), daemon=True).start()
		else:
			LOGGER.warning(f"Couldn't connect to proxy at {proxy_host}:{proxy_port}")

	def connect_to_slave(self, slave_host, slave_port):
		"""Initiates a connection to a slave server for distributing the load 
		and ensuring high availability.

		:param slave_host: The hostname or IP address of the slave server.
		:param slave_port: The port number the slave server listens on.
		"""
		try:
			# for each slave create client sockets
			#LOGGER.debug(f"Sleeping for five seconds before trying to connect to slave")
			#time.sleep(5)
			LOGGER.debug(f"Before creating client socket, host: {slave_host} port: {slave_port}")
			slave_sock = create_client_socket(slave_host, slave_port, timeout=6)
			LOGGER.debug(f"Type of slave sock: {type(slave_sock)}")
			if slave_sock is None:
				LOGGER.warning(f"Could not connect to the given slave server: {slave_host}  {slave_port}")
			else:
				self.socks_for_communicating_to_slaves.append(slave_sock)
				LOGGER.debug(f"Added slave server {slave_host}:{slave_port}")

				# added slave server, will send a backup to all slaves 
				# Create a separate thread for talking to slaves
				threading.Thread(target=self.talk_to_slaves, daemon=True).start()

			
			# Start a new thread dedicated to this slave for communication
		#            threading.Thread(target=self.handle_slave_communication, args=(slave_sock,), daemon=True).start()
		except Exception as e:
			LOGGER.error(f"Could not connect to slave {slave_host}:{slave_port}: {e}")

	def serialize_train(self, train_obj, train_pb):
		"""Serializes a train object into a protobuf message, including its location and 
		route information.

		:param train_obj: The train object to serialize.
		:param train_pb: The protobuf Train message to be populated with the train object's data.
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
		"""Serializes a location object into a protobuf message, including details 
		of the front and back cart positions.

		:param location_obj: The location object to serialize.
		:param location_pb: The protobuf Location message to be populated with the location object's data.
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
		"""Serializes a route object into a protobuf message, including its sequence 
		of junctions and current position in the route.

		:param route_obj: The route object to serialize.
		:param route_pb: The protobuf Route message to be populated with the route object's data.
		"""
		for junction in route_obj.junctions:
			junction_pb = route_pb.junctions.add()
			junction_pb.id = junction.name
		route_pb.current_junction_index = route_obj.current_junction_index
		if route_obj.destination:
			route_pb.destination.id = route_obj.destination.name

	def talk_to_slaves(self):  # needs to send railway update to slaves
		"""Sends the latest railway update message to all connected slave servers. 
		This method is typically invoked after receiving updates from clients or from 
		the master server to ensure all slave servers have the latest state.

   		This method iterates through sockets connected to slave servers, 
		prepares a railway update message, and sends it to each slave.
		"""
		LOGGER.debug(f"number of slaves: {len(self.socks_for_communicating_to_slaves)}")
		for slave_socket in self.socks_for_communicating_to_slaves:
			# Prepare the client state message
			master_resp = TrackNet_pb2.InitConnection()
			master_resp.sender = TrackNet_pb2.InitConnection.SERVER_MASTER
			master_resp.railway_update.CopyFrom(self.create_railway_update_message())
			LOGGER.debugv("Railway update message created")
			LOGGER.debugv(f"type of slave socket: {type(slave_socket)}")
			if slave_socket.fileno() < 0:
				# slave socket is closed
				LOGGER.debug(f"Removing an unavailable slave")
				self.socks_for_communicating_to_slaves.remove(slave_socket)
			else:
				if send(slave_socket, master_resp.SerializeToString()):
					LOGGER.debugv(f"Railway update message sent to slave successfully")
				else:
					LOGGER.warning(f"Could not send backup message to: {slave_socket}")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Process Server args")

	parser.add_argument("-proxy1", type=str, help="Address for proxy1")
	parser.add_argument("-proxy2", type=str, help="Address for proxy2")
	parser.add_argument("-proxyPort1", type=int, help="Proxy 1 port number")
	parser.add_argument("-proxyPort2", type=int, help="Proxy 2 port number")
	parser.add_argument(
		"-listeningPort", type=int, help="Listening port number", default=4444
	)

	args = parser.parse_args()

	proxy1_address = args.proxy1
	proxy2_address = args.proxy2
	proxy1_port_num = args.proxyPort1
	proxy2_port_num = args.proxyPort2
	listening_port_num = args.listeningPort

	LOGGER.debugv(f"Proxy 1 address {proxy1_address}")
	LOGGER.debugv(f"Proxy 2 address {proxy2_address}")
	LOGGER.debugv(f"Proxy 1 port number {proxy1_port_num}")
	LOGGER.debugv(f"Proxy 2 port number {proxy2_port_num}")
	LOGGER.debugv(f"Listening port {listening_port_num}")

	if proxy1_port_num == None:
		proxy1_port_num = 5555

	if proxy2_port_num == None:
		proxy2_port_num = 5555

	if proxy1_address == None and proxy2_address == None:
		# use proxydetails
		proxyDetailsProvided = False
		LOGGER.debug(f"Proxy details not provided, will use util values")
	else:
		proxyDetailsProvided = True
		LOGGER.debug(
			f"Proxy details provided, Proxy 1: {proxy1_address}:{proxy1_port_num} and Proxy 2: {proxy2_address}:{proxy2_port_num}"
		)
		if proxy1_address != None:
			cmdLineProxyDetails.append((proxy1_address, proxy1_port_num))
		if proxy2_address != None:
			cmdLineProxyDetails.append((proxy2_address, proxy2_port_num))

	Server(port=listening_port_num)

