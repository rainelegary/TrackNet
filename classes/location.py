

class Location:
    """
    Used to store a train's location on a track.
    """
    def __init__(
        self, 
        start_junction:int, # the node it's coming from
        end_junction:int, # the node it's heading towards
        distance_covered:int, # kilometers along track
    ):
        self.front_cart = {"track": None, "junction": start_junction, "position": None}
        self.back_cart = {"track": None, "junction": start_junction, "position": None}

        self.track_id = tuple(sorted([start_junction, end_junction])) # track id's have smaller node id listed first
        self.distance_covered: distance_covered

    def get_track_id(self):
        return self.track_id
    
    def get_distance(self):
        return self.distance_covered
    
    def set_position(self, pos):
        pass

    def set_to_park(self, junction):
        """Parks the train at a specified junction and resets speed to 0."""
        self.front_cart = {"track": None, "junction": junction, "position": 0}
        self.back_cart = {"track": None, "junction": junction, "position": 0}


        # Set the current junction to the specified junction
        self.is_parked = True
        self.current_junction_front = junction  
        self.current_junction_back  = junction
        
        # Clear the current track since the train is now parked
        self.current_track_front = None  
        self.current_track_back  = None 
        self.current_speed = 0  # Reset speed when parked
        self.last_time_updated = datetime.now()