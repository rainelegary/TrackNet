
from classes.enums import TrainState, TrainSpeed, TrackCondition
import TrackNet_pb2


class CannotRerouteException(Exception):
    pass


class CollisionException(Exception):
    pass


class Conflict:
    def __init__(self, priority):
        self.priority = priority


class ImmediateJunctionConflict(Conflict):
    def __init__(self, priority, junction_id):
        super().__init__(priority)
        self.junction_id = junction_id


class ImmediateTrackConflict(Conflict):
    def __init__(self, priority, track_id):
        super().__init__(priority)
        self.track_id = track_id


class ConflictAnalyzer:
    """
    The class uses for detecting conflicts within the railway system
    and issuing commands to trains to prevent collisions.

    command format:
        change speed
            new speed (enum)
        reroute
            list of junctions (including most recently visited)
        stop
        clear

    command priority:
        stop
        slow
        park
        reroute
        clear
        fast
    """

    @staticmethod
    def resolve_conflicts(railway, commands):
        # priority queue of conflicts (address high priority ones first) (TODO for later demoes)

        # create a map from train id to conflict instance (TODO for later demoes)
        # (this allows for quick identification of all conflicts related to a given train)


        # commands dictionary. maps: train id -> list of commands to give to that train.
        commands = {}

        # fast and clear
        for train in railway.trains:
            command = TrackNet_pb2.ServerResponse()
            command.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR
            command.speed = TrainSpeed.FAST.value
            commands[train.name] = command

        # TODO reroute

        # TODO park

        # stop
        for junction in railway.junctions:
            commands = ConflictAnalyzer.resolve_immediate_junction_conflict(railway, commands, junction)

        # slow (without overriding stop) / stop
        for track in railway.tracks:
            commands = ConflictAnalyzer.resolve_current_track_conflict(railway, commands, track)
        
        # returns a dictionary containing the commands to give to each train.
        return commands
    

    @staticmethod
    def reroute(railway, commands, train_id, junction_blacklist, track_blacklist): # throws CannotRerouteException
        pass # new reroute function TODO in later iterations
    
    
    # def reroute_train(self, train_name, avoid_track_name):
    #     """
    #     Previous implemenation as written in the server class
    #     """


    #     """
    #     Reroutes a train to avoid a specified track.

    #     :param train_name: The name of the train to reroute.
    #     :param avoid_track_name: The name of the track to avoid.
    #     """
    #     train = self.trains[train_name]
    #     if not train:
    #         print(f"No train found with the name {train_name}.")
    #         return

    #     # Destination is the last junction in the train's current route
    #     destination_junction = train.route.tracks[-1]

    #     # Find a new route from the train's current junction to the destination
    #     new_route = self.map.find_shortest_path(train.current_junction, destination_junction, avoid_track_name)

    #     if new_route:
    #         # Update the train's route
    #         train.set_route(new_route)
    #         print(f"Train {train_name} rerouted successfully.")
    #     else:
    #         print(f"No alternative route found for Train {train_name}.")
    

    @staticmethod
    def resolve_current_track_conflict(railway, commands, track_id):
        """
        Resolve a conflict that may occur on train's current track.

        Prevention Hierarchy:
            1. Slow
            2. Stop
            3. Reverse (TODO later potentially) 

        :param railway: railway with trains, tracks and junctions
        :param commands: a dictionary that maps train id to a pending server response
        :param track_id: id of the track we are preventing conflicts on
        """
        track = railway.tracks[track_id]

        # Determine if in same direction
        def get_heading(train):
            return train.location.front_cart["junction"].name

        train_heading = get_heading(next(iter(track.trains.values())))
        same_direction = all(get_heading(train) == train_heading for train in track.trains)
        if not same_direction:
            raise CollisionException() # TODO a collision hasn't necessarily occurred and we may recover if we reverse

        if railway.tracks[track_id].condition == TrackCondition.BAD:
            for train in railway.trains:
                command = TrackNet_pb2.ServerResponse()
                command.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                command.speed = TrainSpeed.SLOW.value
                commands[train.name] = command

        # Sort trains front to back
        sorted_trains = sorted(track.trains, key=lambda train: train.location.back_cart["position"], reverse=True)

        # Slow down trains starting front to back
        for i, train in enumerate(sorted_trains):
            if i == 0:
                continue
            
            # if there exists a command telling this train to slow down, then:
                # slow down all trains that are behind this one.
                # if a train is recieving a stop command,
                # then do not overwrite it with a slow command.
            
            if ( 
                commands[train.name].HasField("speed")
                and commands[train.name].speed == TrainSpeed.SLOW.value
            ):
                # If this condition is true, then this train is either moving slow or has a command telling it to slow down.
                for train_j_id in range(i + 1, len(sorted_trains)):
                    train_j = sorted_trains[train_j_id]

                    if commands[train_j.name].status == TrackNet_pb2.UpdateStatus.STOP:
                        # skip this train; a stop command 
                        # cannot be overwritten by a slow command
                        continue 

                    # overwrite previous command with slow command
                    command = TrackNet_pb2.ServerResponse()
                    command.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                    command.speed = TrainSpeed.SLOW.value
                    commands[train_j.name] = command
                
                break # already told all following trains to slow down so can exit loop

        # Stop trains starting front to back
        for i, train in enumerate(sorted_trains):
            if i == 0:
                continue
            
            # if there exists a command telling this train to stop, then:
                # slow down all trains that are behind this one.
                # if a train is already recieving a stop command,
                # then it would be redundant to tell it to stop again,
                # so skip over those cases.
            
            if ( 
                commands[train.name].HasField("status")
                and commands[train.name].status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP
            ):
                # If this condition is true, then this train is either moving slow or has a command telling it to slow down.
                for train_j_id in range(i + 1, len(sorted_trains)):
                    train_j = sorted_trains[train_j_id]

                    # overwrite previous command with stop command
                    command = TrackNet_pb2.ServerResponse()
                    command.status = TrackNet_pb2.ServerResponse.UpdateStatus.STOP
                    commands[train_j.name] = command
                
                break # already told all following trains to stop so can exit loop

        return commands # updated set of commands
        
    
    @staticmethod
    def resolve_immediate_junction_conflict(railway, commands, junction_id):
        """
        Resolve a conflict that may occur once trains enter the junction the are heading towards

        Prevention Hierarchy:
            1. Slow
            2. Stop
            3. Reverse (TODO later potentially)

        :param railway: railway with trains, tracks and junctions
        :param commands: a dictionary that maps train id to a pending server response
        :param junction_id: if of the junction we are preventing conflicts on
        """
        junction = railway.junctions[junction_id]

        involved_trains = {} # all trains heading towards or already parked in this junction
        available_tracks = {} # all tracks that do not have trains heading towards this junction
        in_demand_tracks = {} # all tracks that at least one train wants to exit onto

        def get_heading(train):
            return train.location.front_cart["junction"].name

        # determine available and in-demand tracks, as well as involved trains
        
        for track in junction.neighbors.values():
            trains = track.trains
            if not trains:
                available_tracks[track.name] = track
                continue

            # NOTE track heading is the junction that all trains on this track are heading to.
            # it is assumed to be the same for all trains on this track, meaning
            # they are all heading in the same direction.
            # If this is not the case, the an exception will have been raised when resolving track conflicts.

            track_heading = get_heading(next(iter(trains.values())))
            if track_heading == junction.name:
                for train in track.trains:
                    involved_trains[train.name] = train
                    next_track = train.get_next_track()
                    in_demand_tracks[next_track.name] = next_track
            else:
                available_tracks[track.name] = track

        # determine a few more in demand tracks and involved trains
        
        for train in junction.parked_trains:
            involved_trains[train.name] = train
            next_track = train.get_next_track()
            in_demand_tracks[next_track.name] = next_track


        # determine what to do for each train 
        for train in involved_trains:

            # TODO POC - use some kind of command data structure

            if train.get_next_track().name in available_tracks:
                continue # keep going, or start moving if not moving yet

            if train.state in [TrainState.PARKED, TrainState.PARKING]:
                continue # do nothing until desired track clears up (stay parked)

            if train.location.front_cart["track"] in in_demand_tracks:
                # if junction still has capacity
                    # issue "park" command
                # otherwise
                    # issue "stop" command
                continue

            # otherwise (desired track occupied and on low demand track)
            # issue "stop" command to this train

        return commands


    """
    Resolve a conflict that may occur once train goes on its next track

    Prevention Hierarchy:
        1. Park
        2. Re-route
        3. Stop
    """
    @staticmethod
    def resolve_next_track_conflict(railway, commands, train_id, junction_blacklist, track_blacklist): 
        # TODO in later iterations
        pass
        

    """
    Resolve a conflict that may occur once train enters the junction that is after the train's next track

    Prevention Hierarchy:
        1. Park
        2. Re-route
        3. Stop
    """
    @staticmethod
    def resolve_later_junction_conflict(railway, commands, train_id, junction_blacklist, track_blacklist): 
        # TODO in later iterations
        
        # try parking

        # reroute if no parking available
        try:
            return
        except CannotRerouteException:
            pass

        # stop if cannot reroute

    
        


