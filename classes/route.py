from classes.junction import Junction
import logging
LOGGER = logging.getLogger(__name__)

class Route:
    """
    Represents a train's planned route through the railway network. The route is defined as an ordered list of junctions that the train plans to visit. Future versions of this class will include attributes for speed changes, track stops, and junction stops.

    Attributes
    ----------
    junctions : List[Junction]
        An ordered list of junctions the train plans on visiting.
    current_junction_index : int
        The index of the current junction in the list of junctions that the train is at or heading towards.
    destination : Junction
        The final destination junction in the route.


    Attributes to add in future versions (TODO):
    --------------------------------------------
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
        """Initializes a Route instance with a list of junctions and an optional current junction index.

        :param junctions: A list of Junction objects representing the ordered list of junctions the train will visit.
        :param current_junction_index: The current position in the list of junctions, representing where the train is starting from. Defaults to 0.
        """
        self.junctions = junctions
        self.current_junction_index = current_junction_index
        self.destination = junctions[len(junctions) - 1] # Last junction in the route
        
    def get_next_track(self):
        """Returns the next track on the route as a Track object.

        :return: The next Track object on the route based on the current position.
        """
        LOGGER.debugv(f"get_next_track(): current junction index = {self.current_junction_index}")
        if self.current_junction_index == len(self.junctions) - 1:
            return None
        
        return self.junctions[self.current_junction_index].neighbors[self.junctions[self.current_junction_index + 1].name]
    
    def get_next_junction(self) -> Junction:
        """Returns the next junction on the route as a Junction object.

        :return: The next Junction object on the route based on the current position.
        """
        if self.current_junction_index == len(self.junctions) - 1:
            return None
        return self.junctions[self.current_junction_index + 1]

    def get_current_junction(self) -> Junction:
        """Returns the current junction on the route as a Junction object.

        :return: The current Junction object on the route based on the current position.
        """
        return self.junctions[self.current_junction_index]

    def increment_junction_index(self):
        """Increments the current junction index, moving the position forward along the route."""
        self.current_junction_index += 1
        
    def destination_reached(self) -> bool:
        """Checks if the destination has been reached in the route.

        :return: True if the destination junction is the current junction; False otherwise.
        """
        if self.current_junction_index >= len(self.junctions) - 1:
            return True
        return False