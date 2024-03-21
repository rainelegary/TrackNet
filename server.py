import TrackNet_pb2
import TrackNet_pb2 as proto
import logging
import socket
import signal
import threading
from utils import *
from  classes.enums import TrainState, TrackCondition
from classes.railway import Railway
from classes.train import Train
import traceback
from datetime import datetime
import time
import threading
from utils import initial_config, proxy_details
from message_converter import MessageConverter

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
        self.host = socket.gethostname()
        self.port = port

        self.connected_to_master = False
        self.is_master = False
        self.slave_sockets = {}
        self.proxy_sockets = {}
        self.socks_for_communicating_to_slaves = []

        self.railway = Railway(
            trains=None,
            junctions=initial_config["junctions"],
            tracks=initial_config["tracks"]
        )

        self.connect_to_proxy()
        self.isMaster = False
        self.proxy_host = "csx1.ucalgary.ca"
        self.proxy_port = 5555
        self.connect_to_proxy (self.proxy_host, self.proxy_port)
        #self.listen_on_socket ()

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
            return self.railway.create_new_train(train.length, origin_id)
        else:
            try:
                train = self.railway.trains[train.id]
            except:
                LOGGER.error(f"Train {train.id} does not exits in list of trains. Creating new train...")
                return self.railway.create_new_train(train.length, origin_id)

            return train

    def analyze_client_state(self, client_state):
        ## assumes that ClientSate.Location is always set

        #client_state = TrackNet_pb2.ClientState()

        #init_message = TrackNet_pb2.InitConnection()  # Assuming this is your wrapper message
        #init_message.ParseFromString(data)
        #LOGGER.debug(f"Received: {init_message}")

        #client_state.ParseFromString(data)
        resp = TrackNet_pb2.ServerResponse()

        train = self.get_train(client_state.train, client_state.location.front_junction_id)
        ## set train info in response message
        resp.train.id            = train.name
        resp.train.length        = train.length

        resp.client.CopyFrom(client_state.client)

        # check train condition
        if client_state.location.HasField("front_track_id"):
            self.railway.map.set_track_condition(client_state.location.front_track_id, TrackCondition(client_state.condition))

            if self.railway.map.has_bad_track_condition(client_state.location.front_track_id):
                resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                resp.speed = 200     ## TODO set slow speed

        # update train location
        #add 4th argument
        self.railway.update_train(train, TrainState(client_state.train.state), client_state.location, client_state.route)

        # (TODO) use speed, location & route data to detect possible conflicts.
        resp.speed = 200
        resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR

        self.railway.print_map()
        return resp

    def set_slave_identification_msg(self, slave_identification_msg: TrackNet_pb2.InitConnection):
        slave_identification_msg.sender = TrackNet_pb2.InitConnection.SERVER_SLAVE
        slave_identification_msg.slave_details.host = self.host
        slave_identification_msg.slave_details.port = self.port

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
        LOGGER.debug(f"Master received response from proxy\n{proxy_resp}")

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
            resp = self.analyze_client_state(proxy_resp.client_state)
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
            LOGGER.debug(f"Received heartbeat from proxy: {proxy_resp.is_heartbeat}")
            heartbeat_message = proto.InitConnection()
            heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.SERVER_MASTER
            heartbeat_message.is_heartbeat = True
            if send(sock, heartbeat_message.SerializeToString()):
                LOGGER.debug("Sent heartbeat message to main proxy.")
                LOGGER.debug("Waiting for main proxy to respond")
            else:
                LOGGER.warning("Failed to send heartbeat message to main proxy.")

        else:
            LOGGER.warning(f"Server received msg from proxy with missing co0ntent: {proxy_resp}")

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
            LOGGER.error(f"Error communicating with proxy: {e}")
            proxy_sock.shutdown(socket.SHUT_RDWR)
            proxy_sock.close()

    def connect_to_proxy(self):
        while not exit_flag:
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
            slave_sock = create_client_socket(slave_host, 4444)
            self.socks_for_communicating_to_slaves.append(slave_sock)
            LOGGER.debug (f"Added slave server {slave_host}:{slave_port}")
            # Start a new thread dedicated to this slave for communication
#            threading.Thread(target=self.handle_slave_communication, args=(slave_sock,), daemon=True).start()
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



    def get_train(self, train: TrackNet_pb2.Train, origin_id: str):
        """Retrieves a Train object based on its ID. If the train does not exist, it creates a new Train object.

        :param train: The train identifier or a Train object with an unset ID to create a new Train.
        :return: Returns the Train object matching the given ID, or a new Train object if the ID is not set.
        :raises Exception: Logs an error if the train ID does not exist in the list of trains.
        """
        if not train.HasField("id"):
            return self.railway.create_new_train(train.length, origin_id)
        else:
            try:
                train = self.railway.trains[train.id]
            except:
                LOGGER.error(f"Train {train.id} does not exits in list of trains. Creating new train...")
                return self.railway.create_new_train(train.length, origin_id)

            return train

    def handle_client_state(self, client_state):
        resp = TrackNet_pb2.ServerResponse()

        train = self.get_train(client_state.train, client_state.location.front_junction_id)
        ## set train info in response message
        resp.train.id            = train.name
        resp.train.length        = train.length

        resp.clientIP = client_state.clientIP
        resp.clientPort = client_state.clientPort

        # check train condition
        if client_state.location.HasField("front_track_id"):
            self.railway.map.set_track_condition(client_state.location.front_track_id, TrackCondition(client_state.condition))

            if self.railway.map.has_bad_track_condition(client_state.location.front_track_id):
                resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                resp.speed = 200     ## TODO set slow speed

        # update train location
        self.railway.update_train(train, TrainState(client_state.train.state), client_state.location)

        # (TODO) use speed, location & route data to detect possible conflicts.
        resp.speed = 200
        resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR

        self.railway.print_map()
        return resp

    def handle_connection(self, conn):
        ## assumes that ClientSate.Location is always set

        client_state = TrackNet_pb2.ClientState()
        data = receive(conn)

        if data:
            init_message = TrackNet_pb2.InitConnection()  # Assuming this is your wrapper message
            init_message.ParseFromString(data)
            LOGGER.debug(f"Received: {init_message}")

            client_state.ParseFromString(data)
            resp = TrackNet_pb2.ServerResponse()

            train = self.get_train(client_state.train, client_state.location.front_junction_id)
            ## set train info in response message
            resp.train.id            = train.name
            resp.train.length        = train.length

            # check train condition
            if client_state.location.HasField("front_track_id"):
                self.railway.map.set_track_condition(client_state.location.front_track_id, TrackCondition(client_state.condition))

                if self.railway.map.has_bad_track_condition(client_state.location.front_track_id):
                    resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                    resp.speed = 200     ## TODO set slow speed

            # update train location
            self.railway.update_train(train, TrainState(client_state.train.state), client_state.location, client_state.route)

            # TODO Run conflict analyzer

            resp.speed = 200
            resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR

            if not send(conn, resp.SerializeToString()):
                LOGGER.error("response did not send.")

        self.railway.print_map()


if __name__ == '__main__':
    Server()