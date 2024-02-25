from enums import ClientState_TrackCondition

class Train:

    def __init__(
            self, 
            client_id:int, 
            speed:int, # see README for speed specs
            track_condition:ClientState_TrackCondition
        ):
        self.client_id = client_id
        self.speed = speed 
        self.track_condition = track_condition 

    def get_speed(self):
        return self.speed
    
    def set_speed(self, speed):
        self.speed = speed

    def reroute(self, new_route):
        pass

    def report_track_condition(self):
        return self.track_condition

