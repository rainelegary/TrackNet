import logging
from pprint import pprint
from queue import PriorityQueue
from .junction import *
from .route import *
from .train import *
from .track import *


# Example usage:
# initial_config = {
#     "junctions": ["A", "B", "C", "D"],
#     "tracks": [
#         ("A", "B", 10),
#         ("B", "C", 20),
#         ("C", "D", 30),
#         ("A", "D", 40)
#     ]
# }

# railway_system = Railway(
#     trains=None,
#     junctions=initial_config["junctions"],
#     tracks=initial_config["tracks"]
# )

class Railway:
    """Represents the entire railway map, containing junctions and tracks.
    
    Attributes:
        junctions (dict): Stores junctions by their names.
        tracks (dict): Stores all tracks in the railway.
        trains (dict): Stores trains by their name 
    """
    def __init__(self, trains=None, junctions=None, tracks=None):
        self.junctions = {}  # Stores junctions by name
        self.tracks = {}  # List of tracks 
        self.trains = {} # store trains by name 
        self.train_counter = 0

        if junctions:
            for junction_name in junctions:
                self.add_junction(junction_name)

        if tracks:
            for track_info in tracks:
                self.add_track(*track_info)

        if trains:
            for train_name, train_length in trains.items():
                self.add_train(train_name, train_length)

    def create_new_train(self, len : int):
        """
        Creates a new Train object with the specified length and adds it to the list of trains.

        :param len: The length of the new train.
        :return: The newly created Train object.
        """
        new_name = "Train" + str(self.train_counter)
        self.train_counter += 1
        new_train = Train(new_name, len)
        self.trains[new_name] = new_train
        return new_name

    def set_track_condition(self, track_id: str, condition: TrackCondition):
        self.tracks[track_id].condition = condition
                
    def has_bad_track_condition(self, track_id: str):
        return self.tracks[track_id].condition == TrackCondition.BAD
                
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
            end_junction.add_neighbor(start_junction, track)
        else:
            print("One or both junctions do not exist, adding them now.")
            
    def add_train(self, name, length):
        """Adds a new train to the map."""
        if name not in self.trains:
            self.trains[name] = Train(name, length)
        else:
            raise Exception(f"Train {name} already exists.")

    def update_train(self, train, state: TrainState, location_msg: TrackNet_pb2.Location):
        train.state = state
        if location_msg.HasField("front_track_id"):
            # check if new track
            if train.location.front_cart["track"].name != location_msg.front_track_id:
                # add to new track
                self.tracks[location_msg.front_track_id].add_train(train)
                # update location of train
                train.location.front_cart["track"] = self.tracks[location_msg.front_track_id]
            
        elif location_msg.HasField("front_junction_id"):  
            # check if new junction
            if train.location.front_cart["junction"].name != location_msg.front_junction_id:
                # add to new junction
                self.junctions[location_msg.front_junction_id].park_train(train)
                # update location of train
                train.location.front_cart["junction"] = self.junctions[location_msg.front_junction_id]

        if location_msg.HasField("back_track_id"):
            # check if need to remove from previous junction 
            if train.location.back_cart["junction"] is not None:
                self.junctions[location_msg.back_junction_id].depart_train(train) 
                
            # check if new track
            if train.location.back_cart["track"].name != location_msg.back_track_id:
                # update location of train
                train.location.back_cart["track"] = self.tracks[location_msg.back_track_id]
            
        elif location_msg.HasField("back_junction_id"):
            # check if need to remove from previous track
            if train.location.back_cart["track"] is not None:
                self.tracks[location_msg.back_track_id].remove_train(train)
                # track.remove_train(location_msg.back_track_id)
                
            # check if new junction
            if train.location.back_cart["junction"].name != location_msg.back_junction_id:
                # update location of train
                train.location.back_cart["junction"] = self.junctions[location_msg.back_junction_id]

        train.location.front_cart["position"] = location_msg.front_position
        train.location.back_cart["position"] = location_msg.back_position

    def add_train_to_track(self, train_name, track_name):
        """Places an existing train on a specified track by name."""
        #*Modify to remove train from parked junction if on one*

        if train_name in self.trains and track_name in self.tracks:
            train = self.trains[train_name]
            self.tracks[track_name].add_train(train)
            train.place_on_track(self.tracks[track_name])
            print(f"Train {train_name} added to track {track_name}.")
        else:
            print(f"Train {train_name} not found or track {track_name} does not exist.")
    
    def park_train_at_junction(self, train_name, junction_name):
        """Parks an existing train at a specified junction by name."""
        if train_name in self.trains and junction_name in self.junctions:
            train = self.trains[train_name]
            junction = self.junctions[junction_name]

            # Remove the train from its current track if it's on one
            if train.current_track_front:
                del train.current_track_front.trains[train.name]

            junction.park_train(train)
            train.park_at_junction(junction)
            print(f"Train {train_name} parked at junction {junction_name}.")
        else:
            print(f"Train {train_name} not found or junction {junction_name} does not exist.")

    def reroute_train(self, train_name, avoid_track_name):
        """
        Reroutes a train to avoid a specified track.

        :param train_name: The name of the train to reroute.
        :param avoid_track_name: The name of the track to avoid.
        """
        train = self.trains[train_name]
        if not train:
            print(f"No train found with the name {train_name}.")
            return

        # Destination is the last junction in the train's current route
        destination_junction = train.route.tracks[-1]

        # Find a new route from the train's current junction to the destination
        new_route = self.find_shortest_path(train.current_junction, destination_junction, avoid_track_name)

        if new_route:
            # Update the train's route
            train.set_route(new_route)
            print(f"Train {train_name} rerouted successfully.")
        else:
            print(f"No alternative route found for Train {train_name}.")

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

            print(f"Exploring junction {current_junction_name}. Printing neighbors:")
            #find all the neighbors of the current junction
            for neighbor_name, track in current_junction.neighbors.items():
                print(neighbor_name, track.name)
                


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
            path.insert(0, current)
            current = previous_junctions[current]
        path.insert(0, start)
        return path

    def print_map(self):
        """Prints an overview of the map, including junctions, tracks, and parked or running trains."""
        print("Map Overview:")
        print("Junctions:")
        for junction_name, junction in self.junctions.items(): # iterate through junctions
            trains_info = ", ".join(junction.parked_trains.keys())
            print(f"  Junction: {junction_name}, Parked Trains: [{trains_info}]")

        print("Tracks:")
        for track in self.tracks: # iterate through tracks
            running_trains = ", ".join(track.trains.keys())
            pprint(f"  Track: {track.name}, Length: {track.length}, Running Trains: [{running_trains}]")
    
    