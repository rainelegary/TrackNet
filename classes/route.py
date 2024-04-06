from classes.junction import Junction
import logging
LOGGER = logging.getLogger(__name__)

class Route:
    """
    This class is used for defining a train's planned route.

    Attributes:
        junctions (List[Junction]): An ordered list of junctions the train plans on visiting.


    Attributes to add in future versions (TODO):
        speed_changes (list[tuple[Track, int, int]]): 
            Each tuple is the track, distance along track, and what speed to change to.
        track_stops (list[tuple[Track, int, datetime.timedelta]]): 
            Each tuple is the track, distance along track, and amount of time to stop for.
        junction_stops (list[tuple[Junction, datetime.timedelta]]): 
            Each tuple is the junction and how long to stop at it for.
            If train goes straight through the junction without stopping, 
            that junction is not included in this list.
    """
    def __init__(self, junctions: "list[Junction]", current_junction_index=0):
        self.junctions = junctions
        self.current_junction_index = current_junction_index
        self.destination = junctions[len(junctions) - 1] # Last junction in the route
        
    def get_next_track(self):
        """
        Returns next track as an object
        """
        LOGGER.debugv(f"get_next_track(): current junction index = {self.current_junction_index}")
        if self.current_junction_index == len(self.junctions) - 1:
            return None
        
        return self.junctions[self.current_junction_index].neighbors[self.junctions[self.current_junction_index + 1].name]
    
    def get_next_junction(self):
        """
        Returns next junction as an object
        """
        if self.current_junction_index == len(self.junctions) - 1:
            return None
        return self.junctions[self.current_junction_index + 1]

    def get_current_junction(self):
        """
        Returns current junction as an object
        """
        return self.junctions[self.current_junction_index]

    def increment_junction_index(self):
        self.current_junction_index += 1
        
    def destination_reached(self):
        """
        Dertmines whether destination reached or not
        """
        if self.current_junction_index >= len(self.junctions) - 1:
            return True
        return False