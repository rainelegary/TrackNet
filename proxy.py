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
import time
from utils import *


setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger("Proxy")

class Proxy:
    def __init__(self, host, port, is_main=False, proxy_port=6666):
        self.host = host
        self.port = port
        self.master_socket = None
        self.slave_sockets = {}
        self.client_sockets = {}  # Map client address (IP, port) to socket for direct access
        self.socket_list = []
        self.lock = threading.Lock()
        self.is_main = is_main
        self.proxy_port = proxy_port
        self.main_proxy_host = None
        
        self.set_main_proxy_host()
        
        threading.Thread(target=self.proxy_to_proxy, daemon=True).start() 
        
    def set_main_proxy_host(self):
        if self.is_main:
            self.main_proxy_host = self.host
        else:
            for proxy, _ in proxy_details.items():
                if proxy != self.host:
                    self.main_proxy_host = proxy
    
        ## case where only one proxy and command-line arg main missing
        if self.main_proxy_host is None:
            LOGGER.warning(f"Only one proxy? setting as main proxy")
            self.main_proxy_host = self.host
            self.is_main = True

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
    
    def promote_slave_to_master(self, slave_sock: socket.socket):
        self.master_socket = slave_sock
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
                  
    def slave_role_assignment(self, slave_socket: socket.socket):
        with self.lock:
            # Check if there is no master server, and promote the first slave to master
            if self.master_socket is None:
                self.promote_slave_to_master(slave_socket)
                
            # Already have master so assign slave role
            else: 
                self.slave_sockets[f"{slave_socket.getpeername()[0]}"] = slave_socket
                LOGGER.debug(f"Slave {slave_socket.getpeername()[0]} added")
                role_assignment = proto.ServerAssignment()
                role_assignment.is_master = False
                master_ip, _ = self.master_socket.getpeername()
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
                    
                LOGGER.debug("Sending slave details to master")
                if not send(self.master_socket, resp.SerializeToString()):
                    LOGGER.warning(f"Failed to send slave details to master.")
    
    def proxy_to_proxy(self):
        if not self.is_main:
            while not exit_flag:
                proxy_sock = create_client_socket(self.main_proxy_host, self.proxy_port)
                
                if proxy_sock is None:
                    LOGGER.warning(f"Failed to connect to main proxy. Trying again in 5 seconds ...")
                    time.sleep(5)
                    continue 
                
                heartbeat_request = proto.InitConnection()
                heartbeat_request.sender = proto.InitConnection.Sender.PROXY
                heartbeat_request.is_heartbeat = True
                
                if not send(heartbeat_request, proxy_sock.SerializeToString()):
                    LOGGER.warning("Failed to send heartbeat request to main proxy.")
                    
                data = receive(proxy_sock)
                
                if data:
                    heartbeat = proto.Response()
                    heartbeat.ParseFromString(data)
                    
                    if heartbeat.code == proto.Response.Code.HEARTBEAT:
                        pass ## TODO
                ## TODO handle main proxy failure
        else:
            pass
            ## TODO main tell backup who is master server ?? 
                    
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

                        elif init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER:
                            
                            if init_conn.HasField("server_response"):
                                self.relay_server_response(init_conn.server_response) 
                                
                            elif init_conn.HasField("is_heartbeat") and self.is_main:
                                pass
                                
                            else:
                                LOGGER.warning(f"Proxy received msg from master with missing content {init_conn}")
                                
                        elif init_conn.sender == proto.InitConnection.Sender.SERVER_SLAVE and self.is_main:
                                self.slave_role_assignment(conn)
                        
                        elif init_conn.sender == proto.InitConnection.Sender.PROXY and self.is_main:
                            heartbeat = proto.Response()
                            heartbeat.code = proto.Response.Code.HEARTBEAT
                            if not send(conn, heartbeat.SerializeToString()):
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

if __name__ == "__main__":
    if sys.argv[1] == "main":
        proxy = Proxy("localhost", 5555, True)
    else: 
        proxy = Proxy("localhost", 5555)
        
    try:
        proxy.run()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down proxy server.")
