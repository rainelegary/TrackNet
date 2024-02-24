import TrackNet_pb2
import logging
import socket
import signal 
from utils import *
from classes import Train

setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger(__name__)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

class Server():
    
    def __init__(self, host: str, port: int):
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
        self.sock = None
        self.railway = Railway()
        self.train_counter = 0
        
    def get_train(self, train: TrackNet_pb2.Train):
        """Retrieves a Train object based on its ID. If the train does not exist, it creates a new Train object.

        :param train: The train identifier or a Train object with an unset ID to create a new Train.
        :return: Returns the Train object matching the given ID, or a new Train object if the ID is not set.
        :raises Exception: Logs an error if the train ID does not exist in the list of trains.
        """
        if not train.HasField("id"):
            return self.create_new_train(train.length)
        else:
            for t in self.trains:
                if t.name == train.id:
                    return t
                
            LOGGER.error(f"Train {train.id} does not exits in list of trains.")

    

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
                
                client_state = TrackNet_pb2.ClientState()
                data = receive(conn)
                
                if data is not None:
                    client_state.ParseFromString(data)
                    resp = TrackNet_pb2.SercerResponse()
                    
                    train = self.get_train(client_state.train)
                    resp.train.id = train.name
                    resp.train.length = train.length
                    
                    if client_state.TrackCondition == TrackNet_pb2.ClientState.TrackCondition.BAD:
                        ## (TODO) set track to bad condition
                        pass
                    
                    ## TODO update trains position
                    ## TODO check if current track has bad condition ->check_track_condition() & set status to change speed to a reduced speed

                    ## (TODO) use speed, location & route data to detect possible conflicts.
                    
                    resp.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR
                    
                    if not send(conn, resp.SerializeToString()):
                        LOGGER.error("response did not send.")
                        
            except socket.timeout:
                pass 
            
            except Exception as exc: 
                LOGGER.error("listen_on_socket(): " + str(exc))
                self.sock.close()
                LOGGER.info("Restarting listening socket...")
                self.sock = create_server_socket(self.host, self.port)
            
    