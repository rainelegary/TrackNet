class Junction:
    """Represents a railway junction where tracks start or end.
    
    Attributes:
        name (str): The name of the junction.
        neighbors (dict): A dictionary mapping neighbor junction names to the tracks that connect to them.
        parked_trains (dict): A collection of trains that are currently parked at this junction.
    """
    def __init__(self, name):
        self.name = name
        self.neighbors = {}  # Mapping neighbor junction names to track objects
        self.parked_trains = {}  # Store parked trains by name

    def add_neighbor(self, neighbor_junction, track):
        """Adds a neighboring junction and the connecting track to this junction."""
        self.neighbors[neighbor_junction.name] = track

    def park_train(self, train):
        """Parks a train at the junction."""
        self.parked_trains[train.name] = train

    def depart_train(self, train):
        """Departs a train from the junction."""
        del self.parked_trains[train.name]