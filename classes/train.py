import logging
from classes.location import *
from classes.route import *
from classes.junction import *
from classes.enums import *
from classes.railmap import *

LOGGER = logging.getLogger(__name__)


class Train:
    """Represents a train running on the tracks or parked at a junction.

    Attributes
    ----------
    name : str
        The name of the train. If not provided during initialization, it will be assigned later. This is intended for client's train classes.
    length : float
        The length of the train in meters.
    current_speed : float
        The current speed of the train in units per time (e.g., km/h).
    last_time_updated : datetime
        The last time the train's position or speed was updated. Not explicitly set in __init__, should be managed externally.
    route : list
        A list of strings denoting the junctions in a train's route. If not provided during initialization, it should be set using the `set_route` method.

    """
    def __init__(self, name: str=None, length: int=5, state:TrainState=TrainState.PARKED, location: Location=Location(),
        route: Route=None, current_speed: int=0, next_junction: Junction=None, prev_junction: Junction=None):
        """Initializes a new Train instance.

        :param name: Optional; the name of the train. Defaults to None.
        :param length: Optional; the length of the train in meters. Defaults to 1000.
        :param state: The initial state of the train, defaulting to PARKED.
        :param location: The initial location of the train. Defaults to an instance of Location().
        :param route: The planned route for the train. Defaults to None.
        :param current_speed: The initial speed of the train. Defaults to 0.
        :param next_junction: The next junction the train is heading towards. Defaults to None.
        :param prev_junction: The previous junction the train has passed. Defaults to None.
        """
        self.name = name
        self.length = length
        self.state = state
        self.location = location
        self.route = route
        self.current_speed = current_speed
        self.next_junction = next_junction
        self.prev_junction = prev_junction

    def set_speed(self, new_speed: int):
        """Sets the train's speed to a new value.

    def set_speed(self, new_speed: int):
        :param new_speed: The new speed for the train.
        """
        self.current_speed = new_speed

    def get_speed(self) -> int:
        """Returns the current speed of the train.

        :return: The current speed of the train.
        """
        return self.current_speed
    
    def get_next_track_for_conflict_analyzer(self):
        LOGGER.debugv(f"Find the next track for {self.name}")
        LOGGER.debugv(f"{self.name} has current junction index of {self.route.current_junction_index}")
        if self.route.current_junction_index == len(self.route.junctions) - 1:
            return None # on final junction; destination already reached
        
        if (
            self.state in [TrainState.UNPARKING, TrainState.RUNNING, TrainState.PARKING]
            and self.route.current_junction_index == len(self.route.junctions) - 2
        ):
            return None # on final track; no more tracks to enter


        if self.state == TrainState.PARKED:
            
            return self.route.junctions[self.route.current_junction_index].neighbors[self.route.junctions[self.route.current_junction_index + 1].name]
        
        if self.state in [TrainState.UNPARKING, TrainState.RUNNING, TrainState.PARKING]:
            return self.route.junctions[self.route.current_junction_index + 1].neighbors[self.route.junctions[self.route.current_junction_index + 2].name]

    # This function is for testing. It prints all the attributes of the train object:
    def print_train(self):
        """Prints all attributes of the train for testing purposes."""
        next_junction = self.next_junction.name if self.next_junction else "None"
        prev_junction = self.prev_junction.name if self.prev_junction else "None"
        print("=========START=========\n")
        print(
            f"Name: {self.name}, Length: {self.length}, Speed: {self.current_speed} km/h, State: {self.state}, Next Junction: {next_junction}, Prev Junction: {prev_junction}"
        )
        print(f"Printing Location: ")
        front_cart_track = (
            self.location.front_cart["track"].name
            if self.location.front_cart["track"]
            else "None"
        )
        front_cart_junction = (
            self.location.front_cart["junction"].name
            if self.location.front_cart["junction"]
            else "None"
        )
        front_cart_position = self.location.front_cart["position"]
        back_cart_track = (
            self.location.back_cart["track"].name
            if self.location.back_cart["track"]
            else "None"
        )
        back_cart_junction = (
            self.location.back_cart["junction"].name
            if self.location.back_cart["junction"]
            else "None"
        )
        back_cart_position = self.location.back_cart["position"]
        print(
            f"    Front: Track: {front_cart_track}, Junction: {front_cart_junction}, Position: {round(front_cart_position,3)}"
        )
        print(
            f"    Back: Track: {back_cart_track}, Junction: {back_cart_junction}, Position: {round(back_cart_position,3)}"
        )
        print(f"Printing Route: ")

        if self.route is None:
            print("   Route is None")
        else:
            track = "   "
            for junction in self.route.junctions:
                track += junction.name + " -> "
            print(track)
            print(
                f"    Route's 'Current Junction Index': {self.route.current_junction_index}"
            )
        print("\n=========END=========")

    def __repr__(self):
        """Returns a string representation of the Train instance."""
        return f"Train({self.name}, Speed: {self.current_speed} km/h)"
