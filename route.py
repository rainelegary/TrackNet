from classes import Track

class Route:
    """
    This class is used for defining a train's planned route.

    Attributes:
        tracks (List[Track]): An ordered list of junctions the train plans on visiting.


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
    def __init__(
        self,
        tracks: "list[Track]"
    ):
        self.tracks = tracks