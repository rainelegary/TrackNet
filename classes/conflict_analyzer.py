
from enums import TrainState

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

    @staticmethod
    def resolve_conflicts(railway):
        # priority queue of conflicts (address high priority ones first) (TODO for later demoes)

        # create a map from train id to conflict instance (TODO for later demoes)
        # (this allows for quick identification of all conflicts related to a given train)


        # commands dictionary. maps: train id -> list of commands to give to that train.
        commands = {}

        for junction in railway.junctions:
            commands = ConflictAnalyzer.resolve_immediate_junction_conflict(railway, commands, junction)


        for track in railway.tracks:
            commands = ConflictAnalyzer.resolve_current_track_conflict(railway, commands, track)

        # returns a dictionary containing the commands to give to each train.
        return commands
    

    @staticmethod
    def reroute(railway, commands, train_id, junction_blacklist, track_blacklist): # throws CannotRerouteException
        pass # new reroute function TODO in later iterations
    

    """
    Resolve a conflict that may occur on train's current track

    Prevention Hierarchy:
        1. Slow
        2. Stop
        3. Reverse (TODO later potentially) 
    """
    @staticmethod
    def resolve_current_track_conflict(railway, commands, track_id):
        track = railway.tracks[track_id]

        # Determine if in same direction
        def get_heading(train):
            return train.location.front_cart["junction"].name

        train_heading = get_heading(next(iter(track.trains.values())))
        same_direction = all(get_heading(train) == train_heading for train in track.trains)
        if not same_direction:
            raise CollisionException() # TODO a collision hasn't necessarily occurred and we may recover if we reverse

        # Sort trains front to back
        sorted_trains = sorted(track.trains, key=lambda train: train.location.back_cart["position"], reverse=True)

        # Slow down trains starting front to back
        for i, train in enumerate(sorted_trains):
            if i == 0:
                continue
            
            # TODO POC
            # if there exists a command telling this train to slow down, then:
                # slow down all trains that are behind this one.
                # if a train is already recieving a slow down or stop command,
                # then it would be redundant to tell it to slow down again
                # so skip over those cases.
            
            # NOTE we'll need some sort of command data structure to represent commands
                
            break # already told all following trains to slow down so can exit loop
        

        # Stop trains starting front to back
        for i, train in enumerate(sorted_trains):
            if i == 0:
                continue
            
            # TODO POC
            # if there exists a command telling this train to stop, then:
                # slow down all trains that are behind this one.
                # if a train is already recieving a stop command,
                # then it would be redundant to tell it to stop again,
                # so skip over those cases.
                # If it is being told to slow down, delete the slow down command and replace it with a stop command
            
            # NOTE we'll need some sort of command data structure to represent commands
                
            break # already told all following trains to stop so can exit loop

        return commands # updated set of commands
        
    
    """
    Resolve a conflict that may occur once trains enter the junction the are heading towards

    Prevention Hierarchy:
        1. Slow
        2. Stop
        3. Reverse (TODO later potentially)
    """
    @staticmethod
    def resolve_immediate_junction_conflict(railway, commands, junction_id):

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
        


