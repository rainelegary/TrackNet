from pprint import pprint
from .junction import *
from .route import *
from .train import *
from .track import *
import logging
LOGGER = logging.getLogger(__name__)

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

    def create_new_train(self, len : int, origin_id: str):
        """
        Creates a new Train object with the specified length and adds it to the list of trains.

        :param len: The length of the new train.
        :return: The newly created Train object.
        """
        new_name = "Train" + str(self.train_counter)
        self.train_counter += 1
        new_train = Train(new_name, len)
        # add train to origin junction
        self.map.junctions[origin_id].park_train(new_train)
        self.trains[new_name] = new_train
        return new_train
            
    def add_train(self, name, length):
        """Adds a new train to the map."""
        if name not in self.trains:
            self.trains[name] = Train(name, length)
        else:
            raise Exception(f"Train {name} already exists.")

    def update_train(self, train, state, location_msg: TrackNet_pb2.Location):
        # check if new track
        if train.location.front_cart["track"] is None or train.location.front_cart["track"].name != location_msg.front_track_id:
            # add to new track
            self.map.tracks[location_msg.front_track_id].add_train(train)
        

        # check if new junction
        if train.state != TrainState.PARKED and state in [TrainState.PARKED, TrainState.PARKING]:      
            
            # remove train from track
            try:
                self.map.tracks[train.location.back_cart["track"].name].remove_train(train.name)
            except:
                pass
            # add tain to new junction
            self.map.junctions[location_msg.front_junction_id].park_train(train)

        LOGGER.debug(f"train_state={train.state} client_state={state}")
        # check if leaving junction
        if train.state == TrainState.PARKED and state in [TrainState.RUNNING, TrainState.UNPARKING]:
            # remove train from junction
            LOGGER.debug(f"Remove {train.name} from {location_msg.back_junction_id}")
            try:
                ## remove train front cart junc?
                self.map.junctions[location_msg.back_junction_id].depart_train(train)
            except Exception as exc:
                LOGGER.debug("ERROR: "+ str(exc))

        # update location and state of train
        self.trains[train.name].location.front_cart = {"track": self.map.tracks[location_msg.front_track_id], "junction": self.map.junctions[location_msg.front_junction_id], "position": location_msg.front_position}
        self.trains[train.name].location.back_cart = {"track": self.map.tracks[location_msg.back_track_id], "junction": self.map.junctions[location_msg.back_junction_id], "position": location_msg.back_position}
        train.state = state

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
                
                print(f"{track.name}, Length: {track.length}, Running Trains: [",)
                
                for running_train in running_trains:
                    train_position_front = track.trains[running_train].location.front_cart['position']
                    train_position_back  = track.trains[running_train].location.back_cart['position']
                    train_speed          = track.trains[running_train].current_speed
                    track_speed          = track.speed
                    #***prints the track speed*** - train speed is 0 because it is not being sent from client to server in the protobuf
                    print(f"\t\t\t\t\t\t Train: {running_train} Speed: {track_speed} Front Position: {train_position_front} Back Position: {train_position_back}")
                print("]")
                 
            else:
                print(f"  Track: {track_name} has no running trains or is not properly initialized.")

    