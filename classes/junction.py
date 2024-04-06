import logging

LOGGER = logging.getLogger(__name__)

class Junction:
    """Represents a railway junction where tracks start or end.
    
    Attributes
    ----------
    name : str
        The name of the junction.
    neighbors : dict
        A dictionary mapping neighbor junction names to the tracks that connect to them. This allows the junction to know which tracks lead to which neighboring junctions.
    parked_trains : dict
        A collection (dictionary) of trains that are currently parked at this junction, keyed by train names.
    """
    def __init__(self, name: str):
        """Initializes a Junction instance with a given name.

        :param name: The name of the junction.
        """
        self.name = name
        self.neighbors = {}  # Mapping neighbor junction names to track objects
        self.parked_trains = {}  # Store parked trains by name

    def add_neighbor(self, neighbor_junction, track):
        """Adds a neighboring junction and the track that connects this junction to the neighbor.

        :param neighbor_junction: The neighboring junction object.
        :param track: The track object that connects this junction to the neighbor junction.
        """
        self.neighbors[neighbor_junction.name] = track

    def park_train(self, train):
        """Parks a train at this junction, adding it to the ``parked_trains`` dictionary.

        :param train: The train object to be parked at the junction.
        """
        self.parked_trains[train.name] = train

    def depart_train(self, train):
        """Departs a train from this junction, removing it from the ``parked_trains`` dictionary.

        :param train: The train object to be departed from the junction.
        """
        del self.parked_trains[train.name]