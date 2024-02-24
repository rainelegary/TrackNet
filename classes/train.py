import datetime
import logging
import time
import TrackNet_pb2
from classes.location import Location
from classes.route import Route
from classes.junction import Junction
from classes.enums import TrainState
from classes.railmap import RailMap

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
        railmap: RailMap = None,
        destination: Junction = None,
    ):
        self.name = name
        self.length = length
        self.location = Location(junction_front, junction_back, 0)
        self.route = None
        self.state = TrainState.PARKED
        self.junction_delay = 5
        self.railmap = railmap
        self.railway = None
        self.destination = destination
        self.current_speed = 0 
        self.last_time_updated = datetime.now()
    
    def update_location(self, distance_moved):   
        self.location.set_position(distance_moved)

        if self.location.check_front_junction_reached():
            LOGGER.debug(f"Train {self.name}'s front has reached {self.location.front_cart["junction"].name} junction.")
            self.state = TrainState.PARKING         
        
        if self.location.check_back_junction_reached() and self.state == TrainState.PARKING:
            LOGGER.debug(f"Train {self.name}'s back has reached {self.location.back_cart["junction"].name} junction.")
            self.handle_arrival_at_junction()
            
        if self.state == TrainState.UNPARKING and self.location.is_unparked():
            self.state = TrainState.RUNNING
            
    def handle_arrival_at_junction(self):
        # assumes both front and back are at the same junction
        # Handle the train's full arrival at the junction and transition to the next track if applicable
        # proceed with the next part of the route
        junction = self.location.set_to_park()
        self.railway_map.park_train_at_junction(self.name, junction.name)
        self.state == TrainState.PARKING
        self.current_speed = 0
            
        LOGGER.debug(f"Waiting at junction {junction.name} for {self.junction_delay} seconds...")
        time.sleep(self.junction_delay)  # Delay for 5 seconds
        self.move_to_next_track()
            
    def move_to_next_track(self):
        # Advance the train onto the next track or mark it as parked if at the end of the route
        self.route.increment_junction_index()
        if not self.route.destination_reached():
            next_track = self.route.get_next_track()
            self.location.set_track(next_track)
            self.current_speed = 50
            self.railway_map.add_train_to_track(self.name, next_track.name) 
            self.state = TrainState.UNPARKING
            
        else:
            LOGGER.debug(f"Train {self.name} has completed its route and is parked.")

    def stop(self):
        self.current_speed = 0
        self.state = TrainState.STOPPED
        
    def unpark(self, speed):
        self.current_speed = speed
        self.state = TrainState.UNPARKING

    def set_speed(self, new_speed):
        self.current_speed = new_speed
        
    def get_speed(self):
        return self.current_speed
    
    def set_railway (self, railway):
        self.railway = railway
        
    def __repr__(self):
        return f"Train({self.name}, Location: {self.location}, Speed: {self.current_speed} km/h, Last Updated: {self.last_time_updated})"