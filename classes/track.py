
from classes.enums import TrackCondition, TrainSpeed
import logging
LOGGER = logging.getLogger(__name__)

class Track:
    """Represents a track connecting two junctions.
    
    Attributes:
        start_junction (str): The starting junction of the track.
        end_junction (str): The ending junction of the track.
        length (int): The length of the track.
        name (str): The name of the track, represented as 'Start->End'.
        trains (list): A list of trains currently running on this track.
    """
    def __init__(self, junction_a, junction_b, length, condition=TrackCondition.GOOD, speed=TrainSpeed.FAST):
        self.junctions = tuple(sorted([junction_a, junction_b]))
        self.length = length
        self.name = f"Track ({self.junctions[0]}, {self.junctions[1]})"
        self.trains = None
        self.condition = condition
        self.speed = speed
    
    def add_train(self, train):
        """Adds a train to the track."""
        self.trains[train.name] = train
        
    def remove_train(self, train):
        """Removes a train from the track."""
        del self.trains[train]

    def print_track(self):
        """Prints the track's information."""
        print(f"Track: {self.name}, Length: {self.length}, Trains: {self.trains}, Condition: {self.condition}, Speed: {self.speed}")
