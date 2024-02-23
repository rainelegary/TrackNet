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
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.train = Train(5)
        self.probabilty_of_good_track = 95
    
    def get_track_condition(self):
        """ Returns GOOD track condition 95% of the time and 
                    BAD track condition 5% of the time"""
        return TrackNet_pb2.ClientState.TrackCondition.GOOD if random.random() < self.probabilty_of_good_track else TrackNet_pb2.ClientState.TrackCondition.BAD
    
    def set_client_state_msg(self, state):
        if self.train.name is not None:
            state.train_id = self.train.name
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
        
        
    
    def run(self):
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
                        pass 
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.INCREASE_SPEED:
                        pass
                    elif  server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE:
                        pass
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP:
                        pass
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR:
                        pass
                    
                self.sock.close()
                
            time.sleep(3)
            
            
    
    