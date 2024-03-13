import select
import socket
import threading
import TrackNet_pb2
import TrackNet_pb2 as proto
import utils
import traceback
import TrackNet_pb2
import logging
import sys
from utils import *


setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger("Proxy")

class ProxyServer:
    def __init__(self, host, port, is_main=False):
        self.host = host
        self.port = port
        self.master_server_socket = None
        self.slave_sockets = {}
        self.client_sockets = {}  # Map client address (IP, port) to socket for direct access
        self.socket_list = []
        self.lock = threading.Lock()
        self.is_main = is_main

    def run(self):
        server_socket = create_server_socket(self.host, self.port)
        self.socket_list.append(server_socket)
        LOGGER.info(f"Proxy listening on {self.host}:{self.port}")

        try:
            while not exit_flag:
                # select.select(socks to monitor for incoming data, socks to write to, socks to monitor for exceptions, timeout value)
                read_sockets, _, _ = select.select(self.socket_list, [], [], 0.5) #
                for notified_socket in read_sockets:
                    if notified_socket == server_socket:
                        client_socket, client_address = server_socket.accept()
                        # Pass both socket and address for easier client management
                        threading.Thread(target=self.handle_connection, args=(client_socket, client_address), daemon=True).start() 
            
                # check for a master if there is one start a new thread for making sure it is alive 
        except Exception as exc:
            LOGGER.error(f"run(): {exc}")     
                     
        finally:
            self.shutdown(server_socket)

    def proxy_to_client(self, client_state: TrackNet_pb2.ClientState):
        with self.lock:
            if self.master_server_socket is not None:
                new_message = proto.InitConnection()
                new_message.sender = proto.InitConnection.Sender.PROXY
                new_message.client_state.CopyFrom(client_state)
                if not send(self.master_server_socket, new_message.SerializeToString()):
                    LOGGER.warning(f"Failed to send client state message to master.")
                else:
                    LOGGER.debug("client state forwaded to master server")
            else:
                LOGGER.warning("There is currently no master server")
                
    def proxy_to_master(self, server_response: TrackNet_pb2.ServerResponse):
       with self.lock:
            LOGGER.debug(f"Received message from master server, ip:{server_response.client.ip} port:{server_response.client.port}")

            # Extract the target client's IP and port
            target_client_key = f"{server_response.client.ip}:{int(server_response.client.port)}"
            target_client_socket = self.client_sockets.get(target_client_key)
            print("found client")
            
            relay_resp = proto.InitConnection()
            relay_resp.sender = proto.InitConnection.Sender.PROXY
            print(f"about to copy: {server_response}")
            relay_resp.server_response.CopyFrom(server_response)
            LOGGER.debug("server response message to client created")
            
            # Forward the server's message to the target client
            if target_client_socket:
                if not send(target_client_socket, relay_resp.SerializeToString()):
                    LOGGER.warning(f"Failed to send server response message to client")
            else:
                LOGGER.warning(f"Target client {target_client_key} not found.")
    
    def promote_slave_to_master(self, slave_sock: socket.socket):
        self.master_server_socket = slave_sock
        LOGGER.info(f"{slave_sock.getpeername()} promoted to MASTER")
        
        # notify the newly promoted master server of its new role 
        role_assignment = proto.ServerAssignment()
        role_assignment.is_master = True

        if len(self.slave_sockets) <= 0:
            LOGGER.info("No slaves to send to master")
             
        for slave_ip, _ in self.slave_sockets.items():
            slave_details = role_assignment.servers.add()
            slave_details.host = slave_ip
            slave_details.port = slave_to_master_port
            #LOGGER.info(f"Adding {slave_ip}:{slave_to_master_port} to list of slaves")
                
        if not send(slave_sock, role_assignment.SerializeToString()):
            LOGGER.warning(f"Failed to send role assignmnet to newly elected master.")
                  
    def proxy_to_slave(self, slave_socket: socket.socket):
        with self.lock:
            # Check if there is no master server, and promote the first slave to master
            if self.master_server_socket is None:
                self.promote_slave_to_master(slave_socket)
                
            # Already have master so assign slave role
            else: 
                self.slave_sockets[f"{slave_socket.getpeername()[0]}"] = slave_socket
                LOGGER.debug(f"Slave {slave_socket.getpeername()[0]} added")
                role_assignment = proto.ServerAssignment()
                role_assignment.is_master = False
                master_ip, _ = self.master_server_socket.getpeername()
                master_details = role_assignment.servers.add()
                master_details.host = master_ip
                master_details.port = slave_to_master_port
                
                if not send(slave_socket, role_assignment.SerializeToString()):
                    LOGGER.warning(f"Failed to send role assignmnet to slave.")


                # Notify master of new slave server so it can connect to it
                resp = TrackNet_pb2.InitConnection()
                resp.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                for slave_ip, _ in self.slave_sockets.items():
                    slave_details = resp.slave_details.add()
                    slave_details.host = slave_ip
                    slave_details.port = slave_to_master_port
                    #LOGGER.info(f"Adding {slave_ip}:{slave_to_master_port} to list of slaves")
                    
                print("Sending slave details to master")
                if not send(self.master_server_socket, resp.SerializeToString()):
                    LOGGER.warning(f"Failed to send slave details to master.")
    
    def proxy_to_proxy(self):
        pass

    def handle_connection(self, client_socket, client_address):
        # Convert address to a string key
        client_key = f"{client_address[0]}:{client_address[1]}"
        with self.lock:
            self.client_sockets[client_key] = client_socket

        LOGGER.debug("New connection handled in thread")

        while not exit_flag:
            message = receive(client_socket)

            if message is None:
                break

            try:
                init_conn = proto.InitConnection()
                init_conn.ParseFromString(message)

                if init_conn.sender == proto.InitConnection.Sender.CLIENT:
                    self.proxy_to_client(init_conn.client_state)

                elif init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER:
                    
                    if init_conn.HasField("server_response"):
                        self.proxy_to_master(init_conn.server_response)
                            
                    elif init_conn.HasField("is_heartbeat"):
                        pass 
                    
                    else:
                        LOGGER.warning(f"Proxy received msg from master with missing content.")
                        
                elif init_conn.sender  == proto.InitConnection.Sender.SERVER_SLAVE:
                    self.proxy_to_slave(client_socket)
                            
            except Exception as e:
                print(traceback.format_exc())
                #print(f"Failed to process message: {e}")
                break

        with self.lock:
            if client_key in self.client_sockets:
                del self.client_sockets[client_key]  # Remove client from mapping
                
            if client_socket == self.master_server_socket:
                self.master_server_socket = None
                print("Master server connection lost.")
                
            elif client_key.split(":")[0] in self.slave_sockets:

                del self.slave_sockets[client_key.split(":")[0]]
                print("Slave server connection lost.")
                
        client_socket.close()

    def handle_connectionOLD(self, client_socket, client_address):
        # Convert address to a string key
        client_key = f"{client_address[0]}:{client_address[1]}"
        with self.lock:
            self.client_sockets[client_key] = client_socket

        LOGGER.debug("New connection handled in thread")

        while not exit_flag:
            message = receive(client_socket)

            if message is None:
                break

            try:
                init_conn = proto.InitConnection()
                init_conn.ParseFromString(message)

                if init_conn.sender == proto.InitConnection.Sender.CLIENT:
                    with self.lock:
                        if self.master_server_socket:
                            new_message = proto.InitConnection()
                            new_message.sender = proto.InitConnection.Sender.PROXY
                            new_message.client_state.CopyFrom(init_conn.client_state)
                            utils.send(self.master_server_socket, new_message.SerializeToString())
                            print("client state forwaded to master server")
                        else:
                            print("There is currently no master server")

                elif init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER:
                    
                    if init_conn.HasField("server_response"):
                        with self.lock:
                            print(f"Received message from master server, ip:{init_conn.server_response.client.ip} port:{init_conn.server_response.client.port}")
                            print(init_conn)

                            # Extract the target client's IP and port
                            target_client_key = f"{init_conn.server_response.client.ip}:{int(init_conn.server_response.client.port)}"
                            target_client_socket = self.client_sockets.get(target_client_key)
                            print("found client")
                            new_message = proto.InitConnection()
                            new_message.sender = proto.InitConnection.Sender.PROXY
                            print(f"about to copy: {init_conn.server_response}")
                            new_message.server_response.CopyFrom(init_conn.server_response)
                            print("response message to client created")
                            if target_client_socket:
                                utils.send(target_client_socket, new_message.SerializeToString())  # Forward the server's message to the target client
                            else:
                                print(f"Target client {target_client_key} not found.")
                            
                    elif init_conn.HasField("is_heartbeat"):
                        pass 
                    
                    else:
                        LOGGER.warning(f"Proxy received msg from master with missing content.")
                        
                elif init_conn.sender  == proto.InitConnection.Sender.SERVER_SLAVE:
                    with self.lock:
                        # Check if there is no master server, and promote the first slave to master
                        if not self.master_server_socket:
                            self.master_server_socket = client_socket
                            print("First slave server promoted to master server")
                            #  notify the newly promoted master server of its new role 
                            new_message = proto.ServerAssignment()
                            new_message.isMaster = True

                            if len (self.slave_sockets) > 0:
                                for _, slaveServerSocket in self.slave_sockets.items():
                                    slave_ip, slave_port = slaveServerSocket.getsockname()
                                    slaveServerDetails = new_message.servers.add()
                                    slaveServerDetails.host = slave_ip
                                    slaveServerDetails.port = f"{slave_port}"
                                    print("Adding slave to list to send to master")
                                print("Sent all slaves to newly elected master")
                                # handle response of an acknowledgment 
                            else:
                                print("No slaves to send to master")
                            
                            print ("sending role assignment to server")
                            utils.send(client_socket,new_message.SerializeToString())
                            
                        else: # currently have a master so this is a slave server 
                            #self.slave_sockets.append(client_socket)
                            print("Slave server added")
                            print("Already have a master, so assign as a salve")
                            new_message = proto.ServerAssignment()
                            new_message.is_master = False
                            print ("sending role assignment to slave server")
                            utils.send(client_socket,new_message.SerializeToString())

                           
                            slave_resp = TrackNet_pb2.InitConnection()
                            slave_resp.CopyFrom(init_conn)
                            print ("received slave response")
                            print (slave_resp)
                            if slave_resp.sender == TrackNet_pb2.InitConnection.Sender.SERVER_SLAVE:
                                print("Received a message from slave server")
                                if slave_resp.slave_server_details.host and slave_resp.slave_server_details.port:
                                    slave_ip   = slave_resp.slave_server_details.host
                                    slave_port = slave_resp.slave_server_details.port
                                    print(f"Received ip from slave server:   {slave_resp.slave_server_details.host} {slave_ip}")
                                    print(f"Received port from slave server: {slave_resp.slave_server_details.port} {slave_port}")

                                    #Notify master server of new slave server so it can connect to it
                                    resp = TrackNet_pb2.InitConnection()
                                    resp.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                                    resp.slave_server_details.host = slave_ip
                                    resp.slave_server_details.port = slave_port
                                    print ("Sending new slave details to master")
                                    utils.send(self.master_server_socket, resp.SerializeToString())

                            print ("sent details of slave to master server")
                            # handle response of an acknowledgment 
                            #new_message = proto.InitConnection()
                            #new_message.sender = proto.InitConnection.Sender.PROXY
                            # new_message = proto.ServerAssignment()
                            # new_message.isMaster = False
                            # master_ip, master_port = self.master_server_socket.getsockname()
                            # masterServerDetails = new_message.servers.add()
                            # masterServerDetails.host = master_ip
                            # masterServerDetails.port = master_port
                            # utils.send(client_socket,new_message.SerializeToString())
                            
            except Exception as e:
                print(traceback.format_exc())
                #print(f"Failed to process message: {e}")
                break

        with self.lock:
            if client_key in self.client_sockets:
                del self.client_sockets[client_key]  # Remove client from mapping
                
            if client_socket == self.master_server_socket:
                self.master_server_socket = None
                print("Master server connection lost.")
                
            elif client_key in self.slave_sockets:
                #self.slave_server_sockets.remove(client_socket)
                print("Slave server connection lost.")
                
        client_socket.close()

    def shutdown(self, server_socket: socket.socket): 
        with self.lock:
            server_socket.shutdown(socket.SHUT_RDWR)
            server_socket.close()
            for socket in self.socket_list:
                socket.shutdown(socket.SHUT_RDWR)
                socket.close()
            self.socket_list.clear()
            self.client_sockets.clear()
            LOGGER.info(f"Proxy {self.host}{self.port} shut down")

if __name__ == "__main__":
    proxy = ProxyServer("localhost", 5555)
    try:
        proxy.run()
    except KeyboardInterrupt:
        print("Shutting down proxy server.")
