import TrackNet_pb2
import logging
import socket
import signal 
from utils import *

setup_logging() ## only need to call at main entry point of application
LOGGER = logging.getLogger(__name__)

signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)

class Server():
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
    
    def listen_on_socket(self):
        self.sock = create_server_socket(self.host, self.port)
        
        while not exit_flag and self.sock:
            try:
                conn, addr = self.sock.accept()
                
                client_state = TrackNet_pb2.ClientState()
                data = receive(conn)
                
                if data is not None:
                    client_state.ParseFromString(data)
                    resp = TrackNet_pb2.SercerResponse()
                    
                    if not client_state.HasField("train_id"):
                        ## assign client a train id
                        resp.train_id = "name"
                    else:
                        resp.train_id = client_state.train_id
                    
                    if client_state.TrackCondition == TrackNet_pb2.ClientState.TrackCondition.BAD:
                        pass
                    
                    ## use speed, location & route data to detect possible conflicts.
                    
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
            
    