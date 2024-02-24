import datetime

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
