import logging
from classes.enums import TrackCondition 

class Track:
    """Represents a track connecting two junctions.
    
    Attributes:
        start_junction (Junction): The starting junction of the track.
        end_junction (Junction): The ending junction of the track.
        length (int): The length of the track.
        name (str): The name of the track, represented as 'Start->End'.
        trains (list): A list of trains currently running on this track.
    """
    def __init__(self, start_junction, end_junction, length):
        self.start_junction = start_junction
        self.end_junction = end_junction
        self.length = length
        self.name = f"{start_junction.name}->{end_junction.name}"
        self.trains = [] 
        self.condition = TrackCondition.GOOD
    
    def add_train(self, train):
        """Adds a train to the track."""
        self.trains.append(train)
        
    def remove_train(self, train_id):
        for train in self.trains:
            if train.name == train_id:
                self.trains.remove(train)
                return

    def update_train_position(self, train_name, front_position):
        """Updates the position of a specific train on the track."""
        for train in self.trains:
            if train.name == train_name:
                train.update_position(front_position, self.length)
                return
        print(f"Train {train_name} not found on track {self.name}.")
