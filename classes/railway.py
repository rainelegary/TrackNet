from pprint import pprint
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
        self.map = RailMap(junctions, tracks)  # Composition: Railway has a RailMap; Track & Junction are now accessed as map.tracks and map.junctions
        self.trains = {} # store trains by name 
        self.train_counter = 0

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
        return new_train
            
    def add_train(self, name, length):
        """Adds a new train to the map."""
        if name not in self.trains:
            self.trains[name] = Train(name, length)
        else:
            raise Exception(f"Train {name} already exists.")

    def update_train(self, train, state, location_msg: TrackNet_pb2.Location):
        train.state = state
        if location_msg.HasField("front_track_id"):
            # check if new track
            if train.location.front_cart["track"] is None or train.location.front_cart["track"].name != location_msg.front_track_id:
                # add to new track
                self.map.tracks[location_msg.front_track_id].add_train(train)
                # update location of train
                train.location.front_cart["track"] = self.map.tracks[location_msg.front_track_id]
            
        if location_msg.HasField("front_junction_id"):  
            # check if new junction
            if train.location.front_cart["junction"] is None or train.location.front_cart["junction"].name != location_msg.front_junction_id:
                # add to new junction
                self.map.junctions[location_msg.front_junction_id].park_train(train)
                # update location of train
                train.location.front_cart["junction"] = self.map.junctions[location_msg.front_junction_id]

        if location_msg.HasField("back_track_id"):
            # check if need to remove from previous junction 
            if train.location.back_cart["junction"] is not None:
                self.map.junctions[train.location.back_cart["junction"].name].depart_train(train) 
                
            # check if new track
            if train.location.back_cart["track"] is None or train.location.back_cart["track"].name != location_msg.back_track_id:
                # update location of train
                train.location.back_cart["track"] = self.map.tracks[location_msg.back_track_id]
            
        if location_msg.HasField("back_junction_id"):
            # check if need to remove from previous track
            if train.location.back_cart["track"] is not None:
                self.map.tracks[train.location.back_cart["track"].name].remove_train(train.name)
                # track.remove_train(location_msg.back_track_id)
                
            # check if new junction
            if train.location.back_cart["junction"] is None or train.location.back_cart["junction"].name != location_msg.back_junction_id:
                # update location of train
                train.location.back_cart["junction"] = self.map.junctions[location_msg.back_junction_id]

        train.location.front_cart["position"] = location_msg.front_position
        train.location.back_cart["position"] = location_msg.back_position

    def add_train_to_track(self, train_name, track_name):
        """Places an existing train on a specified track by name."""
        #*Modify to remove train from parked junction if on one*

        if train_name in self.trains and track_name in self.map.tracks:
            train = self.trains[train_name]
            self.map.tracks[track_name].add_train(train)
            train.place_on_track(self.map.tracks[track_name])
            print(f"Train {train_name} added to track {track_name}.")
        else:
            print(f"Train {train_name} not found or track {track_name} does not exist.")
    
    def park_train_at_junction(self, train_name, junction_name):
        """Parks an existing train at a specified junction by name."""
        if train_name in self.trains and junction_name in self.map.junctions:
            train = self.trains[train_name]
            junction = self.map.junctions[junction_name]

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
        new_route = self.map.find_shortest_path(train.current_junction, destination_junction, avoid_track_name)

        if new_route:
            # Update the train's route
            train.set_route(new_route)
            print(f"Train {train_name} rerouted successfully.")
        else:
            print(f"No alternative route found for Train {train_name}.")


    def print_map(self):
        """Prints an overview of the map, including junctions, tracks, and parked or running trains."""
        print("Map Overview:")
        print("Junctions:")
        for junction_name, junction in self.map.junctions.items():
            
            trains_info = ", ".join([train for train in junction.parked_trains])  
            print(f"  Junction: {junction_name}, Parked Trains: [{trains_info}]")

        print("Tracks:")
        for track_name, track in self.map.tracks.items():  # Adjusted to iterate through items() 
            if hasattr(track, 'trains') and isinstance(track.trains, dict):  # Safety checks
                
                running_trains = track.trains.keys()  #track.trains is a dictionary
                
                print(f"  Track: {track.name}, Length: {track.length}, Running Trains: [",)
                
                for running_train in running_trains:
                    train_position_front = track.trains[running_train].location.front_cart['position']
                    train_position_back = track.trains[running_train].location.back_cart['position']
                    train_speed = track.trains[running_train].current_speed
                    print(f"\t\t\t\t\t\t Train: {running_train} Speed: {train_speed} Front Position: {train_position_front} Back Position: {train_position_back}")
                print("]")
                 
            else:
                print(f"  Track: {track_name} has no running trains or is not properly initialized.")

    