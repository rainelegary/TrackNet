import select
import socket
import threading
import TrackNet_pb2
import TrackNet_pb2 as proto
import utils
import traceback
import time
import TrackNet_pb2
import logging
import sys
import time
from utils import *

setup_logging() ## only need to call at main entry point of application

LOGGER = logging.getLogger("Proxy")


class Proxy:
    def __init__(self, host, port, is_main=False):
        self.host = host
        self.port = port
        self.proxy_port = port
        self.master_socket = None
        self.slave_sockets = {}
        self.client_sockets = {}  # Map client address (IP, port) to socket for direct access
        self.socket_list = []
        self.lock = threading.Lock()
        self.heartbeat_interval = 10
        self.heartbeat_timeout = 10

        self.is_main = is_main
        self.main_proxy_host = None
        self.listen_to_proxy_called = False

        self.heartbeat_attempts = 0
        self.max_heartbeat_attempts = 3

        self.set_main_proxy_host()

        threading.Thread(target=self.proxy_to_proxy, daemon=True).start()


    def set_main_proxy_host(self):
        print ("in set_main_proxy_host ", self.is_main)
        if self.is_main:
            self.main_proxy_host = self.host
        else:
            for proxy, _ in proxy_details.items():
                if proxy != self.host:
                    self.main_proxy_host = proxy
                else:
                    print ("proxy is the same as self.host")

        print ("self main_proxy_host: ", self.main_proxy_host)
        ## case where only one proxy and command-line arg main missing
        if self.main_proxy_host is None:
            LOGGER.warning(f"Only one proxy? setting as main proxy")
            self.main_proxy_host = self.host
            self.is_main = True
        

    def add_slave_socket(self, slave_socket: socket.socket):
        self.slave_sockets[f"{slave_socket.getpeername()[0]}"] = slave_socket
        LOGGER.debug(f"Slave {slave_socket.getpeername()[0]} added")

    def remove_slave_socket(self, slave_socket:socket.socket):
        try:
            del self.slave_sockets[slave_socket.getpeername()[0]]
        except KeyError:
            pass

    def relay_client_state(self, client_state: TrackNet_pb2.ClientState):
        with self.lock:
            if self.master_socket is not None:
                new_message = proto.InitConnection()
                new_message.sender = proto.InitConnection.Sender.PROXY
                new_message.client_state.CopyFrom(client_state)
                if not send(self.master_socket, new_message.SerializeToString()):
                    LOGGER.warning(f"Failed to send client state message to master.")
                else:
                    LOGGER.debug("client state forwaded to master server")
            else:
                LOGGER.warning("There is currently no master server")

    def relay_server_response(self, server_response: TrackNet_pb2.ServerResponse):
       with self.lock:
            LOGGER.debug(f"Received message from master server, ip:{server_response.client.host} port:{server_response.client.port}")

            # Extract the target client's IP and port
            target_client_key = f"{server_response.client.host}:{server_response.client.port}"
            target_client_socket = self.client_sockets.get(target_client_key)

            relay_resp = proto.InitConnection()
            relay_resp.sender = proto.InitConnection.Sender.PROXY
            relay_resp.server_response.CopyFrom(server_response)
            LOGGER.debug("Relaying server response message to client ...")

            # Forward the server's message to the target client
            if target_client_socket:
                if not send(target_client_socket, relay_resp.SerializeToString()):
                    LOGGER.warning(f"Failed to send server response message to client")
            else:
                LOGGER.warning(f"Target client {target_client_key} not found.")

    def promote_slave_to_master(self, slave_socket: socket.socket):
        self.master_socket = slave_socket
        #LOGGER.info(f"{slave_socket.getpeername()} promoted to MASTER")

        # notify the newly promoted master server of its new role
        role_assignment = proto.ServerAssignment()
        role_assignment.is_master = True

        if len(self.slave_sockets) <= 0:
            LOGGER.info("No slaves to send to master")

        # Send slave details to master server
        for slave_ip, _ in self.slave_sockets.items():
            slave_details = role_assignment.servers.add()
            slave_details.host = slave_ip
            slave_details.port = slave_to_master_port
            #LOGGER.info(f"Adding {slave_ip}:{slave_to_master_port} to list of slaves")

        if send(slave_socket, role_assignment.SerializeToString()):
            LOGGER.debug(f"Sent role assignmnet to newly elected master.")
        else:
            LOGGER.warning(f"Failed to send role assignmnet to newly elected master.")

        ##TODO recv ACK

        # remove new master from list of slaves
        #self.remove_slave_socket(slave_socket)

        LOGGER.debug ("sending heartbeat to new master server")
        #threading.Thread(target=self.send_heartbeat, args=(self.master_socket,), daemon=True).start()
        self.send_heartbeat(self.master_socket)


    def notify_master_of_new_slave(self, init_conn: TrackNet_pb2.InitConnection):
        # Notify master of new slave server so it can connect to it
        slave_host = init_conn.slave_details.host
        slave_port = init_conn.slave_details.port

        #Create protobuf response
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

    def slave_role_assignment(self, slave_socket: socket.socket, init_conn: TrackNet_pb2.InitConnection):
        with self.lock:
            # Check if there is no master server, and promote the first slave to master
            if self.master_socket is None:
                self.promote_slave_to_master(slave_socket)

            # Already have master so assign slave role
            else:
                self.add_slave_socket(slave_socket)

                role_assignment = proto.ServerAssignment()
                role_assignment.is_master = False
                #master_ip, _ = self.master_socket.getpeername()
                #master_details = role_assignment.servers.add()
                #master_details.host = master_ip
                #master_details.port = slave_to_master_port

                if not send(slave_socket, role_assignment.SerializeToString()):
                    LOGGER.warning(f"Failed to send role assignmnet to slave.")

                #self.notify_master_of_slaves()
                self.notify_master_of_new_slave(init_conn)



    def handle_missed_proxy_heartbeat(self):
        self.heartbeat_attempts += 1

        if self.heartbeat_attempts >= self.max_heartbeat_attempts:
            self.is_main = True
            ## TODO handle main proxy failure


    def proxy_to_proxy(self):
        print ("in proxy to proxy")
        connected_to_proxy = False

        if not self.is_main:
            LOGGER.debug ("Before connecting to main proxy")
            while not connected_to_proxy:
                proxy_sock = create_client_socket(self.main_proxy_host, self.proxy_port)

                if proxy_sock:
                    connected_to_proxy = True
                    LOGGER.debug ("Connected to main proxy")
                    self.socket_list.append(proxy_sock)

                else:
                    LOGGER.warning(f"Failed to connect to main proxy. Trying again in 5 seconds ...")
                    time.sleep(5)
                    self.handle_missed_proxy_heartbeat()

            # Send heartbeat request to main proxy through InitConnection message
            heartbeat_request = proto.InitConnection()
            heartbeat_request.sender = proto.InitConnection.Sender.PROXY
            heartbeat_request.is_heartbeat = True
            if send(proxy_sock, heartbeat_request.SerializeToString()):
                LOGGER.debug("Sent heartbeat request to main proxy.")
                #listen to main_proxy
                print ("calling listen to proxy thread")
                #threading.Thread(target=self.listen_to_main_proxy, args=(proxy_sock,), daemon=True).start()
                self.listen_to_main_proxy(proxy_sock)
            else:
                LOGGER.warning("Failed to send heartbeat request to main proxy.")
        #main proxy responsibilities
        else:
            pass


    def listen_to_main_proxy (self, proxy_sock: socket.socket):
        #Listen to main proxy
        print ("inside listen to main_proxy thread")

        if self.listen_to_proxy_called == True:
            print ("listen_to_main_proxy already called")
            return
        self.listen_to_main_proxy = True
        while True:
            LOGGER.debug ("before receiving anything from main proxy")
            data = receive(proxy_sock)
            LOGGER.debug ("Received something from main proxy")
            if data:
                LOGGER.debug ("data is not none")
                heartbeat = proto.Response()
                heartbeat.ParseFromString(data)

                if heartbeat.code == proto.Response.Code.HEARTBEAT:
                    LOGGER.debug ("received heartbeat")
                    self.handle_missed_proxy_heartbeat()

                if heartbeat.HasField("master_host"):
                    LOGGER.debug ("received master host")
                    # if no master server or new master server
                    if self.master_socket is None or self.master_socket.getpeername()[0] != heartbeat.master_host:
                        for _, slave in self.slave_sockets.items():
                            if slave.getpeername()[0] == heartbeat.master_host:
                                self.master_socket = slave
                                self.remove_slave_socket(slave)
                            else:
                                LOGGER.warning(f"BackUp Proxy doesn't have connections to master server ?")


                LOGGER.debug ("before sleeping 2")
                time.sleep(5)
                LOGGER.debug ("done sleeping 2")

                heartbeat_message = proto.InitConnection()
                heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                heartbeat_message.is_heartbeat = True
                if send(proxy_sock, heartbeat_message.SerializeToString()):
                    LOGGER.debug("Sent heartbeat message to main proxy.")
                else:
                    LOGGER.warning("Failed to send heartbeat message to main proxy.")
            else:
                print ("no data received")

    def proxy_to_proxy_old(self):
        print ("in proxy_to_proxy")
        # if backup proxy
        while not exit_flag:
            if not self.is_main:
                proxy_sock = create_client_socket(self.main_proxy_host, self.proxy_port)

                if proxy_sock is None:
                    LOGGER.warning(f"Failed to connect to main proxy. Trying again in 5 seconds ...")
                    time.sleep(5)
                    self.handle_missed_proxy_heartbeat()
                    continue

                LOGGER.debug ("Connected to main proxy")

                # Send heartbeat request
                heartbeat_request = proto.InitConnection()
                heartbeat_request.sender = proto.InitConnection.Sender.PROXY
                heartbeat_request.is_heartbeat = True

                if not send(proxy_sock, heartbeat_request.SerializeToString()):
                    LOGGER.warning("Failed to send heartbeat request to main proxy.")

                # receive heartbeat response
                data = receive(proxy_sock)

                if data:
                    heartbeat = proto.Response()
                    heartbeat.ParseFromString(data)

                    if heartbeat.code == proto.Response.Code.HEARTBEAT:
                        self.handle_missed_proxy_heartbeat()

                    if heartbeat.HasField("master_host"):
                        # if no master server or new master server
                        if self.master_socket is None or self.master_socket.getpeername()[0] != heartbeat.master_host:
                            for _, slave in self.slave_sockets.items():
                                if slave.getpeername()[0] == heartbeat.master_host:
                                    self.master_socket = slave
                                    self.remove_slave_socket(slave)
                                else:
                                    LOGGER.warning(f"BackUp Proxy doesn't have connections to master server ?")

                ## TODO handle main proxy failure
            else:
                # main proxy does not do anything here i think ??
                break


    def send_heartbeat (self, master_socket):
        LOGGER.debug ("in send_heartbeat function")

        # Start a timer
        self.heartbeat_timer = threading.Timer(self.heartbeat_timeout, self.handle_heartbeat_timeout)
        self.heartbeat_timer.start()
        LOGGER.debug ("heartbeat timer started")

        try:
            if self.master_socket:
                heartbeat_message = proto.InitConnection()
                heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                heartbeat_message.is_heartbeat = True
                LOGGER.debug ("before sending heartbeat to master server")
                if send(self.master_socket, heartbeat_message.SerializeToString()):
                    LOGGER.debug("Sent heartbeat message to master server.")
                else:
                    LOGGER.warning(f"Failed to send heartbeat request to master server")
        except Exception as e:
            print("Error sending heartbeat:", e)
            self.handle_heartbeat_timeout()  # Trigger timeout handling            


    # Define a function for sleeping and sending heartbeat
    def handle_heartbeat_response(self):
        LOGGER.debug(f"In handle_heartbeat_response()")
        print("Received heartbeat response from master server.")
        # Cancel the timer if it's still running
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel() 
            LOGGER.debug("cancelling heartbeat timer")

        LOGGER.debug(f"Sleeping for {self.heartbeat_interval} seconds")
        time.sleep(self.heartbeat_interval)
        self.send_heartbeat(self.master_socket)

    def handle_heartbeat_timeout (self):
        print("Heartbeat response timed out.")
        # Take appropriate action here
        if len(self.slave_sockets) > 0:
            LOGGER.debug("Number of slave sockets: %d", len(self.slave_sockets))
            new_master_socket_key, new_master_socket_value = self.slave_sockets.popitem()
            self.promote_slave_to_master(new_master_socket_value)
        else:
            LOGGER.info("len (slave sockets) is 0")
            LOGGER.info("No slave servers available to promote to master.")   


    def send_heartbeat_old(self, master_socket):
        LOGGER.debug ("in send_heartbeat function")
        if self.master_socket:
            #while not utils.exit_flag and self.master_socket == master_socket:
                #with self.lock:
                    try:
                        heartbeat_message = proto.InitConnection()
                        heartbeat_message.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                        heartbeat_message.is_heartbeat = True
                        LOGGER.debug ("before sending heartbeat to master server")
                        if send(self.master_socket, heartbeat_message.SerializeToString()):
                            LOGGER.debug("Sent heartbeat message to master server.")
                        else:
                            LOGGER.warning(f"Failed to send heartbeat request to master server")

                        # Wait for a response with a timeout
                        LOGGER.debug("Waiting for master server's response.")
                        #ready = select.select([self.master_socket], [], [], self.heartbeat_timeout)
                        #if ready[0]:
                        #    response = utils.receive(self.master_socket)
                        #    if response:
                        #        print("Heartbeat acknowledged by master server.")
                        #        LOGGER.debug(f"Sleeping for {self.heartbeat_interval} seconds")
                        #        time.sleep(self.heartbeat_interval)
                        #    else:
                        #        raise Exception("No heartbeat response from master server.")
                        #else:
                        #    raise Exception("Heartbeat response timed out.")

                    except Exception as e:
                        print("Master server is not responding. Considered dead.")
                        self.master_socket = None
                        ## need to select a new master
                        ## need to notify the
                        if len(self.slave_sockets) > 0:
                            # promote first slave to master
                            new_master_socket  = self.slave_server_sockets.pop()

                            self.promote_slave_to_master(new_master_socket)

                            #notify slave of promotion
                            #new_master_message = proto.ServerAssignment()
                            #new_master_message.isMaster = True
                            #utils.send(new_master_server_socket, new_master_message.SerializeToString())
                            #print("A new master server has been promoted.")
                            # notify back up proxy of promotion
                            #self.master_socket = new_master_server_socket
                            # start a heartbeat for the new master
                            #thread = threading.Thread(target=self.send_heartbeat, args=(self.master_socket,), daemon=True).start()

                        else:
                            LOGGER.info("No slave servers available to promote to master.")

                        #break


    def handle_connection(self, conn: socket.socket, address):
        print ("in handle connection")
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

                        elif init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER:

                            if self.master_socket.getpeername()[0] != conn.getpeername()[0]:
                                LOGGER.warning(f"Received message with sender type master from NON master server.")

                            if init_conn.HasField("server_response"):
                                self.relay_server_response(init_conn.server_response)

                            elif init_conn.HasField("is_heartbeat") and self.is_main:
                                LOGGER.debug ("Received heartbeat from master server. Sending response...")
                                # send heartbeat
                                threading.Thread(target=self.handle_heartbeat_response, daemon=True).start()
                            else:
                                LOGGER.warning(f"Proxy received msg from master with missing content {init_conn}")

                        elif init_conn.sender == proto.InitConnection.Sender.SERVER_SLAVE:
                                self.add_slave_socket(conn)

                                if self.is_main:
                                    self.slave_role_assignment(conn, init_conn)

                        elif init_conn.sender == proto.InitConnection.Sender.PROXY and self.is_main:
                            ## add bool for backup is up
                            print ("received message from backup proxy")
                            heartbeat = proto.Response()
                            heartbeat.code = proto.Response.Code.HEARTBEAT

                            # nofity backup proxy who the master server is
                            if self.master_socket is not None:
                                master_host, _ = self.master_socket.getpeername()
                                heartbeat.master_host = master_host

                            LOGGER.debug ("before sleeping 2")
                            time.sleep(5)
                            LOGGER.debug ("after sleeping 2")

                            if send(conn, heartbeat.SerializeToString()):
                                LOGGER.debug("Sent heartbeat to backup proxy")
                                LOGGER.debug("waiting for response from backup proxy")
                            else:
                                LOGGER.warning(f"Failed to send heartbeat to backup proxy.")


                except Exception as e:
                    print(traceback.format_exc())
                    break

        except socket.timeout:
            LOGGER.warning(f"socket timed out.")

        with self.lock:
            if client_key in self.client_sockets:
                del self.client_sockets[client_key]  # Remove client from mapping

            if conn == self.master_socket:
                self.master_socket = None
                print("Master server connection lost.")

            elif client_key.split(":")[0] in self.slave_sockets:
                del self.slave_sockets[client_key.split(":")[0]]
                print("Slave server connection lost.")

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
        print ("in run")
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
                    read_sockets, _, _ = select.select(self.socket_list, [], [], 0.5) #
                    for notified_socket in read_sockets:
                        if notified_socket == proxy_listening_sock:
                            conn, addr = proxy_listening_sock.accept()
                            # Pass both socket and address for easier client management
                            threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()

                    # check for a master if there is one start a new thread for making sure it is alive

                except Exception as exc:
                    LOGGER.error(f"run(): ")

        self.shutdown(proxy_listening_sock)


if __name__ == "__main__":

    if len(sys.argv) <= 2:
        print ("argv[1]" , sys.argv[1])
        if sys.argv[1] == "main":
            #csx2.uc.ucalgary.ca
            print ("setting host to csx1")
            proxy = Proxy("csx1.uc.ucalgary.ca", 5555, True)
        else:
            print ("setting host to localhost")
            proxy = Proxy("localhost", 5555)
    else:
        print ("length args > 2")
        if sys.argv[1] == "main":
            #csx2.uc.ucalgary.ca
            proxy = Proxy(sys.argv[2], 5555, True)
        else:
            proxy = Proxy(sys.argv[2], 5555)

    try:
        proxy.run()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down proxy server.")