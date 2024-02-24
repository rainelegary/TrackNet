import datetime
import logging 

LOGGER = logging.getLogger(__name__)

class Location:
    """ Used to store a train's location on a track.
    :param start_junction: the node it's coming from
    :param end_junction: the node it's heading towards
    :param distance_covered: kilometers along track
    """
    def __init__(self, start_junction: int, end_junction: int, distance_covered: int):
        self.front_cart = {"track": None, "junction": start_junction, "position": None}
        self.back_cart = {"track": None, "junction": start_junction, "position": None}

        self.track_id = tuple(sorted([start_junction, end_junction])) # track id's have smaller node id listed first
        self.distance_covered: distance_covered

    def get_track_id(self):
        return self.track_id
    
    def get_distance(self):
        return self.distance_covered
    
    def set_position(self, front_cart_pos):
        self.front_cart["position"] = front_cart_pos
        self.back_cart["position"] = min(0, front_cart_pos - self.length)

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
      
    def set_track(self, track):
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