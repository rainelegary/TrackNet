import select
import socket
import threading
import TrackNet_pb2 as proto
import utils

class ProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.master_server_socket = None
        self.slave_server_sockets = []
        self.client_sockets = {}  # Map client address (IP, port) to socket for direct access
        self.socket_list = []
        self.lock = threading.Lock()

    def run(self):
        server_socket = utils.create_server_socket(self.host, self.port)
        self.socket_list.append(server_socket)
        print(f"Proxy listening on {self.host}:{self.port}")

        try:
            while not utils.exit_flag:
                read_sockets, _, _ = select.select(self.socket_list, [], [], 0.5)
                for notified_socket in read_sockets:
                    if notified_socket == server_socket:
                        client_socket, client_address = server_socket.accept()
                        # Pass both socket and address for easier client management
                        thread = threading.Thread(target=self.handle_connection, args=(client_socket, client_address))
                        thread.daemon = True
                        thread.start()
            
                # check for a master if there is one start a new thread for making sure it is alive 
                        
        finally:
            self.shutdown(server_socket)

    def handle_connection(self, client_socket, client_address):
        # Convert address to a string key
        client_key = f"{client_address[0]}:{client_address[1]}"
        with self.lock:
            self.client_sockets[client_key] = client_socket

        print("New connection handled in thread")

        while not utils.exit_flag:
            message = utils.receive(client_socket)
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
                        else:
                            print("There is currently no master server")

                elif init_conn.sender  == proto.InitConnection.Sender.SERVER_MASTER:
                    with self.lock:
                        
                        # Extract the target client's IP and port
                        target_client_key = f"{init_conn.server_response.clientIP}:{int(init_conn.server_response.clientPort)}"
                        target_client_socket = self.client_sockets.get(target_client_key)
                        new_message = proto.InitConnection()
                        new_message.sender = proto.InitConnection.Sender.PROXY
                        new_message.ServerResponse.CopyFrom(init_conn.ServerResponse)
                        if target_client_socket:
                            utils.send(target_client_socket, new_message.SerializeToString())  # Forward the server's message to the target client
                        else:
                            print(f"Target client {target_client_key} not found.")
                
                elif init_conn.sender  == proto.InitConnection.Sender.SERVER_SLAVE:
                    with self.lock:
                        # Check if there is no master server, and promote the first slave to master
                        if not self.master_server_socket:
                            self.master_server_socket = client_socket
                            print("First slave server promoted to master server")
                            #  notify the newly promoted master server of its new role 
                            new_message = proto.ServerAssignment()
                            new_message.isMaster = True
                            for slaveServerSocket in self.slave_server_sockets:
                                slave_ip, slave_port = slaveServerSocket.getsockname()
                                slaveServerDetails = new_message.servers.add()
                                slaveServerDetails.ip = slave_ip
                                slaveServerDetails.port = f"{slave_port}"
                            utils.send(client_socket,new_message.SerializaToString())
                            # handle response of an acknowledgment 
                             
                            
                        else:
                            self.slave_server_sockets.append(client_socket)
                            print("Slave server added")
                            #new_message = proto.InitConnection()
                            #new_message.sender = proto.InitConnection.Sender.PROXY
                            new_message = proto.ServerAssignment()
                            new_message.isMaster = False
                            master_ip, master_port = self.master_server_socket.getsockname()
                            masterServerDetails = new_message.servers.add()
                            masterServerDetails.ip = master_ip
                            masterServerDetails.port = f"{master_port}"
                            utils.send(client_socket,new_message.SerializaToString())
                            # handle response of an acknowledgment 

                

            except Exception as e:
                print(f"Failed to process message: {e}")
                break

        with self.lock:
            if client_key in self.client_sockets:
                del self.client_sockets[client_key]  # Remove client from mapping
            if client_socket == self.master_server_socket:
                self.master_server_socket = None
                print("Master server connection lost.")
            elif client_socket in self.slave_server_sockets:
                self.slave_server_sockets.remove(client_socket)
                print("Slave server connection lost.")
        client_socket.close()

    def shutdown(self, server_socket):
        with self.lock:
            server_socket.close()
            for socket in self.socket_list:
                socket.close()
            self.socket_list.clear()
            self.client_sockets.clear()
            print("Proxy server shut down")

if __name__ == "__main__":
    proxy = ProxyServer("localhost", 5555)
    try:
        proxy.run()
    except KeyboardInterrupt:
        print("Shutting down proxy server.")
