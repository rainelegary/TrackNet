from classes.enums import TrackCondition, TrainSpeed
from classes.junction import Junction
from classes.train import Train
import logging

LOGGER = logging.getLogger(__name__)


class Track:
    """Represents a track connecting two junctions. A track is defined by its starting and ending junctions, length, and conditions such as track condition and allowed train speed.

    Attributes
    ----------
    junctions : tuple
        A tuple containing the names of the starting and ending junctions, sorted alphabetically.
    length : int
        The length of the track.
    name : str
        The name of the track, automatically generated based on the starting and ending junctions, formatted as 'Track (Start, End)'.
    trains : dict
        A dictionary of trains currently running on this track, keyed by train names.
    condition : TrackCondition
        The condition of the track, defaulting to TrackCondition.GOOD.
    speed : TrainSpeed
        The speed limit for trains on the track, defaulting to TrainSpeed.FAST.
    """

    def __init__(self, junction_a: Junction, junction_b, length, condition=TrackCondition.GOOD, speed=TrainSpeed.FAST):
        """Initializes a Track instance.

        :param junction_a: The name of one junction connected by the track.
        :param junction_b: The name of the other junction connected by the track.
        :param length: The length of the track.
        :param condition: The condition of the track, affecting train movement. Defaults to TrackCondition.GOOD.
        :param speed: The speed limit for trains on the track, influencing how fast trains can go. Defaults to TrainSpeed.FAST.
        """
        self.junctions = tuple(sorted([junction_a, junction_b]))
        self.length = length
        self.name = f"Track ({self.junctions[0]}, {self.junctions[1]})"
        self.trains = {}
        self.condition = condition
        self.speed = speed

    def add_train(self, train: Train):
        """Adds a train to the track.

        :param train: The train to be added to the track.
        """
        self.trains[train.name] = train

    def remove_train(self, train: Train):
        """Removes a train from the track.

        :param train: The train to be removed from the track.
        """
        del self.trains[train]

    def print_track(self):
        """Prints the track's detailed information, including its name, length, current trains, condition, and speed limit."""
        print(f"Track: {self.name}, Length: {self.length}, Trains: {self.trains}, Condition: {self.condition}, Speed: {self.speed}")
