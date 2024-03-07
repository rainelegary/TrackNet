import TrackNet_pb2
import logging
import socket
import signal 
import threading
from utils import *
from  classes.enums import TrainState, TrackCondition
from classes.railway import Railway
from classes.train import Train

setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger(__name__)

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [
        ("A", "B", 10),
        ("B", "C", 10),
        ("C", "D", 10),
        ("A", "D", 40)
    ]
}
#signal.signal(signal.SIGTERM, exit_gracefully)
#signal.signal(signal.SIGINT, exit_gracefully)

#Slave server 
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
        self.host = host
        self.port = port
        #remove sock
        self.sock = None
        self.proxy_sock = None
        self.master_sock = None

        self.railway = Railway(
            trains=None,
            junctions=initial_config["junctions"],
            tracks=initial_config["tracks"]
        )

        self.isMaster = False
        self.proxy_host = ""
        self.proxy_port = ""
        self.connect_to_proxy (self.proxy_host, self.proxy_port)
        self.connected_to_master = False
        #self.listen_on_socket ()

    def set_slave_identification_msg (self, slave_identification_msg: TrackNet_pb2.InitConnection):
        slave_identification_msg.sender = TrackNet_pb2.InitConnection.SERVER_SLAVE

        slave_identification_msg.slave_server_details.host = self.host
        slave_identification_msg.slave_server_details.port = self.port 

    def connect_to_proxy (self, proxy_host, proxy_port):
        self.proxy_sock = create_slave_socket(proxy_host, proxy_port)
        if self.proxy_sock:        
            LOGGER.debug ("Connected to proxy")
            #Send proxy init message to identify itself as a slave
            slave_identification_msg = TrackNet_pb2.InitConnection()
            self.set_slave_identification_msg (slave_identification_msg)

            if send(self.proxy_sock, slave_identification_msg.SerializeToString()):
                LOGGER.debug ("Sent slave identification message to proxy")
                listen_to_proxy_thread = threading.Thread(target=self.listen_to_proxy, daemon=True).start()


    def listen_to_proxy (self):
        try:
            while True: 
                data = receive(self.proxy_sock)
                if data is not None: 
                    proxy_resp = TrackNet_pb2.ServerAssignment()
                    proxy_resp.ParseFromString(data)
                    
                    # Determine if this server has been assigned as the master
                    if proxy_resp.HasField("role"):
                        if proxy_resp.role.isMaster:
                            print("This server has promoted to the MASTER")
                            self.promote_to_master() 
                        else:
                            print("This server has been designated as a SLAVE.")

                            if not self.connected_to_master and (len(proxy_resp.servers) == 1):
                                # Extract the master server's IP and port from the ServerDetails
                                master_host = proxy_resp.servers[0].ip
                                master_port = proxy_resp.servers[0].port

                                #Connect to master if the current server hasn't been assigned master by proxy
                                #listen to master instead of initiating connection
                                self.connect_to_master (master_host, master_port) 
                           

                    # Determine is other server is assigned as the master
                    

        except Exception as e:
            LOGGER.error(f"Error communicating with proxy: {e}")
            self.proxy_sock.close() 

    def connect_to_master (self, master_host, master_port):
        self.master_sock = create_slave_socket (master_host, master_port)
        if (self.master_sock):
            LOGGER.debug ("Connected to master")
            self.connected_to_master = True
            # Handle master communication in a separate thread
            threading.Thread(target=self.handle_master_communication, daemon=True).start()

    def handle_master_communication (self):
        try:
            while True:
                data = receive(self.master_sock)
                if data is not None:
                    master_resp = TrackNet_pb2.InitConnection()
                    master_resp.ParseFromString(data)
                    if master_resp.HasField("railway_update"):
                        self.railway = master_resp.railway_update.railway
                        LOGGER.debug(f"Received railway update from master at {master_resp.railway_update.timestamp}")
        except Exception as e:
            LOGGER.error(f"Error communicating with master: {e}")
            self.connected_to_master = False
            self.master_sock.close()  

    def promote_to_master(self):
        self.isMaster = True
        #initialize saved railway state

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


    def handle_connection(self, conn):
        ## assumes that ClientSate.Location is always set
        
        client_state = TrackNet_pb2.ClientState()
        data = receive(conn)
        
        if data is not None:
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
            self.railway.update_train(train, TrainState(client_state.train.state), client_state.location)

            # (TODO) use speed, location & route data to detect possible conflicts.
            resp.speed = 200
            resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR
            
            if not send(conn, resp.SerializeToString()):
                LOGGER.error("response did not send.")

        self.railway.print_map()

    def listen_on_socket(self):
        """Listens for incoming connections on the server's socket. Handles incoming data, parses it, and responds according to the server logic.

        This method continuously listens for incoming connections, accepts them, and processes the received data to manage the state of trains and the track. It handles client requests, updates train positions, and responds with the appropriate server response. The method also handles exceptions and socket timeouts, ensuring the server remains operational.

        :raises socket.timeout: Ignores timeout exceptions and continues listening.
        :raises Exception: Logs and handles generic exceptions, restarting the socket if necessary.
        """
        self.sock = create_server_socket(self.host, self.port)
        
        while not exit_flag and self.sock:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self.handle_connection, args=(conn,), daemon=True).start() 
                        
            except socket.timeout:
                pass 
            
            except Exception as exc: 
                LOGGER.error("listen_on_socket(): " + str(exc))
                self.sock.close()
                LOGGER.info("Restarting listening socket...")
                self.sock = create_server_socket(self.host, self.port)
            
    
if __name__ == '__main__':
    Server()