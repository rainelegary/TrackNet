
from enums import ClientState_TrackCondition

class Location:

    def __init__(
        self, 
        start_node:int, # the node it's coming from
        end_node:int, # the node it's heading towards
        distance_covered:int, # kilometers along track
    ):
        self.start_node = start_node
        self.end_node = end_node
        self.track_id = tuple(sorted([start_node, end_node])) # track id's have smaller node id listed first
        self.distance_covered: distance_covered


class Train:

    def __init__(
            self,
            id:int, # same as client's id
            length:int, # kilometers
            front_location:Location,
            back_location:Location,
            speed:int, # see README for speed specs
            track_condition:ClientState_TrackCondition,
            destination:int, # node id 
            route, # TODO give type hint once Route class is created
        ):
        self.id = id
        self.length = length
        self.front_location = front_location
        self.back_location = back_location
        self.speed = speed 
        self.track_condition = track_condition 
        self.destination = destination
        self.route = route

    def get_speed(self):
        return self.speed
    
    def set_speed(self, new_speed):
        self.speed = new_speed

    def get_route(self):
        return self.route

    def reroute(self, new_route):
        pass

    def get_destination(self):
        return self.destination

    def report_track_condition(self):
        return self.track_condition
    


