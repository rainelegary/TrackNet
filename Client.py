import TrackNet_pb2
import logging
import signal 
import time
from Utils import *
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
        self.train = Train("name", 5)
    
    def run(self):
        while not exit_flag:
            self.sock = create_client_socket(self.host, self.port)
            
            state = TrackNet_pb2.ClientState()
            state.train_id = self.train.name
            state.speed = 60
            state.location = None
            state.condition = TrackNet_pb2.ClientState.TrackCondition.GOOD
            state.route = None
            
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
            
            
    
    