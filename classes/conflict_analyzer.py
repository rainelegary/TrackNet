
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
        # priority queue of conflicts (address high priority ones first)

        # create a map from train id to conflict instance 
        #(this allows for quick identification of all conflicts related to a given train)

        # commands dictionary. maps: train id -> list of commands to give to that train.
        commands = {}





        # returns a dictionary containing the commands to give to each train.
        return commands
    

    @staticmethod
    def reroute(railway, commands, train_id, junction_blacklist, track_blacklist): # throws CannotRerouteException
        pass
    

    """
    Resolve a conflict that may occur on train's current track

    Prevention Hierarchy:
        1. Slow
        2. Stop
        3. Reverse (TODO later potentially) 
    """
    @staticmethod
    def resolve_current_track_conflict(railway, commands, track_id):
        track = railway
        trains = []
        
    
    """
    Resolve a conflict that may occur once trains enter the junction the are heading towards

    Prevention Hierarchy:
        1. Slow
        2. Stop
        3. Reverse (TODO later potentially)
    """
    @staticmethod
    def resolve_immediate_junction_conflict(railway, commands, junction_id):
        pass


    """
    Resolve a conflict that may occur once train goes on its next track

    Prevention Hierarchy:
        1. Park
        2. Re-route
        3. Stop
    """
    @staticmethod
    def resolve_next_track_conflict(railway, commands, train_id, junction_blacklist, track_blacklist): 
        # TODO later
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
        # TODO later
        
        # try parking

        # reroute if no parking available
        try:
            return
        except CannotRerouteException:
            pass

        # stop if cannot reroute
        


