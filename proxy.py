from datetime import datetime
import os
import select
import socket
import threading
import TrackNet_pb2
import TrackNet_pb2 as proto
import traceback
import TrackNet_pb2
import logging
import sys
from utils import *
import argparse
import time 
import signal

# Global Variables
proxy_address = None
proxy_port_num = None
listening_port_num = None
isMain = None
isBackup = None


setup_logging()  ## only need to call at main entry point of application

LOGGER = logging.getLogger("Proxy")

#signal.signal(signal.SIGTERM, exit_gracefully)
#signal.signal(signal.SIGINT, exit_gracefully)

class Proxy:
    """Manages network connections for a railway simulation proxy, handling communication between clients, servers, and other proxies.

    Attributes
    ----------
    host : str
        The hostname of the proxy server.
    port : int
        The listening port number for incoming connections.
    proxy_port : int
        The port number used for proxy-to-proxy communications.
    is_main : bool
        Indicates whether this proxy instance functions as the main proxy.
    master_socket : socket.socket
        The socket object used for communication with the master server.
    slave_sockets : dict
        A dictionary mapping slave proxy addresses to their respective socket objects.
    client_sockets : dict
        A dictionary mapping client addresses to their respective socket objects.
    """
    def __init__(self,proxy_port=5555,listening_port=5555,is_main=False,mainProxyAddress=list(proxy_details.items())[0][0]):
        """Initializes the Proxy instance with the specified proxy port, listening port, and mode (main or backup).

        :param proxy_port: The port number for proxy communications. Defaults to 5555.
        :param listening_port: The port number for listening to incoming connections. Defaults to 5555.
        :param is_main: A boolean indicating whether the proxy operates as the main proxy. Defaults to False.
        :param mainProxyAddress: The address of the main proxy. This is necessary for backup proxies to know where to connect.
        """
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

        self.heartbeat_interval = 4
        self.heartbeat_timeout = 3
        self.slave_heartbeat_timeout = 2

        self.proxy_time = None
        self.adjusted_offset = None
        
        self.is_main = is_main
        if is_main:
            self.main_proxy_host = self.host
        else:
            self.main_proxy_host = mainProxyAddress

        self.heartbeat_attempts = 0
        self.max_heartbeat_attempts = 0
        self.heartbeat_timer = None
        self.master_server_heartbeat_thread = threading.Thread(target=self.send_heartbeat_to_master_loop, daemon=True)
        if self.is_main:
            self.master_server_heartbeat_thread.start()
        # self.set_main_proxy_host()

        self.all_slave_timestamps = {}
        threading.Thread(target=self.proxy_to_proxy, daemon=True).start()

    def set_main_proxy_host(self):
        """Sets the hostname for the main proxy based on the proxy's 
        operational mode and provided configuration. """
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

    def cleanSlaveSockets(self):
        for ((slave_host,slave_port),time) in self.all_slave_timestamps.items(): 
            if time == -1:
                try:
                    del self.slave_sockets[(slave_host,slave_port)]
                    LOGGER.debug(f"Deleted slave ({slave_host},{slave_port}) as no longer connected")
                except KeyError:
                    LOGGER.debug(f"Could not delete slave ({slave_host},{slave_port}) due to key error")
                except Exception as e:
                    LOGGER.debug(f"Could not delete slave ({slave_host},{slave_port}) due to unexpected exception: {e}")



    def add_slave_socket(self, slave_socket: socket.socket, slave_port: int):
        """Registers a new slave proxy connection by adding its socket and port to the 
        ``slave_sockets`` dictionary.

        :param slave_socket: The socket object associated with the slave proxy connection.
        :param slave_port: The port number of the slave proxy.
        """
        self.slave_sockets[(f"{slave_socket.getpeername()[0]}",slave_port)] = slave_socket
        LOGGER.debug(f"Slave ({slave_socket.getpeername()[0]},{slave_port}) added")

    def remove_slave_socket(self, slave_socket: socket.socket,slave_port: int):
        """Removes a slave proxy connection from the ``slave_sockets`` dictionary based on
        its socket object.

        :param slave_socket: The socket object associated with the slave proxy to be removed.
        :param slave_port: The port number of the slave proxy to be removed.
        """
        try:
            del self.slave_sockets[(slave_socket.getpeername()[0],slave_port)]
        except KeyError:
            pass
        except Exception as exc:
            LOGGER.warning(f"Error removing slave socket from list of slaves: {exc}")

    def relay_client_state(self, client_state: TrackNet_pb2.ClientState):
        """Forwards a client state message from a client to the master server.

        :param client_state: A protobuf message containing the state of a client.
        """
        LOGGER.info("Relaying a client state")
        LOGGER.debug(f"{client_state}")
        # Extract the target client's IP and port
        target_client_key = (f"{client_state.client.host}:{client_state.client.port}")
        self.client_state_handled[target_client_key] = (client_state,False) 

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

            if not send(self.master_socket, new_message.SerializeToString()):
                LOGGER.warning(f"Failed to send client state message to master.")
            else:
                LOGGER.debug("client state forwaded to master server")
                
        else:
            LOGGER.warning("There is currently no master server")

    def relay_server_response(self, server_response: TrackNet_pb2.ServerResponse):
        """Forwards a server response from the master server to the appropriate client 
        based on the client's address.

        :param server_response: A protobuf message containing a response from the master server.
        """
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

            LOGGER.debug(f"Relaying server response message to client: {target_client_key}")
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
        """Promotes a slave proxy to the role of master proxy. This involves updating the ``master_socket`` to the provided slave socket.

        :param slave_socket: The socket object of the slave proxy being promoted.
        :param slave_port: The port number of the slave proxy being promoted.
        """
        self.master_socket = slave_socket
        LOGGER.debugv(f"master socket was updated: {self.master_socket}")
        try:
            self.master_socket_hostIP = slave_socket.getpeername()[0]
        except Exception as e:
            LOGGER.warning(f"Exception {e} was thrown when setting master_socket_hostIP ")

        self.remove_slave_socket(self.master_socket,slave_port)
        LOGGER.info(f"Promoting {self.master_socket_hostIP} to MASTER, was previously a slave listening on port {slave_port}") #current master socket: {self.master_socket}")
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

            LOGGER.debug("Will send any unhandeled client states to the new master")

            for (client_state,responseSent) in self.client_state_handled.values():
                if responseSent == False:
                    LOGGER.debug(f"Found unhandled client state")
                    self.relay_client_state(client_state)

        else:
            LOGGER.warning(f"Failed to send role assignmnet to newly elected master.")       

    def notify_master_of_new_slave(self, init_conn: TrackNet_pb2.InitConnection):
        """Notifies the master server about a new slave server connection. This method constructs a 
        message with the new slave server's details and sends it to the master server.

        :param init_conn: An ``InitConnection`` protobuf message containing the details of the newly connected slave server.
        """
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
        """Sends the details of all connected slave servers to the master server. 
        This method is typically called to update the master server with a 
        comprehensive list of slave servers upon certain events."""
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

    def slave_role_assignment(self, slave_socket: socket.socket, init_conn: TrackNet_pb2.InitConnection):
        """Assigns a role to a newly connected slave server. If there is no master server, 
        the first connected slave is promoted to master. Otherwise, the new slave is simply
        added to the list of slave servers.

        :param slave_socket: The socket object associated with the newly connected slave server.
        :param init_conn: An ``InitConnection`` protobuf message containing the details of the slave server.
        """
        slave_host = init_conn.slave_details.host
        slave_port = init_conn.slave_details.port

        with self.lock:
            # Check if there is no master server, and promote the first slave to master
            if self.master_socket is None:
                LOGGER.debug("No master server so will promote this server as master ")
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
                LOGGER.debug(f"Will sleep for 20 seconds before notifying master of new slave")
                time.sleep(2)
                self.notify_master_of_new_slave(init_conn)

    def handle_missed_proxy_heartbeat(self):
        """Handles situations where a heartbeat message from the main proxy is missed. 
        Increments a counter for missed heartbeats and, if the number of missed heartbeats 
        exceeds a threshold, promotes the backup proxy to the main proxy role.

        :return: A boolean indicating whether the current proxy has been 
            promoted to the main proxy role.
        """
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
        """Manages the connection between backup and main proxies. A backup proxy attempts 
        to connect to the main proxy. If the connection fails repeatedly, the backup proxy 
        may assume the role of the main proxy."""
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
        """Listens for messages from the main proxy, maintaining a heartbeat connection. 
        This method is responsible for ensuring that the backup proxy remains updated 
        about the status of the main proxy and takes action if the main proxy fails.

        :param proxy_sock: The socket object used for communication with the main proxy.
        """
        LOGGER.info("Keeping heartbeat with main proxy ...")

        while not self.is_main:
            heartbeat_message = proto.InitConnection()
            heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
            heartbeat_message.is_heartbeat = True

            if send(proxy_sock, heartbeat_message.SerializeToString()):
                LOGGER.debugv("Sent heartbeat message to main proxy.")
                
            else:
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
                        #LOGGER.info(f"slave sockets: {self.slave_sockets}, items: {self.slave_sockets.items()}")
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
                                        LOGGER.debug(f"Master server updated to {heartbeat.master_host}")
                                except Exception as e:
                                    LOGGER.warning(f"Exception {e} was thrown when finding master server from slaves")

                        if foundMasterServer == False:
                            LOGGER.warning(
                                f"BackUp Proxy doesn't have connection to the master server ? {heartbeat.master_host}"
                            )
                        else:
                            self.remove_slave_socket(self.master_socket,slave_port_chosen)
                            LOGGER.debug("Will send any unhandeled client states to the new master")
                            for (client_state,responseSent) in self.client_state_handled.values():
                                if responseSent == False:
                                    LOGGER.debug(f"Found unhandled client state")
                                    self.relay_client_state(client_state)

                time.sleep(self.heartbeat_interval)
            else:
                LOGGER.debug("No data received from main")
                if self.handle_missed_proxy_heartbeat():
                    LOGGER.info("IS MAIN PROXY")

    def send_heartbeat_to_master_loop(self):
        """Initiates a loop that sends heartbeat messages to the master server at regular 
        intervals. If the master server becomes unresponsive, it triggers a timeout handling 
        procedure."""
        LOGGER.debug(f"Sending heartbeat thread started: ")
        while not exit_flag:
            
            if self.heartbeat_timer and self.heartbeat_timer.is_alive():
                LOGGER.debug(f"sent a heartbeat already and timer running {self.master_socket} {self.heartbeat_timer}")
            else:
                try:
                    if self.master_socket is not None:
                        LOGGER.debugv(f"master socket: {self.master_socket} ")
                        if self.master_socket.fileno() < 0:
                            LOGGER.warning(f"File descriptor for socket is negative. Assume master server is down: {self.master_socket} ")
                            self.handle_heartbeat_timeout_loop()
                        else:
                            heartbeat_message = proto.InitConnection()
                            heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                            heartbeat_message.is_heartbeat = True

                            # Start a timer
                            LOGGER.debugv("Starting timer right before sending heartbeat:")
                            self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.handle_heartbeat_timeout_loop)
                            LOGGER.debugv(f"if daemon on the heartbeat timer {self.heartbeat_timer.daemon}")
                            self.heartbeat_timer.start()

                            LOGGER.debugv(f"Sending... heartbeat to master server {self.master_socket}")

                            if not send(self.master_socket, heartbeat_message.SerializeToString()):
                                LOGGER.warning(f"Failed to send heartbeat request to master server {self.master_socket} FD: {self.master_socket.fileno()}")
                                self.heartbeat_timer.cancel()
                                self.handle_heartbeat_timeout_loop()
                            else:
                                LOGGER.debugv(f"Sent heartbeat to master {self.master_socket} ")
                                #self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.handle_heartbeat_timeout_loop)
                                #self.heartbeat_timer.start()       
                    else:
                        LOGGER.debugv(f"No master server: {self.master_socket} so won't send a heartbeat")

                except Exception as e:
                    LOGGER.warning(f"Error sending heartbeat to maser server: {e}")
                    self.heartbeat_timer.cancel()
                    self.handle_heartbeat_timeout_loop()  # Trigger timeout handling 

            time.sleep(self.heartbeat_interval)         
            
    def handle_heartbeat_response_loop(self):
        """Handles the response to the heartbeat message sent by the proxy. If a heartbeat 
        response is received from the master server, the associated timer is canceled to 
        prevent the timeout handling procedure."""
        # LOGGER.debugv("Received heartbeat response from master server.")
        # Cancel the timer if it's still running
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel()


    def handle_heartbeat_timeout_loop(self):
        """Handles the scenario when a heartbeat response is not received from the 
        master server within a specified timeout period. This method may involve 
        promoting a slave server to the master or taking other recovery actions.
        """
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel()
        with self.lock:
            LOGGER.info("Heartbeat response timed out. Stop sending hearbeat by setting master socket to none")
            #self.master_server_heartbeat_thread
            try:
                self.master_socket.close()
            except Exception as e:
                LOGGER.debug(f"exception thrown when closing socket {e}")
            self.master_socket = None

        if len(self.slave_sockets) > 0:
            LOGGER.debug("Number of slave sockets: %d", len(self.slave_sockets))
            chosenTuple = self.choose_new_master()

            if chosenTuple != None :
                (new_master_socket,slave_port) = chosenTuple
                self.promote_slave_to_master(new_master_socket,slave_port)
            else:
                LOGGER.debug("Unable to promote a master from current list of slaves.")
                
            # clean the dictionary with the slave sockets after sending hearbeat to slave servers 
            self.cleanSlaveSockets()

                
        else:
            LOGGER.info("len (slave sockets) is 0")
            LOGGER.info("No slave servers available to promote to master.")

    def send_heartbeat_to_slaves(self, slave_socket, slave_host, slave_port):
        """Sends a heartbeat message to a slave server to verify its responsiveness. 
        This method is part of the mechanism for monitoring the health of slave servers 
        and choosing a new master server if necessary.

        Called in choose_new_master.

        :param slave_socket: The socket object used for communication with the slave server.
        :param slave_host: The hostname of the slave server.
        :param slave_port: The port number of the slave server.
        """
        # Send a heartbeat request to a slave server and waits to receive "slave_last_backup_timestamp" as the response."""
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
                    if self.all_slave_timestamps.get((slave_host, slave_port), 0) != (-1):
                        timestampReceived = True
                    time.sleep(0.1)  # Sleep for a short time to avoid busy waiting
                
        except Exception as e:
            LOGGER.warning(f"Error in send_heartbeat_to_slaves on socket {slave_socket}: {e}")

    def choose_new_master(self):
        """Chooses a new master server from the list of connected slave servers based on their 
        last known states or other criteria. This method is invoked when the current master 
        server becomes unresponsive or otherwise needs to be replaced."""
        self.all_slave_timestamps = {}

        # List to hold all thread objects
        threads = []

        for ((slaveHost,slavePort),slave_socket) in self.slave_sockets.items():
            # Create a new Thread for each slave socket to send and receive messages
            self.all_slave_timestamps[(slaveHost,slavePort)] = (-1)

            thread = threading.Thread(
                target=self.send_heartbeat_to_slaves,
                args=(slave_socket,slaveHost, slavePort),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # LOGGER.debug("-----------Priniting all the slave timestamps-----------")
        # for key, value in self.all_slave_timestamps.items():
        #     LOGGER.debug(f"Key: {key}, Value: {value}")

        # After all threads complete, you can process the timestamps
        if self.all_slave_timestamps:
            max_key = max(self.all_slave_timestamps, key=self.all_slave_timestamps.get)
            if(self.all_slave_timestamps[max_key] == (-1)):
                # then no slave is connected
                LOGGER.debug(f"All slaves are dead, will not be able to promote a slave to master server")
                return None
            else:
                LOGGER.debug(f"key chosen {max_key}")
                (chosen_slave_host,chosen_slave_port) = max_key
                LOGGER.info(f"New master chosen in choose_new_master based on timestamp: {(chosen_slave_host,chosen_slave_port)}" )
                try:
                    ip_address = socket.gethostbyname(chosen_slave_host)
                    LOGGER.debugv(f"The IP address of {chosen_slave_host} is {ip_address}")
                    most_recent_slave = (ip_address,chosen_slave_port)

                    # LOGGER.debug("-----------Priniting all the slave sockets-----------")
                    # for key, value in self.slave_sockets.items():
                    #     LOGGER.debug(f"Key: {key}, Value: {value}")

                    if (most_recent_slave) in self.slave_sockets:
                        return (self.slave_sockets[(most_recent_slave)],chosen_slave_port)
                    else:
                        LOGGER.warning(f"Error cannot find the socket for the slave chosen {most_recent_slave}") 
                except socket.gaierror as e:
                    LOGGER.warning(f"Failed to get the IP address of {chosen_slave_host}: {e}")
                except Exception as e:
                    LOGGER.warning(f"Unexpected exception when choossing new slave {max_key}:{self.all_slave_timestamps[max_key]}: {e}")
                    return None
        else:
            LOGGER.warning("No timestamps received, cannot select a new master.")
            return None

    def handle_connection(self, conn: socket.socket, address):
        """Manages incoming connections on the proxy server, handling data transmission between 
        clients, the master server, and slave servers. This method is responsible for routing 
        messages and maintaining the proxy's internal state.

        :param conn: The socket object representing the connection.
        :param address: The address of the connecting entity.
        """
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
                            LOGGER.debug(f"Received a client state from client")
                            self.relay_client_state(init_conn.client_state)

                        elif (init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER):

                            if self.master_socket is None:
                                LOGGER.debug("Received heartbeat from master server when it set to None")

                            if self.master_socket_hostIP != conn.getpeername()[0]:
                                LOGGER.warning(f"Received message with sender type master from NON master server.")

                            if init_conn.HasField("server_response"):
                                self.relay_server_response(init_conn.server_response)

                            if init_conn.HasField("is_heartbeat") and self.is_main:
                                LOGGER.debugv(f"Received heartbeat from master server. Sending response...")
                                
                                #self.handle_heartbeat_response_loop()
                                LOGGER.debugv(f"Recived heartbeat from master server. checking if timer running")
                                if (self.heartbeat_timer is not None) and self.heartbeat_timer.is_alive():
                                    LOGGER.debugv(f"Timer is still running, will cancel timer")
                                    self.heartbeat_timer.cancel()
                                

                                # send heartbeat
                                # LOGGER.debug(
                                #     "Creating Thread to handle heartbeat response which calls: handle_heartbeat_response "
                                # )
                                #threading.Thread(target=self.handle_heartbeat_response, daemon=True).start()

                            #else:
                                #LOGGER.warning(f"Proxy received msg from master with missing content {init_conn}")

                        elif (init_conn.sender == proto.InitConnection.Sender.SERVER_SLAVE):
                            
                            if init_conn.HasField("slave_details"):

                                if self.is_main:
                                    LOGGER.debug(f"Slave server has connect, will now decide its role")
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

                            if send(conn, heartbeat.SerializeToString()):
                                LOGGER.debugv("Sent heartbeat response to backup proxy")
                            else:
                                LOGGER.warning(f"Failed to send heartbeat to backup proxy.")

                except Exception as e:
                    LOGGER.debug("Exception thrown in handle connection loop")
                    LOGGER.error(traceback.format_exc())
                    break

        except socket.timeout:
            LOGGER.warning(f"socket timed out.")

        LOGGER.debug(f"handle connection thread closing")
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
        """Gracefully shuts down the proxy server, closing all active connections 
        and cleaning up resources.

        :param proxy_listening_sock: The main listening socket of the proxy 
            server to be closed.
        """
        with self.lock:
            try:
                proxy_listening_sock.shutdown(socket.SHUT_RDWR)
                proxy_listening_sock.close() 
            except Exception:
                pass
            for socket in self.socket_list:
                try: 
                    socket.shutdown(socket.SHUT_RDWR)
                    socket.close()
                except Exception:
                    pass

            self.socket_list.clear()
            self.client_sockets.clear()
            LOGGER.info(f"Proxy {self.host}{self.port} shut down")

    def run(self):
        """Starts the proxy server, listening for incoming connections and handling them 
        according to their type (client, master server, or slave server). This method 
        implements the main loop of the proxy server."""
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
                    
                    read_sockets, _, _ = select.select([proxy_listening_sock], [], [], 0.5)  #

                    if len(read_sockets) > 0:
                        
                        conn, addr = proxy_listening_sock.accept()
                        # Pass both socket and address for easier client management
                        #print("--------------------handle connection thread is called and started")
                        threading.Thread(
                            target=self.handle_connection,
                            args=(conn, addr),
                            daemon=True,
                        ).start()

                    # check for a master if there is one start a new thread for making sure it is alive

                except Exception as exc:
                    LOGGER.error(f"run(): threw an exception {exc}")

        LOGGER.info("Shutting down...")
        self.shutdown(proxy_listening_sock)
        


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
    LOGGER.debugv(f"Proxy address {proxy_address}")
    LOGGER.debugv(f"Proxy port number {proxy_port_num}")
    LOGGER.debugv(f"Listening port {listening_port_num}")
    LOGGER.debugv(f"Main: {isMain} and Backup: {isBackup}")

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
            sys.exit(1)
        
