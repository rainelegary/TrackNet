import datetime
import logging
import time
import TrackNet_pb2
from classes.location import *
from classes.route import *
from classes.junction import *
from classes.enums import *
from classes.railmap import *

LOGGER = logging.getLogger(__name__)


class Train:
    """Represents a train running on the tracks or parked at a junction.

    Attributes:
        name (str): The name of the train.
        length (float): The length of the train as a percentage of the track's length.
        current_speed (float): The current speed of the train in units per time (e.g., km/h).
        last_time_updated (datetime): The last time the train's position or speed was updated.
        route (str []): A list of strings denoting the junctions in a train's route
    """

    def __init__(
        self,
        name = None, # Name will be assigned later if this is a client's train class
        length = 1000, # in meters
        junction_front:Junction = None, # junction ID
        junction_back:Junction = None,
    ):
        self.name = name
        self.length = length
        self.state = TrainState.PARKED
        self.location = Location(junction_front, junction_back)
        self.route = None
        #speed is set by the server
        self.current_speed = 0 
        self.next_junction = None
        self.prev_junction = None

    def set_route(self, route):
        self.route = route

    def set_speed(self, new_speed):
        self.current_speed = new_speed

    def get_speed(self):
        return self.current_speed

    # This function is for testing. It prints all the attributes of the train object:
    def print_train(self):
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
            f"    Front: Track: {front_cart_track}, Junction: {front_cart_junction}, Position: {front_cart_position}"
        )
        print(
            f"    Back: Track: {back_cart_track}, Junction: {back_cart_junction}, Position: {back_cart_position}"
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
        return f"Train({self.name}, Speed: {self.current_speed} km/h)"
