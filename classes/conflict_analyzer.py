
from classes.enums import TrainState, TrainSpeed, TrackCondition
from classes.train import Train
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

    SAFETY_DISTANCE:
        The following distance used by trains
        Also how far to stop from a conflict site

    JUNCTION_CAPACITY:
        The maximum number of trains parked at a junction
    """

    SAFETY_DISTANCE = 3
    JUNCTION_CAPACITY = 2

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
            
        # slow
        for track_id in railway.tracks.keys():
            commands = ConflictAnalyzer.resolve_bad_track_condition(railway, commands, track_id)

        # stop
        for junction_id in railway.junctions.keys():
            commands = ConflictAnalyzer.resolve_immediate_junction_conflict(railway, commands, junction_id)

        # slow (without overriding stop) / stop
        for track_id in railway.tracks.keys():
            commands = ConflictAnalyzer.resolve_current_track_conflict(railway, commands, track_id)
        
        # returns a dictionary containing the commands to give to each train.
        return commands
    

    @staticmethod
    def may_enter_next_track(railway, commands, train_id):
        train = railway.trains[train_id]
        current_junction = train.location.front_cart["junction"]
        next_track = train.route.get_next_track()
        next_junction = train.route.get_next_junction()

        if Train.state not in [TrainState.PARKED, TrainState.PARKING]:
            return True # train is moving on a track

        # break ties by train id. wait for train with smaller id to go first
        favored_train_id = sorted(list(filter(
                lambda t: (railway.trains[t].route.get_next_track().name == next_track.name),
                current_junction.trains.keys()
            )))[0]

        if favored_train_id != train_id:
            return False

        if len(next_track.trains) == 0: 
            return True # track is empty

        # At this point in the code, we have ruled out the possibility that the track is empty.
        # Now determine direction of trains on track
        track_heading = next(iter(next_track.trains.values())).next_junction.name
        if track_heading != next_junction.name:
            return False # existing trains are moving opposite direction
        
        # train that has made the least progress along the track
        back_train = sorted(next_track.trains, key=lambda t: t.location.back_cart["position"])[0]

        # only go if the back train is far enough along the track
        return (back_train.location.back_cart["position"] > ConflictAnalyzer.SAFETY_DISTANCE)


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
    def resolve_bad_track_condition(railway, commands, track_id):
        if railway.tracks[track_id].condition == TrackCondition.BAD:
            for train in railway.tracks[track_id].trains.values():
                # message creation inside the for loop as the messages must be separate objects, 
                # as they may be overwritten in different ways in the future
                command = TrackNet_pb2.ServerResponse() 
                command.status = TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                command.speed = TrainSpeed.SLOW.value
                commands[train.name] = command
        
        return commands
    

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

        train_heading = next(iter(track.trains.values())).next_junction
        same_direction = all(train.next_junction == train_heading for train in track.trains.values())
        if not same_direction:
            raise CollisionException("Trains moving opposite directions on the same track") # TODO a collision hasn't necessarily occurred and we may recover if we reverse

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

        # determine available and in-demand tracks, as well as involved trains
        
        for track in junction.neighbors.values():
            trains = track.trains
            if not trains:
                available_tracks[track.name] = track
                continue

            # NOTE track heading is the junction that all trains on this track are heading to.
            # it is assumed to be the same for all trains on this track, meaning
            # they are all heading in the same direction.
            # If this is not the case, the an exception will be raised when resolving track conflicts.

            track_heading = next(iter(trains.values())).next_junction
            if track_heading == junction.name:
                for train in track.trains.values():
                    if track.length - train.location.front_cart["position"] < ConflictAnalyzer.SAFETY_DISTANCE:
                        involved_trains[train.name] = train
                    next_track = train.get_next_track()
                    in_demand_tracks[next_track.name] = next_track
            else:
                available_tracks[track.name] = track

        # determine a few more in demand tracks and involved trains
        
        for train in junction.parked_trains.values():
            involved_trains[train.name] = train
            next_track = train.get_next_track()
            in_demand_tracks[next_track.name] = next_track

        parking_trains = {}
        moving_trains = {} # unpark / keep moving
        stopping_trains = {}

        # determine what to do for each train 
        for train_id, train in involved_trains.items():

            may_enter_next_track = ConflictAnalyzer.may_enter_next_track(railway, commands, train_id)

            if (
                train.route.get_next_track().name in available_tracks
                and may_enter_next_track
            ):
                moving_trains[train_id] = train
                continue 

            if train.state in [TrainState.PARKED, TrainState.PARKING] and not may_enter_next_track:
                # cannot enter track yet; stay parked
                parking_trains[train_id] = train
                continue
            
            # can now assume train is moving and its next track is not available

            if (
                train.location.front_cart["track"].name in in_demand_tracks
                and train.state not in [TrainState.PARKED, TrainState.PARKING]
            ):
                if len(parking_trains) < ConflictAnalyzer.JUNCTION_CAPACITY:
                    # junction still has capacity
                    # issue "park" command
                    parking_trains[train_id] = train
                else:
                    # junction is full 
                    # issue "stop" command
                    stopping_trains[train_id] = train
                continue

            # otherwise (desired track occupied and on low demand track)
            # issue "stop" command to this train
            stopping_trains[train_id] = train


        # populate commands
        # each train has a different command object to allow for different references
        for train_id, train in parking_trains:
            command = TrackNet_pb2.ServerResponse()
            command.status = TrackNet_pb2.ServerResponse.UpdateStatus.PARK
            commands[train_id] = command
        
        for train_id, train in moving_trains:
            command = TrackNet_pb2.ServerResponse()
            command.status = TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR
            commands[train_id] = command
        
        for train_id, train in stopping_trains:
            command = TrackNet_pb2.ServerResponse()
            command.status = TrackNet_pb2.ServerResponse.UpdateStatus.STOP
            commands[train_id] = command

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

    
# railmap
    # junctions
        # id
        # neighboring track id's (change proto)
        # parked train id's (change proto)
    # tracks
        # junction_a id
        # junction_b id
        # id
        # train id's (change proto)
        # condition
        # speed
    # trains
        # id
        # length
        # state
        # location
            #
        # route
            #
        # destination junction id (change proto)
        # speed

    # train counter