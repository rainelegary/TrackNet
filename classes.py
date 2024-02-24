from datetime import datetime
import logging
import time
from classes.location import Location
from queue import PriorityQueue


LOGGER = logging.getLogger(__name__)

class Junction:
    """Represents a railway junction where tracks start or end.
    
    Attributes:
        name (str): The name of the junction.
        neighbors (dict): A dictionary mapping neighbor junction names to the tracks that connect to them.
        parked_trains (list): A list of Train objects that are currently parked at this junction.
    """
    def __init__(self, name):
        self.name = name
        self.neighbors = {}  # Mapping neighbor junction names to track objects
        self.parked_trains = []  # List to hold multiple trains

    def add_neighbor(self, neighbor_junction, track):
        """Adds a neighboring junction and the connecting track to this junction."""
        self.neighbors[neighbor_junction.name] = track

    def park_train(self, train):
        """Parks a train at the junction."""
        self.parked_trains.append(train)

    def depart_train(self, train_name):
        """Departs a train from the junction by its name."""
        self.parked_trains = [train for train in self.parked_trains if train.name != train_name]

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
    
    def add_train(self, train):
        """Adds a train to the track."""
        self.trains.append(train)

    def update_train_position(self, train_name, front_position):
        """Updates the position of a specific train on the track."""
        for train in self.trains:
            if train.name == train_name:
                train.update_position(front_position, self.length)
                return
        print(f"Train {train_name} not found on track {self.name}.")

class Train:
    """Represents a train running on the tracks or parked at a junction.
    
    Attributes:
        name (str): The name of the train.
        length (float): The length of the train as a percentage of the track's length.
        front_position (float): The front position of the train on the track as a percentage (value between 0-100).
        back_position (float): The back position of the train on the track as a percentage (value between 0-100).
        current_track (Track): The track the train is currently on. None if parked.
        current_junction (Junction): The junction the train is currently parked at. None if on track.
        current_speed (float): The current speed of the train in units per time (e.g., km/h).
        last_time_updated (datetime): The last time the train's position or speed was updated.
        is_parked (Boolean): Indicates whether a train is currently parked or not
        distance_covered (float): Indicates distance covered on a specific track (km)
        route (str []): A list of strings denoting the junctions in a train's route
    """
    def __init__(
        self,
        name = None, # Name will be assigned later if this is a client's train class
        length = 1000, # in meters
        current_junction_front:int = None, # junction ID
        current_junction_back:int = None,
        destination:Junction = None,
    ):
        self.name = name
        self.length = length
        self.track = None
        self.location = Location(current_junction_front, current_junction_back, 0)
        ## (TODO) properly set route
        self.route = Route()
        #self.route = []
        
        self.track_distance_front = length
        self.track_distance_back = 0
        self.current_track_front = None
        self.current_track_back = None
        self.current_junction_front = current_junction_front
        self.current_junction_back = current_junction_back
        self.current_junction_index = 0
        self.distance_covered = 0
        self.destination = None
        self.railway_map = None
        self.destination = destination
        
        self.current_speed = 0 
        self.last_time_updated = datetime.now()
        self.is_parked = False

    def set_railway_map (self, railway_map):
        self.railway_map = railway_map

    def park_at_junction(self, junction):
        """Parks the train at a specified junction and resets speed to 0."""
        # Set the current junction to the specified junction
        self.is_parked = True
        self.current_junction_front = junction  
        self.current_junction_back  = junction
        
        # Clear the current track since the train is now parked
        self.current_track_front = None  
        self.current_track_back  = None 
        self.current_speed = 0  # Reset speed when parked
        self.last_time_updated = datetime.now()

    def place_on_track(self, track):
        """Places the train on a specified track."""
        self.current_track = track # Set the current track to the specified track 
        self.current_junction = None # Clear the current junction since the train is now moving
        self.current_speed = 50 # Set speed to a speed on the track (need to create universal constants for this or base it off of the track)
        self.last_time_updated = datetime.now() 
    
    def set_speed(self, new_speed):
        self.current_speed = new_speed

    def get_speed(self):
        return self.current_speed

    def stop(self):
        pass

    def __repr__(self):
        location = self.current_junction.name if self.current_junction else self.current_track.name
        return f"Train({self.name}, Location: {location}, Speed: {self.current_speed} km/h, Last Updated: {self.last_time_updated})"
    
    def set_route(self, route):
        self.route = route
        self.current_position = 0
        self.distance_covered = 0

    ## moved to client
    def move_along_route(self):
        now = datetime.now()
        elapsed_time = (now - self.last_time_updated).total_seconds()

        # Adjust the speed to achieve desired movement
        speed_factor = 10  # Adjust this factor as needed
        effective_speed = self.current_speed * speed_factor        
        distance_moved = effective_speed * (elapsed_time / 3600)  # Assuming speed is in km/h
        self.distance_covered += distance_moved
        # Update the last update time
        self.last_time_updated = now

        # Advance the front of the train
        if self.current_track_front:
            #self.distance_covered += distance_moved
            if self.distance_covered >= self.current_track_front.length:
                # The front reaches the end junction, mark this but don't move onto the next track yet
                self.current_junction_front = self.current_track_front.end_junction
                print(f"Train {self.name}'s front has reached {self.current_junction_front.name} junction.")
                self.current_track_front = None  # Clear the front track as it has reached the junction
            else:
                print(f"Train {self.name} is moving on track {self.current_track.name} ({self.current_track.length} km), distance covered front: {self.distance_covered:.2f} km, back: {self.distance_covered - self.length:.2f}")

        # Calculate if the back of the train has reached the end of its track
        distance_back_covered = self.distance_covered - self.length
        if distance_back_covered >= 0 and self.current_track_back:
            if distance_back_covered >= self.current_track_back.length:
                # The back reaches the junction, now handle the train's arrival
                self.current_junction_back = self.current_track_back.end_junction
                print(f"Train {self.name}'s back has reached {self.current_junction_back.name} junction.")
                self.current_track_back = None  # Clear the back track as it has reached the junction
                self.handle_train_arrival_at_junction()
            elif (not self.current_track_front):
                print(f"Train {self.name}'s back is still on the track, distance covered: ({distance_back_covered:.2f}) moving towards {self.current_junction_front.name} junction.")
        elif not self.current_track_back:
            # If there's no current track for the back, it means it's already at a junction or hasn't started moving yet
            self.handle_train_arrival_at_junction()

    ## switch tracks 
    def handle_train_arrival_at_junction(self):
        # Handle the train's full arrival at the junction and transition to the next track if applicable
        if not self.is_parked and self.current_junction_front and self.current_junction_front == self.current_junction_back:
            # Both front and back are at the same junction, proceed with the next part of the route
            self.park_at_junction(self.current_junction_front)
            self.railway_map.park_train_at_junction(self.name, self.current_junction_front.name)
            #print(f"Train {self.name} is now fully parked at {self.current_junction_front.name} junction.")

        if self.is_parked:
            # Introduce a delay]
            delay = 5
            print(f"Waiting at junction {self.current_junction_front.name} for {delay} seconds...")
            time.sleep(delay)  # Delay for 5 seconds
            self.move_to_next_track_or_park()
        elif not self.is_parked:
            print(f"Waiting for the back of the train to reach the junction...")

    ## stop 
    def move_to_next_track_or_park(self):
        # Advance the train onto the next track or mark it as parked if at the end of the route
        self.current_junction_index += 1
        if self.current_junction_index < len(self.route.tracks):
            next_track = self.current_junction_front.neighbors[self.route.tracks[self.current_junction_index].name]
            self.current_track_front = next_track
            self.current_track_back  = next_track
            self.is_parked = False
            print ("next track: " + next_track.name)
            self.distance_covered = 0  # Reset distance for the new track
            self.place_on_track(next_track)
            self.railway_map.add_train_to_track(self.name, next_track.name)
            #print(f"Train {self.name} is moving onto {next_track.name} from {self.current_junction_front.name}.")
        else:
            print(f"Train {self.name} has completed its route and is parked.")


class Map:
    """Represents the entire railway map, containing junctions and tracks.
    
    Attributes:
        junctions (dict): Stores junctions by their names.
        tracks (list): A list of all tracks in the map.
        trains (dict): Stores trains by their name 
    """
    def __init__(self):
        self.junctions = {}  # Stores junctions by name
        self.tracks = []  # List of tracks 
        self.trains = {} # store trains by name 
        
    
    def add_junction(self, name):
        """Adds a junction to the map."""
        if name not in self.junctions:
            junction = Junction(name)
            self.junctions[name] = junction
            return junction
        else:
            return self.junctions[name]
    
    def add_track(self, start_name, end_name, length):
        """Adds a track between two junctions."""
        if start_name in self.junctions and end_name in self.junctions:
            start_junction = self.junctions[start_name]
            end_junction = self.junctions[end_name]
            track = Track(start_junction, end_junction, length)
            self.tracks.append(track)
            start_junction.add_neighbor(end_junction, track)
        else:
            print("One or both junctions do not exist, adding them now.")
            
    def add_train(self, name, length):
        """Adds a new train to the map."""
        if name not in self.trains:
            self.trains[name] = Train(name, length)
        else:
            print(f"Train {name} already exists.")

    def add_train_to_track(self, train_name, track_name):
        """Places an existing train on a specified track by name."""
        #*Modify to remove train from parked junction if on one*

        if train_name in self.trains and any(track.name == track_name for track in self.tracks):
            train = self.trains[train_name]
            for track in self.tracks:
                if track.name == track_name:
                    track.add_train(train)
                    train.place_on_track(track)
                    print(f"Train {train_name} added to track {track_name}.")
                    return
            print(f"Track {track_name} not found.")
        else:
            print(f"Train {train_name} not found or track {track_name} does not exist.")
    
    def park_train_at_junction(self, train_name, junction_name):
        """Parks an existing train at a specified junction by name."""
        if train_name in self.trains and junction_name in self.junctions:
            train = self.trains[train_name]
            junction = self.junctions[junction_name]

            # Remove the train from its current track if it's on one
            if train.current_track_front:
                train.current_track_front.trains.remove(train)

            junction.park_train(train)
            train.park_at_junction(junction)
            print(f"Train {train_name} parked at junction {junction_name}.")
        else:
            print(f"Train {train_name} not found or junction {junction_name} does not exist.")

    def reroute_train(self, train_name, avoid_track_name):
        """
        Reroutes a train to avoid a specified track.

        :param train_name: The name of the train to reroute.
        :param avoid_track_name: The name of the track to avoid.
        """
        train = self.trains.get(train_name)
        if not train:
            print(f"No train found with the name {train_name}.")
            return

        # Destination is the last junction in the train's current route
        destination_junction = train.route.tracks[-1]

        # Find a new route from the train's current junction to the destination
        new_route = self.find_shortest_path(train.current_junction, destination_junction, avoid_track_name)

        if new_route:
            # Update the train's route
            train.set_route(new_route)
            print(f"Train {train_name} rerouted successfully.")
        else:
            print(f"No alternative route found for Train {train_name}.")

    # example usage = map_instance.find_shortest_path(start_junction_name="A", destination_junction_name="D", avoid_track_name="AB")
    def find_shortest_path(self, start_junction_name, destination_junction_name, avoid_track_name=None):
        distances = {junction: float('infinity') for junction in self.junctions}
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

    def reconstruct_path(self, previous_junctions, start, end):
        path = []
        current = end
        while current != start:
            if current is None:
                return None  # Path not found
            path.insert(0, current)
            current = previous_junctions[current]
        path.insert(0, start)
        return path

    def print_map(self):
        """Prints an overview of the map, including junctions, tracks, and parked or running trains."""
        print("Map Overview:")
        print("Junctions:")
        for junction_name, junction in self.junctions.items(): # iterate through junctions
            trains_info = ", ".join([train.name for train in junction.parked_trains])
            print(f"  Junction: {junction_name}, Parked Trains: [{trains_info}]")

        print("Tracks:")
        for track in self.tracks: # iterate through tracks
            running_trains = ", ".join([train.name for train in track.trains])
            print(f"  Track: {track.name}, Length: {track.length}, Running Trains: [{running_trains}]")
    
    

