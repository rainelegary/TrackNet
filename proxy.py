import select
import socket
import threading
import TrackNet_pb2
import TrackNet_pb2 as proto
import traceback
import time
import TrackNet_pb2
import logging
import sys
import time
from utils import *
import argparse


# Global Variables
proxy_address = None
proxy_port_num = None
listening_port_num = None
isMain = None
isBackup = None


setup_logging()  ## only need to call at main entry point of application

LOGGER = logging.getLogger("Proxy")


class Proxy:
    def __init__(
        self,
        proxy_port=5555,
        listening_port=5555,
        is_main=False,
        mainProxyAddress=list(proxy_details.items())[0][0],
    ):
        LOGGER.debug(f"port: {proxy_port} listening port {listening_port}")
        self.host = socket.gethostname()
        self.port = listening_port
        self.proxy_port = proxy_port
        self.master_socket = None
        self.master_socket_hostIP = None
        self.slave_sockets = {}
        self.client_sockets = ({})  # Map client address (IP, port) to socket for direct access
        self.client_state_handled = {} # Map client address (IP, port) and to tuple (client_state,response_received)
        self.socket_list = []
        self.lock = threading.Lock()
        self.heartbeat_interval = 3
        self.heartbeat_timeout = 2
        self.slave_heartbeat_timeout = 2

        self.is_main = is_main
        if is_main:
            self.main_proxy_host = self.host
        else:
            self.main_proxy_host = mainProxyAddress

        self.heartbeat_attempts = 0
        self.max_heartbeat_attempts = 0
        self.heartbeat_timer = None
        self.master_server_heartbeat_thread = threading.Thread(target=self.send_heartbeat_loop, daemon=True)
        if self.is_main:
            self.master_server_heartbeat_thread.start()
        # self.set_main_proxy_host()

        self.all_slave_timestamps = {}
        threading.Thread(target=self.proxy_to_proxy, daemon=True).start()

    def set_main_proxy_host(self):
        if self.is_main:
            self.main_proxy_host = self.host
        elif proxy_address != None:
            self.main_proxy_host = proxy_address
        else:
            self.main_proxy_host = list(proxy_details.items())[0][0]

            # for proxy, _ in proxy_details.items():
            #     if proxy != self.host and proxy != "DESKTOP-BF2NK58":
            #         self.main_proxy_host = proxy
            #     else:
            #         LOGGER.debug("proxy is the same as self.host")

        LOGGER.info(f"Main proxy hostname: {self.main_proxy_host}")
        ## case where only one proxy and command-line arg main missing
        if self.main_proxy_host is None:
            LOGGER.warning(f"Only one proxy? setting as main proxy")
            self.main_proxy_host = self.host
            self.is_main = True

    def add_slave_socket(self, slave_socket: socket.socket, slave_port: int):
        self.slave_sockets[(f"{slave_socket.getpeername()[0]}",slave_port)] = slave_socket
        LOGGER.debug(f"Slave ({slave_socket.getpeername()[0]},{slave_port}) added")

    def remove_slave_socket(self, slave_socket: socket.socket,slave_port: int):
        try:
            del self.slave_sockets[(slave_socket.getpeername()[0],slave_port)]
        except KeyError:
            pass
        except Exception as exc:
            LOGGER.warning(f"Error removing slave socket from list of slaves: {exc}")

    def relay_client_state(self, client_state: TrackNet_pb2.ClientState):
        LOGGER.info("Received client state")
        LOGGER.debug(f"{client_state}")
        # Extract the target client's IP and port
        target_client_key = (f"{client_state.client.host}:{client_state.client.port}")

        self.client_state_handled[target_client_key] = (client_state,False)

        with self.lock:
            if self.master_socket is not None:
                new_message = proto.InitConnection()
                new_message.sender = proto.InitConnection.Sender.PROXY
                # Can't copy from entire client state
                # Have to copy each field individually
                new_message.client_state.client.CopyFrom(client_state.client)
                new_message.client_state.train.CopyFrom(client_state.train)
                new_message.client_state.location.CopyFrom(client_state.location)
                new_message.client_state.condition = client_state.condition
                new_message.client_state.route.CopyFrom(client_state.route)
                new_message.client_state.speed = client_state.speed
                # new_message.client_state.CopyFrom(client_state)

                if self.master_socket is None:
                    LOGGER.debug("MASTER NONE")
                if not send(self.master_socket, new_message.SerializeToString()):
                    LOGGER.warning(f"Failed to send client state message to master.")
                else:
                    LOGGER.debug("client state forwaded to master server")
            else:
                LOGGER.warning("There is currently no master server")

    def relay_server_response(self, server_response: TrackNet_pb2.ServerResponse):
        with self.lock:
            LOGGER.debug(
                f"Received server response from master server for client with ip:{server_response.client.host} and port:{server_response.client.port}"
            )

            # Extract the target client's IP and port
            target_client_key = (
                f"{server_response.client.host}:{server_response.client.port}"
            )
            target_client_socket = self.client_sockets.get(target_client_key)
            

            relay_resp = proto.InitConnection()
            relay_resp.sender = proto.InitConnection.Sender.PROXY
            relay_resp.server_response.CopyFrom(server_response)

            LOGGER.debug(f"Relaying server response message to client on socket: {target_client_socket}")
            LOGGER.debug(f"{relay_resp}")
            # Forward the server's message to the target client
            if target_client_socket:
                try: 
                    if not send(target_client_socket, relay_resp.SerializeToString(),returnException=True):
                        LOGGER.warning(f"Failed to send server response message to client. socket: {target_client_socket}")
                    else:
                        self.client_state_handled[target_client_key] = (None,True)
                except Exception as e:
                    LOGGER.warning(f"Failed to send server response message to client. socket: {target_client_socket}")
                    LOGGER.warning(f"Exception thrown: {e} type: {type(e)} repr: {repr(e)}")

            else:
                LOGGER.warning(f"Target client {target_client_key} not found.")

    def promote_slave_to_master(self, slave_socket: socket.socket, slave_port: int):

        self.master_socket = slave_socket
        try:
            self.master_socket_hostIP = slave_socket.getpeername()[0]
        except Exception as e:
            LOGGER.warning(
                f"Exception {e} was thrown when setting master_socket_hostIP "
            )

        self.remove_slave_socket(self.master_socket,slave_port)
        LOGGER.info(f"Promoting {self.master_socket_hostIP} to MASTER, was previously a slave listening on port {slave_port}")
        # LOGGER.info(f"{slave_socket.getpeername()} promoted to MASTER")

        # notify the newly promoted master server of its new role
        proxy_message = proto.InitConnection()
        proxy_message.sender = proto.InitConnection.Sender.PROXY
        role_assignment = proto.ServerAssignment()
        role_assignment.is_master = True

        if len(self.slave_sockets) <= 0:
            LOGGER.info("No slaves to send to master")

        # Send slave details to master server
        for (slave_ip,slave_port), _ in self.slave_sockets.items():
            slave_details = role_assignment.servers.add()
            slave_details.host = slave_ip
            #slave_details.port = slave_to_master_port
            slave_details.port = slave_port
            # LOGGER.info(f"Adding {slave_ip}:{slave_to_master_port} to list of slaves")

        proxy_message.server_assignment.CopyFrom(role_assignment)

        if send(slave_socket, proxy_message.SerializeToString()):
            LOGGER.debug(f"Sent role assignmnet to newly elected master.")

            LOGGER.debug("Will send unhandeled client states to new master")

            for (client_state,responseSent) in self.client_state_handled.values():
                if responseSent == False:
                    LOGGER.debug(f"Will send client state {client_state} to new master")
                    self.relay_client_state(client_state)

        else:
            LOGGER.warning(f"Failed to send role assignmnet to newly elected master.")

        ##TODO recv ACK

        # remove new master from list of slaves
        # self.remove_slave_socket(slave_socket)
        #LOGGER.debug("sending heartbeat to new master server")
        #self.master_server_heartbeat_thread.start()
        # threading.Thread(target=self.send_heartbeat, args=(self.master_socket,), daemon=True).start()
        #self.send_heartbeat()

    def notify_master_of_new_slave(self, init_conn: TrackNet_pb2.InitConnection):
        # Notify master of new slave server so it can connect to it
        slave_host = init_conn.slave_details.host
        slave_port = init_conn.slave_details.port

        # Create protobuf response
        resp = TrackNet_pb2.InitConnection()
        resp.sender = TrackNet_pb2.InitConnection.Sender.PROXY
        slave_details = resp.slave_details
        slave_details.host = slave_host
        slave_details.port = slave_port

        LOGGER.debug("Sending slave details to master")
        if not send(self.master_socket, resp.SerializeToString()):
            LOGGER.warning(f"Failed to send slave details to master.")

    def notify_master_of_slaves(self):
        # Notify master of new slave server so it can connect to it
        resp = TrackNet_pb2.InitConnection()
        resp.sender = TrackNet_pb2.InitConnection.Sender.PROXY
        for slave_ip, _ in self.slave_sockets.items():
            slave_details = resp.slave_details.add()
            slave_details.host = slave_ip
            slave_details.port = slave_to_master_port

        LOGGER.debug("Sending slave details to master")
        if not send(self.master_socket, resp.SerializeToString()):
            LOGGER.warning(f"Failed to send slave details to master.")

    def slave_role_assignment(
        self, slave_socket: socket.socket, init_conn: TrackNet_pb2.InitConnection
    ):
        slave_host = init_conn.slave_details.host
        slave_port = init_conn.slave_details.port

        with self.lock:
            # Check if there is no master server, and promote the first slave to master
            if self.master_socket is None:
                self.promote_slave_to_master(slave_socket,slave_port)

            # Already have master so assign slave role
            else:

                self.add_slave_socket(slave_socket,slave_port)

                proxy_message = proto.InitConnection()
                proxy_message.sender = proto.InitConnection.Sender.PROXY
                role_assignment = proto.ServerAssignment()
                role_assignment.is_master = False
                proxy_message.server_assignment.CopyFrom(role_assignment)

                if not send(slave_socket, proxy_message.SerializeToString()):
                    LOGGER.warning(f"Failed to send role assignmnet to slave.")

                # self.notify_master_of_slaves()
                self.notify_master_of_new_slave(init_conn)

    def handle_missed_proxy_heartbeat(self):
        self.heartbeat_attempts += 1

        if self.heartbeat_attempts >= self.max_heartbeat_attempts:
            self.is_main = True
            LOGGER.debug("Setting self to main proxy")
            LOGGER.info("Calling send heartbeat")
            #self.send_heartbeat()
            if self.master_socket:
                self.master_server_heartbeat_thread.start()
            return True

        return False

    def proxy_to_proxy(self):
        connected_to_proxy = False

        if not self.is_main:
            LOGGER.debug("IS BACKUP PROXY")
            LOGGER.info("Connecting to main proxy...")
            while not connected_to_proxy:
                proxy_sock = create_client_socket(self.main_proxy_host, self.proxy_port)

                if proxy_sock:
                    connected_to_proxy = True
                    LOGGER.debug("Connected to main proxy")
                    # self.socket_list.append(proxy_sock)
                    proxy_sock.settimeout(self.heartbeat_timeout)

                else:
                    LOGGER.warning(
                        f"Failed to connect to main proxy. Trying again in 5 seconds ..."
                    )
                    time.sleep(self.heartbeat_interval)
                    if self.handle_missed_proxy_heartbeat():
                        LOGGER.info("IS MAIN PROXY")
                        return

            self.listen_to_main_proxy(proxy_sock)

    def listen_to_main_proxy(self, proxy_sock: socket.socket):
        LOGGER.info("Keeping heartbeat with main proxy ...")

        while not self.is_main:
            heartbeat_message = proto.InitConnection()
            heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
            heartbeat_message.is_heartbeat = True
            if not send(proxy_sock, heartbeat_message.SerializeToString()):
                LOGGER.warning("Failed to send heartbeat message to main proxy.")

            data = receive(proxy_sock)

            if data:
                heartbeat = proto.Response()
                heartbeat.ParseFromString(data)

                if heartbeat.code != proto.Response.Code.HEARTBEAT:
                    LOGGER.debug("Did not received heartbeat from main proxy?")

                if heartbeat.HasField("master_host"):

                    # if no master server or new master server
                    if (
                        self.master_socket is None
                        or self.master_socket_hostIP != heartbeat.master_host
                    ):
                        LOGGER.debug("Updating master server ...")
                        LOGGER.info(
                            f"slave sockets: {self.slave_sockets}, items: {self.slave_sockets.items()}"
                        )
                        foundMasterServer = False
                        slave_port_chosen = None

                        with self.lock:
                            for (slave_host, slave_port), slave in self.slave_sockets.items():
                                try:
                                    if slave.getpeername()[0] == heartbeat.master_host:
                                        foundMasterServer = True
                                        slave_port_chosen = slave_port
                                        self.master_socket = slave
                                        self.master_socket_hostIP = slave.getpeername()[0]
                                        LOGGER.debug(
                                            "Master server updated to %s",
                                            heartbeat.master_host,
                                        )
                                except Exception as e:
                                    LOGGER.warning(
                                        f"Exception {e} was thrown when finding master server from slaves"
                                    )
                        if foundMasterServer == False:
                            LOGGER.warning(
                                f"BackUp Proxy doesn't have connection to the master server ? {heartbeat.master_host}"
                            )
                        else:
                            self.remove_slave_socket(self.master_socket,slave_port_chosen)

                time.sleep(self.heartbeat_interval)
            else:
                LOGGER.debug("No data received from main")
                if self.handle_missed_proxy_heartbeat():
                    LOGGER.info("IS MAIN PROXY")


	
    def send_heartbeat_loop(self):

        LOGGER.debug(f"Sending heartbeat thread started: ")
        while True:
            
            if self.heartbeat_timer and self.heartbeat_timer.is_alive():
                LOGGER.debug(f"sent a heartbeat already and timer running")
            else:
                try:
                    if self.master_socket:
                        LOGGER.debugv(f"master socket: {self.master_socket} ")
                        if self.master_socket.fileno() < 0:
                            LOGGER.warning(f"File descriptor for socket is negative. Assume master server is down: {self.master_socket} ")
                            self.handle_heartbeat_timeout_loop()
                        else:
                            heartbeat_message = proto.InitConnection()
                            heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                            heartbeat_message.is_heartbeat = True

                            # Start a timer
                            LOGGER.debug("Starting timer right before sending heartbeat:")
                            self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.handle_heartbeat_timeout_loop)
                            self.heartbeat_timer.start()

                            LOGGER.debug(f"Sending... heartbeat to master server {self.master_socket}")

                            if not send(self.master_socket, heartbeat_message.SerializeToString()):
                                LOGGER.warning(f"Failed to send heartbeat request to master server {self.master_socket} FD: {self.master_socket.fileno()}")
                                self.heartbeat_timer.cancel()
                                self.handle_heartbeat_timeout_loop()
                            else:
                                LOGGER.debug("Sent heartbeat to master")
                                #self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.handle_heartbeat_timeout_loop)
                                #self.heartbeat_timer.start()       
                    else:
                        LOGGER.debugv(f"No master server: {self.master_socket}")

                except Exception as e:
                    LOGGER.warning(f"Error sending heartbeat to maser server: {e}")
                    self.heartbeat_timer.cancel()
                    self.handle_heartbeat_timeout()  # Trigger timeout handling 

            time.sleep(self.heartbeat_interval)         
            
    def handle_heartbeat_response_loop(self):
        # LOGGER.debugv("Received heartbeat response from master server.")
        # Cancel the timer if it's still running
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel()

    def handle_heartbeat_timeout_loop(self):
        LOGGER.info("Heartbeat response timed out. Stop sending hearbeat by setting master socket to none")
        #self.master_server_heartbeat_thread
        self.master_socket = None
        if len(self.slave_sockets) > 0:
            LOGGER.debug("Number of slave sockets: %d", len(self.slave_sockets))
            chosenTuple = self.choose_new_master()

            if chosenTuple != None :
                (new_master_socket,slave_port) = chosenTuple
                self.promote_slave_to_master(new_master_socket,slave_port)
            else:
                LOGGER.warning(
                    "Unexpected return: Received none from choose_new_master."
                )
        else:
            LOGGER.info("len (slave sockets) is 0")
            LOGGER.info("No slave servers available to promote to master.")

        


    def send_heartbeat(self):  
        try:
            if self.master_socket:
                heartbeat_message = proto.InitConnection()
                heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                heartbeat_message.is_heartbeat = True
                LOGGER.debug(
                    f"Sending... heartbeat to master server {self.master_socket}"
                )
                if not send(self.master_socket, heartbeat_message.SerializeToString()):
                    LOGGER.warning(f"Failed to send heartbeat request to master server")
                else:
                    # Start a timer
                    self.heartbeat_timer = threading.Timer(
                        self.heartbeat_timeout, self.handle_heartbeat_timeout
                    )
                    self.heartbeat_timer.start()
        except Exception as e:
            LOGGER.warning("Error sending heartbeat:", e)
            self.handle_heartbeat_timeout()  # Trigger timeout handling

    # Define a function for sleeping and sending heartbeat
    def handle_heartbeat_response(self):
        # LOGGER.debugv("Received heartbeat response from master server.")
        # Cancel the timer if it's still running
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel()

        time.sleep(self.heartbeat_interval)
        self.send_heartbeat()

    def handle_heartbeat_timeout(self):
        LOGGER.info("Heartbeat response timed out.")
        self.master_socket = None
        if len(self.slave_sockets) > 0:
            LOGGER.debug("Number of slave sockets: %d", len(self.slave_sockets))
            (new_master_socket,slave_port) = self.choose_new_master()
            if new_master_socket:
                self.promote_slave_to_master(new_master_socket,slave_port)
            else:
                LOGGER.warning(
                    "Unexpected return: Received none from choose_new_master."
                )
        else:
            LOGGER.info("len (slave sockets) is 0")
            LOGGER.info("No slave servers available to promote to master.")

    def send_receive_on_socket(self, slave_socket, slave_host, slave_port):
        """Is called in choose_new_master. Send a heartbeat request to a slave server and waits to receive "slave_last_backup_timestamp" as the response."""
        # Send request for heartbeat
        request_heartbeat = TrackNet_pb2.InitConnection()
        request_heartbeat.sender = TrackNet_pb2.InitConnection.Sender.PROXY
        request_heartbeat.is_heartbeat = True
        try:

            if not send(slave_socket, request_heartbeat.SerializeToString()):
                LOGGER.warning(f"failed to send heatbeat request to slave socket: {slave_socket}")
            else:
                # Wait for self.slave_heartbeat_timeout seconds or until the slave sent its timestamp
                start_time = time.time()
                timestampReceived = False
                while (((time.time() - start_time) <= self.slave_heartbeat_timeout) and (timestampReceived == False)):
                    if self.all_slave_timestamps.get((slave_host, slave_port), 0) != 0:
                        timestampReceived = True
                    time.sleep(0.1)  # Sleep for a short time to avoid busy waiting
                
                # if timestampReceived == False:
                #     if (slave_host, slave_port) in self.all_slave_timestamps:
                #         del self.all_slave_timestamps[(slave_host, slave_port)]
                #     else:
                #         LOGGER.debug(f"Key {(slave_host, slave_port)} not found in all_slave_timestamps.")
                
        except Exception as e:
            LOGGER.warning(
                f"Error in send_receive_on_socket on socket {slave_socket}: {e}"
            )

    def choose_new_master(self):
        self.all_slave_timestamps = {}

        # List to hold all thread objects
        threads = []

        for ((slaveHost,slavePort),slave_socket) in self.slave_sockets.items():
            # Create a new Thread for each slave socket to send and receive messages
            self.all_slave_timestamps[(slaveHost,slavePort)] = 0

            thread = threading.Thread(
                target=self.send_receive_on_socket,
                args=(slave_socket,slaveHost, slavePort),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        LOGGER.debug("-----------Priniting all the slave timestamps-----------")
        for key, value in self.all_slave_timestamps.items():
            LOGGER.debug(f"Key: {key}, Value: {value}")

        # After all threads complete, you can process the timestamps
        if self.all_slave_timestamps:
            max_key = max(self.all_slave_timestamps, key=self.all_slave_timestamps.get)
            LOGGER.debug(f"key chosen {max_key}")
            (chosen_slave_host,chosen_slave_port) = max_key
            LOGGER.info(f"New master chosen in choose_new_master based on timestamp: {(chosen_slave_host,chosen_slave_port)}" )
            try:
                ip_address = socket.gethostbyname(chosen_slave_host)
                LOGGER.debug(f"The IP address of {chosen_slave_host} is {ip_address}")
                most_recent_slave = (ip_address,chosen_slave_port)

                LOGGER.debug("-----------Priniting all the slave sockets-----------")
                for key, value in self.slave_sockets.items():
                    LOGGER.debug(f"Key: {key}, Value: {value}")

                if (most_recent_slave) in self.slave_sockets:
                    return (self.slave_sockets[(most_recent_slave)],chosen_slave_port)
                else:
                    LOGGER.warning(f"Error cannot find the socket for the slave chosen {most_recent_slave}") 
            except socket.gaierror as e:
                print(f"Failed to get the IP address of {chosen_slave_host}: {e}")
                return None
        else:
            LOGGER.warning("No timestamps received, cannot select a new master.")
            return None

    def handle_connection(self, conn: socket.socket, address):
        try:
            # Convert address to a string key
            client_key = f"{address[0]}:{address[1]}"
            with self.lock:
                self.client_sockets[client_key] = conn

            LOGGER.debug(f"New connection handled in thread {client_key}")

            while not exit_flag:
                data = receive(conn)
                try:
                    if data:
                        init_conn = proto.InitConnection()
                        init_conn.ParseFromString(data)

                        if init_conn.sender == proto.InitConnection.Sender.CLIENT:
                            
                            self.relay_client_state(init_conn.client_state)

                        elif (init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER):

                            if self.master_socket_hostIP != conn.getpeername()[0]:
                                LOGGER.warning(
                                    f"Received message with sender type master from NON master server."
                                )

                            if init_conn.HasField("server_response"):
                                self.relay_server_response(init_conn.server_response)

                            elif init_conn.HasField("is_heartbeat") and self.is_main:
                                LOGGER.debugv(
                                    "Received heartbeat from master server. Sending response..."
                                )
                                
                                #self.handle_heartbeat_response_loop()
                                LOGGER.debug(f"Recived heartbeat from master server. checking if timer running")
                                if self.heartbeat_timer and self.heartbeat_timer.is_alive():
                                    LOGGER.debug(f"Timer is still running, will cancel timer")
                                    self.heartbeat_timer.cancel()

                                # send heartbeat
                                # LOGGER.debug(
                                #     "Creating Thread to handle heartbeat response which calls: handle_heartbeat_response "
                                # )
                                #threading.Thread(target=self.handle_heartbeat_response, daemon=True).start()

                            else:
                                LOGGER.warning(
                                    f"Proxy received msg from master with missing content {init_conn}"
                                )
                        elif (init_conn.sender == proto.InitConnection.Sender.SERVER_SLAVE):
                            
                            if init_conn.HasField("slave_details"):

                                if self.is_main:
                                    self.slave_role_assignment(conn, init_conn)
                                else:
                                    slave_port = init_conn.slave_details.port
                                    self.add_slave_socket(conn,slave_port)

                            elif init_conn.HasField("slave_backup_timestamp"):
                                LOGGER.debug(f"Message received from slave socket has a last backup timestamp response: {init_conn}")
                                try:    
                                    timestamp = init_conn.slave_backup_timestamp.timestamp
                                    slave_host = init_conn.slave_backup_timestamp.host
                                    slave_port = init_conn.slave_backup_timestamp.port
                                    self.all_slave_timestamps[(slave_host,slave_port)] = timestamp
                                except Exception as e:
                                    LOGGER.warning(f"Error handling slaves backup response {init_conn} socket: {conn}")
                            else:
                                LOGGER.debug(f"proxy recieved an init connection with no salve details and no slave_backup_timestamp: init_conn")


                        elif (
                            init_conn.sender == proto.InitConnection.Sender.PROXY
                            and self.is_main
                        ):
                            ## add bool for backup is up
                            LOGGER.debugv("Received message from backup proxy")
                            heartbeat = proto.Response()
                            heartbeat.code = proto.Response.Code.HEARTBEAT

                            # nofity backup proxy who the master server is
                            try:
                                master_host, _ = self.master_socket.getpeername()
                                heartbeat.master_host = master_host
                                LOGGER.debugv("Setting master host to %s", master_host)

                            except Exception as e:
                                LOGGER.debugv(
                                    "Master server not connected. Unable to set master host"
                                )

                            if not send(conn, heartbeat.SerializeToString()):
                                LOGGER.warning(
                                    f"Failed to send heartbeat to backup proxy."
                                )

                except Exception as e:
                    LOGGER.error(traceback.format_exc())
                    break

        except socket.timeout:
            LOGGER.warning(f"socket timed out.")

        with self.lock:
            if client_key in self.client_sockets:
                del self.client_sockets[client_key]  # Remove client from mapping

            if conn == self.master_socket:
                self.master_socket = None
                LOGGER.warning("Master server connection lost.")

            elif client_key in self.slave_sockets:
                del self.slave_sockets[client_key]
                LOGGER.warning("Slave server connection lost.")

        if conn is not None:
            conn.close()

    def shutdown(self, proxy_listening_sock: socket.socket):
        with self.lock:
            if proxy_listening_sock is not None:
                proxy_listening_sock.shutdown(socket.SHUT_RDWR)
                proxy_listening_sock.close()
            for socket in self.socket_list:
                socket.shutdown(socket.SHUT_RDWR)
                socket.close()
            self.socket_list.clear()
            self.client_sockets.clear()
            LOGGER.info(f"Proxy {self.host}{self.port} shut down")

    def run(self):
        while not exit_flag:
            proxy_listening_sock = create_server_socket(self.host, self.port)

            if proxy_listening_sock is None:
                LOGGER.warning(f"Failed to create proxy-to-proxy listening port.")
                time.sleep(5)
                continue

            self.socket_list.append(proxy_listening_sock)
            LOGGER.info(f"Proxy listening on {self.host}:{self.port}")

            while not exit_flag:
                try:
                    # select.select(socks to monitor for incoming data, socks to write to, socks to monitor for exceptions, timeout value)
                    read_sockets, _, _ = select.select(
                        [proxy_listening_sock], [], [], 0.5
                    )  #

                    if len(read_sockets) > 0:
                        conn, addr = proxy_listening_sock.accept()
                        # Pass both socket and address for easier client management
                        threading.Thread(
                            target=self.handle_connection,
                            args=(conn, addr),
                            daemon=True,
                        ).start()

                    # check for a master if there is one start a new thread for making sure it is alive

                except Exception as exc:
                    LOGGER.error(f"run(): {exc}")

        LOGGER.info("Shutting down...")
        self.shutdown(proxy_listening_sock)
        proxy_listening_sock.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Proxess Proxy args")

    parser.add_argument("-proxy_addres", type=str, help="Address for proxy")
    parser.add_argument("-proxyPort", type=int, help="Proxy port number")
    parser.add_argument("-listeningPort", type=int, help="Listening port number")

    # Add the flags for main and backup
    parser.add_argument("-main", action="store_true", help="Set mode to main")
    parser.add_argument("-backup", action="store_true", help="Set mode to backup")

    args = parser.parse_args()


    proxy_address = args.proxy_addres
    proxy_port_num = args.proxyPort
    listening_port_num = args.listeningPort

    # Determine the mode based on the flags
    isMain = args.main
    isBackup = args.backup

    # Main proxy address and port
    LOGGER.debug(f"Proxy address {proxy_address}")
    LOGGER.debug(f"Proxy port number {proxy_port_num}")
    LOGGER.debug(f"Listening port {listening_port_num}")
    LOGGER.debug(f"Main: {isMain} and Backup: {isBackup}")

    if isMain and isBackup:
        print("Passed both -main and -backup. Proxy can not be both")
    else:

        if proxy_port_num == None:
            proxy_port_num = 5555

        if listening_port_num == None:
            listening_port_num = 5555

        proxy = Proxy(
            mainProxyAddress=proxy_address,
            proxy_port=proxy_port_num,
            listening_port=listening_port_num,
            is_main=isMain,
        )
        try:
            proxy.run()
        except KeyboardInterrupt:
            LOGGER.info("Keyboard interupt detected")
