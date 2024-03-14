import datetime
import logging
import time
import TrackNet_pb2
from classes.location import *
from classes.route import *
from classes.junction import *
from classes.enums import *
from classes.railmap import *

LOGGER = logging.getLogger(__name__)
    

class Train:
    """Represents a train running on the tracks or parked at a junction.
    
    Attributes:
        name (str): The name of the train.
        length (float): The length of the train as a percentage of the track's length.
        current_speed (float): The current speed of the train in units per time (e.g., km/h).
        last_time_updated (datetime): The last time the train's position or speed was updated.
        route (str []): A list of strings denoting the junctions in a train's route
    """
    def __init__(
        self,
        name = None, # Name will be assigned later if this is a client's train class
        length = 1000, # in meters
        junction_front: Junction = None, # junction ID
        junction_back: Junction = None,
    ):
        self.name = name
        self.length = length
        self.state = TrainState.PARKED
        self.location = Location(junction_front, junction_back)
        self.route = None
        #speed is set by the server
        self.current_speed = 0 
        self.next_junction = None
        self.prev_junction = None
    
    def set_route(self, route):
        self.route = route

    def set_speed(self, new_speed):
        self.current_speed = new_speed
        
    def get_speed(self):
        return self.current_speed
        
    def __repr__(self):
        return f"Train({self.name}, Location: {self.location}, Speed: {self.current_speed} km/h)"
