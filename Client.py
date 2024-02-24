import TrackNet_pb2
import logging
import signal 
import time
import random
from utils import *
from classes import *
from enums import *

setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger(__name__)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

class Client():
    
    def __init__(self, host: str, port: int):
        """ A client class responsible for simulating a train's interaction with a server, including sending its state and receiving updates.

        :param host: The hostname or IP address of the server to connect to.
        :param port: The port number to connect to on the server.
        :ivar host: Hostname or IP address of the server.
        :ivar port: Port number for the server connection.
        :ivar sock: Socket object for the client. Initially set to None.
        :ivar train: A Train object representing the client's train.
        :ivar probabilty_of_good_track: The probability (as a percentage) that the track condition is good.
        """
        self.host = host
        self.port = port
        self.sock = None
        self.train = Train(5)
        self.probabilty_of_good_track = 95
    
    def get_track_condition(self):
        """ Determines the track condition based on a predefined probability.

        :return: Returns GOOD track condition with a 95% probability and BAD track condition with a 5% probability.
        :rtype: TrackNet_pb2.ClientState.TrackCondition
        """
        return TrackNet_pb2.ClientState.TrackCondition.GOOD if random.random() < self.probabilty_of_good_track else TrackNet_pb2.ClientState.TrackCondition.BAD
    

    def update_position(self):
        ## increment position of train
        pass 


    def set_client_state_msg(self, state: TrackNet_pb2.ClientState):
        """ Populates a `ClientState` message with the current state of the train, including its id, length, speed, location, track condition, and route.

        :param state: The `ClientState` message object to be populated with the train's current state.
        """
        if self.train.name is not None:
            state.train.id = self.train.name
        state.train.length = self.train.length
        state.speed = self.train.get_speed()
        state.location.track_id = self.train.location.get_track_id()
        state.location.distance = self.train.location.get_distance()
        state.condition = self.get_track_condition()
        
        ## (TODO) make sure route has been set correctly
        for track in self.train.route.tracks:
            track = state.route.tracks.add() 
            track.name = track.name
            track.length = track.length
            track.to_node = track.start_junction
            track.from_node = track.end_junction
            
        state.route.destination = None
        state.route.origin = None   
    
    def run(self):
        """Initiates the client's main loop, continuously sending its state to the server and processing the server's response. It handles connection management, state serialization, and response deserialization. Based on the server's response, it adjusts the train's speed, reroutes, or stops as necessary.

        The method uses a loop that runs until an `exit_flag` is set. It manages the socket connection, sends the train's state, and processes responses from the server. The method also handles rerouting, speed adjustments, and stopping the train based on the server's instructions.
        """
        while not exit_flag:
            self.sock = create_client_socket(self.host, self.port)
            
            state = TrackNet_pb2.ClientState()
            
            self.set_client_state_msg(state)
            
            if send(self.sock, state.SerializeToString()):
                data = receive(self.sock)
                server_resp = TrackNet_pb2.ServerResponse()
                
                if data is not None:
                    server_resp.ParseFromString(data)
                    
                    if self.train.name is None:
                        self.train.name = server_resp.train_id
                        
                    if server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REDUCE_SPEED:
                        self.train.set_speed(server_resp.speed_change)
                        
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.INCREASE_SPEED:
                        self.train.set_speed(server_resp.speed_change)
                        
                    elif  server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE:
                        ## (TODO)
                        ## create new Route object using data from message
                        ## use self.train.set_route(new_route) to reroute
                        pass
                    
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP:
                        ## (TODO) call self.train stop method 
                        pass
                    
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR:
                        pass
                    
                self.sock.close()
                
            time.sleep(3)
            
            
    
    