from .junction import *
from .route import *
from .train import *
from .track import *
from .location import *
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
    """Represents the entire railway system, including all junctions, tracks, and trains within the network.

    Attributes
    ----------
    map : Railmap
        A composition of the Railmap class that stores all the junctions and tracks within the railway system. Junctions and tracks within the Railmap can be accessed as map.junctions and map.tracks, respectively.
    trains : dict
        Stores all trains by their names. Each train is associated with its name as the key.
    train_counter : int
        A counter used to assign unique names to newly created trains.
    """

    def __init__(self, trains=None, junctions=None, tracks=None):
        """Initializes the Railway system with optional trains, junctions, and tracks.

        :param trains: A dictionary of trains where keys are train names and values are train lengths. Defaults to None.
        :param junctions: A list of junction names to initialize the railway map. Defaults to None.
        :param tracks: A list of tuples where each tuple contains information about a track (start junction, end junction, and length). Defaults to None.
        """
        self.map = Railmap(junctions, tracks)  # Composition: Railway has a Railmap; Track & Junction are now accessed as map.tracks and map.junctions
        self.trains = {}  # store trains by name
        self.train_counter = 0

        if trains:
            for train_name, train_length in trains.items():
                self.add_train(train_name, train_length)

    def create_new_train(self, length: int, origin_id: str):
        """Creates and parks a new train at the specified origin junction.

        :param length: The length of the new train.
        :param origin_id: The ID (name) of the junction where the train will start.
        :return: The newly created Train object.
        """
        new_name = "Train" + str(self.train_counter)
        self.train_counter += 1
        new_train = Train(new_name, length)
        # add train to origin junction
        self.map.junctions[origin_id].park_train(new_train)
        self.trains[new_name] = new_train
        return new_train

    def add_train(self, name: str, length: int):
        """Adds a new train to the railway map.

        :param name: The name of the new train.
        :param length: The length of the new train.
        """
        if name not in self.trains:
            self.trains[name] = Train(name, length)
        else:
            raise Exception(f"Train {name} already exists.")

    def update_train(self, train, state, location_obj: Location, route_obj: Route) -> bool:
        """Updates the state and location of a specified train based on the provided protobuf messages.

        :param train: The Train object to update.
        :param state: The new state of the train.
        :param location_msg: A protobuf message containing the new location information.
        :param route_msg: A protobuf message containing the new route information.
        """
        train_done = False

        front_track_id = location_obj.front_cart["track"].name
        front_junction_id = location_obj.front_cart["junction"].name
        front_position = location_obj.front_cart["position"]
        back_track_id = location_obj.back_cart["track"].name
        back_junction_id = location_obj.back_cart["junction"].name
        back_position = location_obj.back_cart["position"]
        
        LOGGER.debugv(f" train name: {train.name} \n train location={train.location} \n new location={location_obj}")
		

        # check if new track
        if (train.state in [TrainState.PARKED, TrainState.PARKING]) and (state in [TrainState.RUNNING, TrainState.UNPARKING]):
            # add to new track
            self.map.tracks[front_track_id].add_train(train)
			
			# remove train from junction
            LOGGER.debugv(f"Remove {train.name} from {back_junction_id}")
            try:
                ## remove train front cart junc?
                self.map.junctions[back_junction_id].depart_train(train)
            except Exception as exc:
                LOGGER.debugv("ERROR removing train from junction: " + str(exc))


        # check if new junction
        if train.state not in [TrainState.PARKED, TrainState.PARKING] and state in [TrainState.PARKED, TrainState.PARKING]:      
            
            # remove train from track
            try:
                self.map.tracks[train.location.back_cart["track"].name].remove_train(train.name)
            except:
                pass
            # add tain to new junction
            self.map.junctions[front_junction_id].park_train(train)

        LOGGER.debugv(f"train_state={train.state} client_state={state}")

        self.trains[train.name].location = location_obj
        self.trains[train.name].state = state
        self.trains[train.name].route = route_obj

        if self.trains[train.name].location.back_cart["junction"] == self.trains[train.name].route.destination:
            try: 
                self.map.junctions[back_junction_id].depart_train(train)
                train_done = True
            except Exception as exc:
                LOGGER.debug("ERROR removing train fro junction: " + str(exc))

        return train_done

        # update route
        # train = self.trains[train.name]
        # self.set_route_for_train(route_msg, train)
        # train.route = MessageConverter.route_msg_to_obj(route_msg, self.map.junctions)

    def set_route_for_train(self, route: TrackNet_pb2.Route, train: Train):
        """Sets a new route for the specified train.

        :param route: A protobuf Route message detailing the new route.
        :param train: The Train object to update.
        """
        new_route = []
        for junc in route.junctions:
            new_route.append(self.map.junctions[junc])
        train.route = Route(new_route, route.current_junction_index)
        train.location.set_track(self.train.route.get_next_track())
        LOGGER.debugv(f"init track={self.train.route.get_next_track()}")

    def print_map(self):
        """Prints an overview of the railway map, including details of junctions, tracks, and trains."""

        # Printing Junctions with parked trains
        if self.map.junctions:
            print("Junctions:")
            for junction_name, junction in self.map.junctions.items():
                trains_info = ", ".join(junction.parked_trains) if junction.parked_trains else "None"
                print(f"  Junction: {junction_name}, Parked Trains: [{trains_info}]")
        else:
            print("No Junctions to display.")

        # Printing Tracks with running trains
        print("\nTracks:")
        if self.map.tracks:
            for track_name, track in self.map.tracks.items():
                if hasattr(track, "trains") and track.trains:
                    print(f"Track: {track_name}, Length: {track.length}m, Speed Limit: {track.speed}km/h")
                    for train_id, train_data in track.trains.items():
                        # Rounding positions to two decimal places
                        front_position = round(train_data.location.front_cart['position'], 2)
                        back_position = round(train_data.location.back_cart['position'], 2)
                        print(f"  - Train: {train_id}, Speed: {train_data.current_speed}km/h, "
                            f"Position: Front {front_position}m - Back {back_position}m")
                else:
                    print(f"Track: {track_name}, Length: {track.length}m - No running trains")
        else:
            print("No Tracks to display.")

    def get_map_string(self):
        """Returns a string overview of the railway map, including details of junctions, tracks, and trains."""
        map_overview = ""

        # Adding Junctions with parked trains to the string
        if self.map.junctions:
            map_overview += "Junctions:\n"
            for junction_name, junction in self.map.junctions.items():
                trains_info = ", ".join(junction.parked_trains) if junction.parked_trains else "None"
                map_overview += f"  Junction: {junction_name}, Parked Trains: [{trains_info}]\n"
        else:
            map_overview += "No Junctions to display.\n"

        # Adding Tracks with running trains to the string
        map_overview += "\nTracks:\n"
        if self.map.tracks:
            for track_name, track in self.map.tracks.items():
                if hasattr(track, "trains") and track.trains:
                    map_overview += f"Track: {track_name}, Length: {track.length}m, Speed Limit: {track.speed}km/h\n"
                    for train_id, train_data in track.trains.items():
                        # Rounding positions to two decimal places
                        front_position = round(train_data.location.front_cart['position'], 2)
                        back_position = round(train_data.location.back_cart['position'], 2)
                        map_overview += f"  - Train: {train_id}, Speed: {train_data.current_speed}km/h, " \
                                        f"Position: Front {front_position}m - Back {back_position}m\n"
                else:
                    map_overview += f"Track: {track_name}, Length: {track.length}m - No running trains\n"
        else:
            map_overview += "No Tracks to display.\n"

        return map_overview
