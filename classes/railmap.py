import logging 
from classes.junction import Junction
from classes.enums import TrackCondition
from classes.track import Track

LOGGER = logging.getLogger(__name__)

class RailMap: 
    def __init__(self):
        self.junctions = {}  # Stores junctions by name
        self.tracks = {}  # List of tracks 
      
    def add_junction(self, name):
        """Adds a junction to the map."""
        if name not in self.junctions:
            junction = Junction(name)
            self.junctions[name] = junction
            return junction
        else:
            return self.junctions[name]
    
    def add_track(self, start_name, end_name, length):
        """Adds a track between two junctions."""
        if start_name in self.junctions and end_name in self.junctions:
            start_junction = self.junctions[start_name]
            end_junction = self.junctions[end_name]
            track = Track(start_junction, end_junction, length)
            self.tracks[track.name] = track
            start_junction.add_neighbor(end_junction, track)
        else:
            print("One or both junctions do not exist, adding them now.")
       
    def set_track_condition(self, track_id: str, condition: TrackCondition):
        #for track in self.tracks:
        #    if track.name == track_id:
        #        track.condition = condition
        self.tracks[track_id].track.condition = condition
                
    def has_bad_track_condition(self, track_id: str):
        #for track in self.tracks:
        #    if track.name == track_id and track.condition == TrackCondition.BAD:
        #        return True  
        #return False 
    
        if self.tracks[track_id].track.condition == TrackCondition.BAD:
            return True
        return False
         
    def get_random_origin_junction(self):
        pass