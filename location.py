

class Location:
    """
    Used to store a train's location on a track.
    """
    def __init__(
        self, 
        start_node:int, # the node it's coming from
        end_node:int, # the node it's heading towards
        distance_covered:int, # kilometers along track
    ):
        self.start_node = start_node
        self.end_node = end_node
        self.track_id = tuple(sorted([start_node, end_node])) # track id's have smaller node id listed first
        self.distance_covered: distance_covered

