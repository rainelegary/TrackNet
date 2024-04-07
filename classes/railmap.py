import logging
from classes.junction import Junction
from classes.enums import TrackCondition
from classes.track import Track
from queue import PriorityQueue

LOGGER = logging.getLogger(__name__)


class Railmap:
    """Manages the layout of the railway network, including junctions and tracks. It provides functionalities to add junctions, tracks, and to query the railway map's state.

    Attributes
    ----------
    junctions : dict
        A dictionary that stores junction objects by their names.
    tracks : dict
        A collection that stores track objects, with track names as keys.
    """

    def __init__(self, junctions=None, tracks=None):
        """Initializes the Railmap with optional lists of junctions and tracks.

        :param junctions: An optional list of junction names to be added to the map upon initialization. Defaults to None.
        :param tracks: An optional list of tuples defining tracks. Each tuple contains the names of two junctions connected by the track and the track's length. Defaults to None.
        """
        self.junctions = {}  # Stores junctions by name
        self.tracks = {}  # Collection of tracks

        if junctions:
            for junction_name in junctions:
                self.add_junction(junction_name)

        if tracks:
            for track_info in tracks:
                self.add_track(*track_info)

    def add_junction(self, name: str) -> Junction:
        """Adds a new junction to the railway map by name.

        :param name: The name of the junction to be added.
        :return: The Junction object created or retrieved.
        """
        if name not in self.junctions:
            junction = Junction(name)
            self.junctions[name] = junction
            return junction
        else:
            return self.junctions[name]

    def add_track(self, junction_a_name: str, junction_b_name: str, length: int):
        """Adds a new track between two specified junctions.

        :param junction_a_name: The name of the first junction.
        :param junction_b_name: The name of the second junction.
        :param length: The length of the track connecting the two junctions.
        """
        if junction_a_name in self.junctions and junction_b_name in self.junctions:
            junction_a: Junction = self.junctions[junction_a_name]
            junction_b: Junction = self.junctions[junction_b_name]
            track = Track(junction_a_name, junction_b_name, length)
            self.tracks[track.name] = track
            junction_a.add_neighbor(junction_b, track)
            junction_b.add_neighbor(junction_a, track)
        else:
            LOGGER.debug("One or both junctions do not exist, adding them now.")

    def set_track_condition(self, track_id: str, condition: TrackCondition):
        """Sets the condition of a specified track.

        :param track_id: The identifier (name) of the track.
        :param condition: The new condition to be set for the track.
        """
        self.tracks[track_id].condition = condition

    def has_bad_track_condition(self, track_id: str) -> bool:
        """Checks if a specified track has a BAD condition.

        :param track_id: The identifier (name) of the track.
        :return: True if the track's condition is BAD, False otherwise.
        """
        return self.tracks[track_id].condition == TrackCondition.BAD

    def get_origin_destination_junction(self):
        """Returns the origin and destination junctions of the railway map.

        :return: A tuple containing the origin and destination Junction objects.
        """
        return self.junctions["A"], self.junctions["D"]

    def find_shortest_path(self, start_junction_name: str, destination_junction_name: str, avoid_track_name=None):
        """Finds the shortest path between two junctions, optionally avoiding a specified track.

        example usage = map_instance.find_shortest_path(start_junction_name="A", destination_junction_name="D", avoid_track_name="AB")

        :param start_junction_name: The name of the start junction.
        :param destination_junction_name: The name of the destination junction.
        :param avoid_track_name: An optional track name to avoid in the pathfinding. Defaults to None.
        :return: A list of Junction objects representing the shortest path.
        """
        distances = {junction: float("infinity") for junction in self.junctions}
        previous_junctions = {junction: None for junction in self.junctions}
        distances[start_junction_name] = 0

        pq = PriorityQueue()
        pq.put((0, start_junction_name))

        while not pq.empty():
            current_distance, current_junction_name = pq.get()
            current_junction = self.junctions[current_junction_name]

            if current_junction_name == destination_junction_name:
                break

            for neighbor_name, track in current_junction.neighbors.items():
                if track.name == avoid_track_name:
                    continue

                distance = current_distance + track.length
                if distance < distances[neighbor_name]:
                    distances[neighbor_name] = distance
                    previous_junctions[neighbor_name] = current_junction_name
                    pq.put((distance, neighbor_name))

        return self.reconstruct_path(previous_junctions, start_junction_name, destination_junction_name)

    def reconstruct_path(self, previous_junctions: dict, start: str, end: str) -> list:
        """Reconstructs a path from start to end junction using the data from pathfinding.

        :param previous_junctions: A dictionary mapping each junction to its predecessor on the path.
        :param start: The name of the start junction.
        :param end: The name of the end junction.
        :return: A list of Junction objects representing the path.
        """
        path = []
        current = end
        while current != start:
            if current is None:
                return None  # Path not found
            path.insert(0, self.junctions[current])
            current = previous_junctions[current]
        path.insert(0, self.junctions[start])
        return path

    def print_map(self):
        """Prints the details of the railmap, including information about junctions, tracks, and parked or running trains."""
        print("Junctions:")
        for junction in self.junctions.values():
            print(
                f"  Junction: {junction.name}. Trains parked: {len(junction.parked_trains)}"
            )
            for parker_train in junction.parked_trains.values():
                print(f"        {parker_train.name}")
        print("\nTracks:")
        for track in self.tracks.values():
            print(
                f"  Track: {track.name}. Length: {track.length}. Condition: {track.condition}. Speed: {track.speed}. Trains on track: {len(track.trains) if track.trains else 0}"
            )
            for train in track.trains.values():
                print(f"        {train.name}")
