import select
import socket
import threading
import TrackNet_pb2
import TrackNet_pb2 as proto
import utils
from utils import *

class ProxyServer:
    def __init__(self, host, port): #initialise all values
        self.host = host
        self.port = port
        self.master_server_socket = None
        self.slave_server_sockets = []
        self.client_sockets = []
        self.socket_list = []
        self.lock = threading.Lock()

    def run(self): # create server socket and start threads for all socket connections
        server_socket = utils.create_server_socket(self.host, self.port)
        self.socket_list.append(server_socket)
        print(f"Proxy listening on {self.host}:{self.port}")

        try:
            while not utils.exit_flag:
                read_sockets, _, _ = select.select(self.socket_list, [], [], 0.5)
                for notified_socket in read_sockets:
                    if notified_socket == server_socket:
                        client_socket, _ = server_socket.accept() # accept connectino then handle connection in thread 
                        thread = threading.Thread(target=self.handle_connection, args=(client_socket,))
                        thread.daemon = True
                        thread.start()
        finally:
            self.shutdown(server_socket)

    def handle_connection(self, client_socket): # handle connections 
        with self.lock:
            self.socket_list.append(client_socket)
        print("New connection handled in thread")

        while not utils.exit_flag:
            message = utils.receive(client_socket)

            if message is None:
                break

            try:
                init_conn = proto.InitConnection()
                init_conn.ParseFromString(message)
                # handle connection based on types 
                if init_conn.sender == proto.InitConnection.Sender.CLIENT:
                    with self.lock:
                        if self.master_server_socket:
                            utils.send(self.master_server_socket, message)
                        else:
                            print("There is currently no master server")

                elif init_conn.sender == proto.InitConnection.Sender.SERVER_MASTER:
                    with self.lock: # need to forward to the client 
                        self.master_server_socket = client_socket
                        print("Master server updated")
                        #utils.send(self.client_sockets, message)

                elif init_conn.sender == proto.InitConnection.Sender.SERVER_SLAVE:
                    with self.lock:
                        # Check if there is no master server, and promote the first slave to master
                        if not self.master_server_socket:
                            self.master_server_socket = client_socket
                            print("First slave server promoted to master server")
                            #  notify the newly promoted master server of its new role here
                        else:
                            self.slave_server_sockets.append(client_socket)
                            print("Slave server added")
                            data = receive(client_socket)
                            if data:
                                slave_resp = TrackNet_pb2.InitConnection()
                                slave_resp.ParseFromString(data)
                                if slave_resp.sender == TrackNet_pb2.InitConnection.Sender.SERVER_SLAVE:
                                    print("Received a message from slave server")
                                    if slave_resp.new_slave_server_details.ip and slave_resp.new_slave_server_details.port:
                                        slave_ip   = slave_resp.new_slave_server_details.ip
                                        slave_port = slave_resp.new_slave_server_details.port
                                        print(f"Received ip from slave server:   {slave_resp.new_slave_server_details.ip}")
                                        print(f"Received port from slave server: {slave_resp.new_slave_server_details.port}")

                                        #Notify master server of new slave server so it can connect to it
                                        resp = TrackNet_pb2.InitConnection()
                                        resp.sender = TrackNet_pb2.InitConnection.Sender.PROXY
                                        resp.new_slave_server_details.ip   = slave_ip
                                        resp.new_slave_server_details.port = slave_port
                                        print ("Sending new slave details to master")
                                        send(self.master_server_socket, resp.SerializeToString())

                            else:
                                print ("Error: Nothing received from slave server")
                            
            except Exception as e:
                print(f"Failed to process message: {e}")
                break
        
        # Cleanup when the connection is closed or an error occurs
        with self.lock:
            self.socket_list.remove(client_socket)
            if client_socket in self.client_sockets:
                self.client_sockets.remove(client_socket)
            if client_socket == self.master_server_socket:
                self.master_server_socket = None
                print("Master server connection lost. Looking for a new master...")
               
            elif client_socket in self.slave_server_sockets:
                self.slave_server_sockets.remove(client_socket)
                print("Slave server connection lost")
        client_socket.close()

    def shutdown(self, server_socket): #shutdown process
        with self.lock:
            server_socket.close()
            for socket in self.socket_list:
                socket.close()
            self.socket_list.clear()
            print("Proxy server shut down")

if __name__ == "__main__":
    proxy = ProxyServer("localhost", 5555)
    try:
        proxy.run()
    except KeyboardInterrupt:
        print("Shutting down proxy server.")
