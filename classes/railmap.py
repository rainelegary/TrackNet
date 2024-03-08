import logging 
from classes.junction import Junction
from classes.enums import TrackCondition
from classes.track import Track
from queue import PriorityQueue

LOGGER = logging.getLogger(__name__)

class RailMap: 
    def __init__(self, junctions=None, tracks=None):
        self.junctions = {}  # Stores junctions by name
        self.tracks = {}  # Collection of tracks

        if junctions:
            for junction_name in junctions:
                self.add_junction(junction_name)  

        if tracks:
            for track_info in tracks:
                self.add_track(*track_info)  
      
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
            junction_a:Junction = self.junctions[junction_a_name]
            junction_b:Junction = self.junctions[junction_b_name]
            track = Track(junction_a_name, junction_b_name, length)
            self.tracks[track.name] = track
            junction_a.add_neighbor(junction_b, track)
            junction_b.add_neighbor(junction_a, track)
        else:
            print("One or both junctions do not exist, adding them now.")
       
    def set_track_condition(self, track_id: str, condition: TrackCondition):
        self.tracks[track_id].condition = condition
                
    def has_bad_track_condition(self, track_id: str):
        return self.tracks[track_id].condition == TrackCondition.BAD
         
    def get_origin_destination_junction(self):
        return self.junctions["A"], self.junctions["D"]

    # example usage = map_instance.find_shortest_path(start_junction_name="A", destination_junction_name="D", avoid_track_name="AB")
    def find_shortest_path(self, start_junction_name, destination_junction_name, avoid_track_name=None):
        distances = {junction: float('infinity') for junction in self.junctions}
        previous_junctions = {junction: None for junction in self.junctions}
        distances[start_junction_name] = 0

        pq = PriorityQueue()
        pq.put((0, start_junction_name))

        while not pq.empty():
            current_distance, current_junction_name = pq.get()
            current_junction = self.junctions[current_junction_name]

            if current_junction_name == destination_junction_name:
                break

            for neighbor_name, track in current_junction.neighbors.items():
                if track.name == avoid_track_name:
                    continue

                distance = current_distance + track.length
                if distance < distances[neighbor_name]:
                    distances[neighbor_name] = distance
                    previous_junctions[neighbor_name] = current_junction_name
                    pq.put((distance, neighbor_name))

        return self.reconstruct_path(previous_junctions, start_junction_name, destination_junction_name)

    def reconstruct_path(self, previous_junctions, start, end):
        path = []
        current = end
        while current != start:
            if current is None:
                return None  # Path not found
            path.insert(0, self.junctions[current])
            current = previous_junctions[current]
        path.insert(0, self.junctions[start])
        return path