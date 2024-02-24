import datetime
import TrackNet_pb2
import logging 
from classes.junction import Junction
from classes.track import Track

LOGGER = logging.getLogger(__name__)

class Location:
    """ Used to store a train's location on a track.
    :param start_junction: the node it's coming from
    :param end_junction: the node it's heading towards
    """
    def __init__(self, start_junction: Junction, end_junction: Junction):
        self.front_cart = {"track": None, "junction": start_junction, "position": 0}
        self.back_cart = {"track": None, "junction": end_junction, "position": 0}
    
    def set_position(self, front_cart_position):
        self.front_cart["position"] = front_cart_position
        self.back_cart["position"] = min(0, front_cart_position - self.length)

    def set_location_message(self, msg: TrackNet_pb2.Location):
        if self.front_cart["track"] is not None:
            msg.track = self.front_cart["track"].name
            
        if self.front_cart["junction"] is not None:
            msg.junction = self.front_cart["junction"].name
            
        msg.position = self.front_cart["position"]
        

    def is_unparked(self):
        if self.front_cart["position"] > 0:
            return True
        return False

    def check_front_junction_reached(self):
        if self.front_cart["track"] is not None and self.front_cart["position"] >= self.front_cart["track"].length:
            self.front_cart["junction"] = self.front_cart["track"].end_junction
            self.front_cart["track"] = None  # Clear the front track as it has reached the junction
            return True
        return False
    
    def check_back_junction_reached(self):   
        # Calculate if the back of the train has reached the end of its track
        if self.back_cart["track"] is not None and self.back_cart["position"] >= self.back_cart["track"].length:
            self.back_cart["junction"] = self.back_cart["track"].end_junction 
            self.back_cart["track"] = None  # Clear the back track as it has reached the junction
            return True
        return False
      
    def set_track(self, track: Track):
        self.front_cart["track"] = track
        self.back_cart["track"] = track
        
    def set_to_park(self):
        """Parks the train at junction"""
        junction = self.front_cart["junction"]
        self.front_cart = {"track": None, "junction": junction, "position": 0}
        self.back_cart = {"track": None, "junction": junction, "position": 0}
        
    def __str__(self):
        if self.front_cart["track"] is not None:
            return f"{self.front_cart["track"].name} {self.front_cart["postion"]:.2f}"
        return f"{self.front_cart["junction"].name} "