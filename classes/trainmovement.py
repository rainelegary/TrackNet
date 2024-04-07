import time
import logging
from classes.location import *
from classes.route import *
from classes.junction import *
from classes.enums import *
from classes.train import Train

LOGGER = logging.getLogger(__name__)

class TrainMovement(Train):
    """A class for managing the movements of a train, inheriting from the Train class. 

    This class is used by the client program exclusively. It simulates the
    movement of a train within a dispatch area

    Attributes
    ----------
    junction_delay : Integer representing the delay (in seconds) at a junction.

    stay_parked : Boolean indicating whether the train stays parked or not.
    """
    def __init__(self, name: str=None, length: int=5, location: Location=None):
        """Initializes the TrainMovement instance.

        :param name: (Optional) The name of the train. Assigned later by server. Defaults to None.
        :param length: (Optional) The length of the train in meters. Defaults to 1000.
        :param location: (Optional) The initial location of the train. Defaults to None.
        """
        Train.__init__(self, name, length, location=location)
        self.junction_delay = 5
        self.stay_parked = False

    def update_location(self, distance_moved: int): 
        """Updates the train's location and state based on the distance moved.

        :param distance_moved: The distance (in meters) that the train has moved.
        """
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

        if self.state == TrainState.PARKED and not self.stay_parked and not self.route.destination_reached():
            self.leave_junction()

    def leave_junction(self):
        next_track = self.route.get_next_track()
        self.location.set_track(next_track)
        self.prev_junction = self.next_junction
        self.next_junction = self.route.get_next_junction()
        self.current_speed = TrainSpeed.FAST.value
        self.state = TrainState.UNPARKING

    def handle_arrival_at_junction(self):
        """Handles the train's arrival at a junction, including parking, 
        waiting, and potentially moving to the next track in trains route.
        
        Assumes both front and back are at the same junction
        """
        self.location.set_to_park()
        self.state = TrainState.PARKED
        self.current_speed = 0
        self.route.increment_junction_index()

        LOGGER.debug(f"Waiting at junction {self.next_junction.name} for {self.junction_delay} seconds...")
        # 5 seconds delay needed to ensure server railway is synched correctly
        time.sleep(self.junction_delay)

        if not self.stay_parked and not self.route.destination_reached():
            self.leave_junction()

    def stop(self):
        """Stops the train by setting its current speed to 0 and changing its state to STOPPED."""
        self.current_speed = 0
        self.state = TrainState.STOPPED

    def resume_movement(self, speed: int):
        """Resumes the train's movement at the specified speed.

        :param speed: The speed at which the train should resume moving.
        """
        self.current_speed = speed
        self.state = TrainState.RUNNING
        
    def unpark(self, speed: int):
        """Unparks the train and sets its speed, changing its state to UNPARKING.

        :param speed: The speed at which the train should start moving upon unparking.
        """
        self.current_speed = speed
        self.state = TrainState.UNPARKING
        