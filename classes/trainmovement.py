import time
import TrackNet_pb2
from classes.location import *
from classes.route import *
from classes.junction import *
from classes.enums import *
from classes.train import Train

class TrainMovement(Train):

    def __init__(
        self,
        name = None, # Name will be assigned later if this is a client's train class
        length = 1000, # in meters
        junction_front: Junction = None, # junction ID
        junction_back: Junction = None,
    ):
        Train.__init__(self, name, length, junction_front, junction_back)
        self.next_junction = None
        self.prev_junction = None
        self.junction_delay = 5
        #speed is set by the server
        self.stay_parked = False

    def update_location(self, distance_moved): 
        self.location.set_position(distance_moved, self.length)

        if self.location.check_back_cart_departed():
            self.state = TrainState.RUNNING

        if self.location.check_front_cart_departed() and not self.location.check_back_cart_departed():
            self.state = TrainState.UNPARKING 
            
        if self.location.check_front_junction_reached():
            self.location.set_junction_front_cart(self.next_junction)
            LOGGER.debug(f"{self.name}'s front has reached {self.location.front_cart['junction'].name} junction - Waiting for back to reach junction.")
            self.state = TrainState.PARKING         
        
        if self.location.check_back_junction_reached() and self.state == TrainState.PARKING:
            self.location.set_junction_back_cart(self.next_junction)
            LOGGER.debug(f"{self.name}'s back has reached {self.location.back_cart['junction'].name} junction.")
            self.handle_arrival_at_junction()
            
    def handle_arrival_at_junction(self):
        # assumes both front and back are at the same junction
        # Handle the train's full arrival at the junction and transition to the next track if applicable
        # proceed with the next part of the route
        self.location.set_to_park()
        self.state = TrainState.PARKED
        self.current_speed = 0
  
        LOGGER.debug(f"Waiting at junction {self.next_junction.name} for {self.junction_delay} seconds...")
        time.sleep(self.junction_delay)  # Delay for 5 seconds

        self.route.increment_junction_index()
        
        if not self.stay_parked:
            if not self.route.destination_reached():
                next_track = self.route.get_next_track()
                self.location.set_track(next_track)
                self.prev_junction = self.next_junction
                self.next_junction = self.route.get_next_junction()
                self.current_speed = next_track.speed
                self.state = TrainState.UNPARKING
                
            else:
                LOGGER.debug(f"{self.name} has completed its route and is parked.")

    def stop(self):
        self.current_speed = 0
        self.state = TrainState.STOPPED
        
    def unpark(self, speed):
        self.current_speed = speed
        self.state = TrainState.UNPARKING
        