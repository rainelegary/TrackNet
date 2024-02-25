import logging
from classes.enums import TrackCondition, TrackSpeed

class Track:
    """Represents a track connecting two junctions.
    
    Attributes:
        start_junction (Junction): The starting junction of the track.
        end_junction (Junction): The ending junction of the track.
        length (int): The length of the track.
        name (str): The name of the track, represented as 'Start->End'.
        trains (list): A list of trains currently running on this track.
    """
    def __init__(self, junction_a, junction_b, length):
        self.junctions = tuple(sorted([junction_a, junction_b], key=lambda j: j.name))
        self.length = length
        self.name = f"Track ({self.junctions[0].name}, {self.junctions[1].name})"
        self.trains = {} 
        self.condition = TrackCondition.GOOD
        self.speed = TrackSpeed.FAST.value
    
    def add_train(self, train):
        """Adds a train to the track."""
        self.trains[train.name] = train
        
    def remove_train(self, train):
        """Removes a train from the track."""
        del self.trains[train.name]
