from classes.junction import Junction

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
    def __init__(self, junctions: "list[Junction]"):
        self.junctions = junctions
        self.current_junction_index = 0
        self.destination = junctions[len(junctions) - 1]
        
    def get_next_track(self):
        return self.junctions[self.current_junction_index].neighbors[self.junctions[self.current_junction_index + 1].name]
    
    def get_next_junction(self):
        return self.junctions[self.current_junction_index + 1]

    def get_current_junction(self):
        return self.junctions[self.current_junction_index]

    def increment_junction_index(self):
        self.current_junction_index += 1
        
    def destination_reached(self):
        if self.current_junction_index > len(self.junctions):
            return True
        return False