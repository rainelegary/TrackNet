import logging 
from classes.junction import Junction
from classes.enums import TrackCondition
from classes.track import Track

LOGGER = logging.getLogger(__name__)

class RailMap: 
    def __init__(self):
        self.junctions = {}  # Stores junctions by name
        self.tracks = {}  # Collection of tracks
      
    def add_junction(self, name):
        """Adds a junction to the map."""
        if name not in self.junctions:
            junction = Junction(name)
            self.junctions[name] = junction
            return junction
        else:
            return self.junctions[name]
    
    def add_track(self, junction_a_name, junction_b_name, length):
        """Adds a track between two junctions."""
        if junction_a_name in self.junctions and junction_b_name in self.junctions:
            junction_a = self.junctions[junction_a_name]
            junction_b = self.junctions[junction_b_name]
            track = Track(junction_a, junction_b, length)
            self.tracks[track.name] = track
            junction_a.add_neighbor(junction_b, track)
            junction_b.add_neighbor(junction_a, track)
        else:
            print("One or both junctions do not exist, adding them now.")
       
    def set_track_condition(self, track_id: str, condition: TrackCondition):
        self.tracks[track_id].track.condition = condition
                
    def has_bad_track_condition(self, track_id: str):
        if self.tracks[track_id].track.condition == TrackCondition.BAD:
            return True
        return False
         
    def get_random_origin_junction(self):
        pass