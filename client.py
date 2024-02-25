import TrackNet_pb2
import logging
import signal 
import time
import random
import threading
from utils import *
from classes import *
from classes.enums import *
from classes.railmap import RailMap
from classes.route import Route
from classes.train import Train
from datetime import datetime

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
        self.probabilty_of_good_track = 95
        self.railmap = RailMap()
        
        origin = self.railmap.get_random_origin_junction()
        self.train = Train(length=self.generate_random_train_length(), junction_front=origin, junction_back=origin)
        
        threading.Thread(target=self.update_position, args=(), daemon=True).start() 
        
    def generate_random_train_length(self):
        ## TODO 
        return 30
        
    def get_track_condition(self):
        """ Determines the track condition based on a predefined probability.

        :return: Returns GOOD track condition with a 95% probability and BAD track condition with a 5% probability.
        :rtype: TrackNet_pb2.ClientState.TrackCondition
        """
        return TrackNet_pb2.ClientState.TrackCondition.GOOD if random.random() < self.probabilty_of_good_track else TrackNet_pb2.ClientState.TrackCondition.BAD
    
    def update_position(self):
        ## TODO decided how often to update
        while not exit_flag:
            time.sleep(3)
            if self.train.state in [TrainState.PARKED, TrainState.STOPPED]:
                continue

            elapsed_time = (datetime.now() - self.last_time_updated).total_seconds()

            # Adjust the speed to achieve desired movement
            speed_factor = 10  # Adjust this factor as needed
            effective_speed = self.train.get_speed() * speed_factor        
            distance_moved = effective_speed * (elapsed_time / 3600)  # Assuming speed is in km/h
        
            self.train.update_location(distance_moved)
            self.last_time_updated = datetime.now()
            

    def set_client_state_msg(self, state: TrackNet_pb2.ClientState):
        """ Populates a `ClientState` message with the current state of the train, including its id, length, speed, location, track condition, and route.

        :param state: The `ClientState` message object to be populated with the train's current state.
        """
        if self.train.name is not None:
            state.train.id = self.train.name
        state.train.length = self.train.length
        state.train.state = self.train.state
        state.speed = self.train.get_speed()
        self.train.location.set_location_message(state.location)
        state.condition = self.get_track_condition()
        
        if self.train.route is not None:
            for junction_obj in self.train.route.junctions:
                junction_msg = state.route.junctions.add() 
                junction_msg.id = junction_obj
            
            state.route.destination = self.train.route.destination

    def set_route(self, route: TrackNet_pb2.Route):
        new_route = []
        for junc in route.junctions:
            new_route.append(self.railmap.junctions[junc])
        self.train.route = Route(new_route)
    
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
                        LOGGER.debug(f"Initi. {self.train.name}")
                        
                    if self.train.route is None: 
                        if not server_resp.HasField("new_route"):
                            LOGGER.warning(f"Server has not yet provided route for train.")
                            ## cannot take instructions until route is assigned
                            self.sock.close()
                            continue
                        
                        self.set_route(server_resp.route)
                        
                    if server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED:
                        LOGGER.debug(f"CHANGE_SPEED {self.train.name} to {server_resp.speed_change}")
                        self.train.set_speed(server_resp.speed_change)
                        
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE:
                        LOGGER.debug(f"REROUTING {self.train.name}")
                        self.set_route(server_resp.route)
                    
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP:
                        LOGGER.debug(f"STOPPING {self.train.name}")
                        self.train.stop()
                    
                    elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR:
                        if self.train.state in [TrainState.PARKED, TrainState.STOPPED]:
                            self.train.unpark(server_resp.speed_change)
                    
                self.sock.close()
                
            time.sleep(5)
            
            
    
    
