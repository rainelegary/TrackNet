from datetime import datetime

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
    """
    def __init__(self, name, length):
        self.name = name
        self.length = length
        self.front_position = 0.0 
        self.back_position = 0.0
        self.current_track = None
        self.current_junction = None 
        self.current_junction_index = 0
        self.route = []
        self.current_speed = 0.0  
        self.last_time_updated = datetime.now()  

    def update_position(self, front_position, track_length):
        """Updates the train's position on the track, recalculates back position"""
        self.front_position = front_position
        self.back_position = max(0.0, front_position - (self.length / track_length) * 100) # Calculates percentage of the train length on the track and subtracts it fromt he frnt position
        self.last_time_updated = datetime.now()

    def park_at_junction(self, junction):
        """Parks the train at a specified junction and resets speed to 0."""
        self.current_junction = junction  # Set the current junction to the specified junction
        self.current_track = None  # Clear the current track since the train is now parked
        self.current_speed = 0  # Reset speed when parked
        self.last_time_updated = datetime.now()

    def place_on_track(self, track):
        """Places the train on a specified track."""
        self.current_track = track # Set the current track to the specified track 
        self.current_junction = None # Clear the current junction since the train is now moving
        self.current_speed = 50 # Set speed to a speed on the track (need to create universal constants for this or base it off of the track)
        self.last_time_updated = datetime.now() 
    
    def set_speed(self, new_speed):
        self.speed = new_speed

    def __repr__(self):
        location = self.current_junction.name if self.current_junction else self.current_track.name
        return f"Train({self.name}, Location: {location}, Speed: {self.current_speed} km/h, Last Updated: {self.last_time_updated})"
    
    def set_route(self, route):
        self.route = route
        self.current_position = 0
        self.distance_covered = 0

    def move_along_route(self):
        # Check if there's a next track in the route
        if self.current_junction_index < len(self.route) - 1:
            if self.current_track:
                # Calculate elapsed time since the last update
                now = datetime.now()
                elapsed_time = (now - self.last_time_updated).total_seconds()

                # Adjust the speed to achieve desired movement
                speed_factor = 10  # Adjust this factor as needed
                effective_speed = self.current_speed * speed_factor
                # Update the distance covered based on adjusted speed and elapsed time
                distance_moved = (effective_speed * elapsed_time) / 3600  # Convert speed to km/h
                self.distance_covered += distance_moved

                # Check if the train has reached the end of the current track
                if self.distance_covered >= self.current_track.length:
                    # Reset distance covered for the next track
                    self.distance_covered = 0
                    # Move to the next track in the route
                    self.current_junction_index += 1
                    if self.current_junction_index < len(self.route) - 1:
                        self.current_track = self.route[self.current_junction_index].neighbors[self.route[self.current_junction_index + 1].name]
                        print(f"Train {self.name} has moved to the next track: {self.current_track.name}")
                    else:
                        print(f"Train {self.name} has completed its route.")
                else:
                   print(f"Train {self.name} is moving on {self.current_track.name}, distance covered: {self.distance_covered:.2f} km")
                
                # Update the last time the train's position was updated
                self.last_time_updated = now
            else:
                # If the train is not on a track, it should be placed on the first track of its route
                # This part is simplified; you'd need logic to select the correct track based on the train's current position in the route
                pass
        else:
            print(f"Train {self.name} has no more tracks to move along its route.")    
    

class Map:
    """Represents the entire railway map, containing junctions and tracks.
    
    Attributes:
        junctions (dict): Stores junctions by their names.
        tracks (list): A list of all tracks in the map.
        trains (dict): Strores trains by their name 
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
            if train.current_track:
                train.current_track.trains.remove(train)

            junction.park_train(train)
            train.park_at_junction(junction)
            print(f"Train {train_name} parked at junction {junction_name}.")
        else:
            print(f"Train {train_name} not found or junction {junction_name} does not exist.")

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
    
    

