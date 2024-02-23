

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
        self.start_junction = start_junction
        self.end_junction = end_junction
        self.track_id = tuple(sorted([start_junction, end_junction])) # track id's have smaller node id listed first
        self.distance_covered: distance_covered

    def get_track_id(self):
        return self.track_id
    
    def get_distance(self):
        return self.distance_covered