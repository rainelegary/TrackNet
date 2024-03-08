
import TrackNet_pb2
from classes.railway import Railway
from classes.railmap import RailMap
from classes.train import Train
from classes.route import Route
from classes.track import Track
from classes.junction import Junction
from classes.location import Location


class MessageConverter:
    
    @staticmethod
    def railway_obj_and_ts_to_msg(railway: Railway, timestamp: str) -> TrackNet_pb2.RailwayUpdate:
        pass

    
    @staticmethod
    def railway_msg_to_obj_and_ts(msg: TrackNet_pb2.RailwayUpdate) -> "tuple[Railway, str]":
        pass

    
    @staticmethod
    def railmap_obj_to_msg(railmap: RailMap) -> TrackNet_pb2.Railmap:
        pass

    
    @staticmethod
    def railmap_msg_to_obj(msg: TrackNet_pb2.Railmap) -> RailMap:
        pass


    @staticmethod
    def junction_obj_to_msg(junction: Junction) -> TrackNet_pb2.Junction:
        pass

    
    @staticmethod
    def junction_msg_to_obj(msg: TrackNet_pb2.Junction) -> Junction:
        pass
    

    @staticmethod
    def track_obj_to_msg(track: Track) -> TrackNet_pb2.Track:
        pass

    
    @staticmethod
    def track_msg_to_obj(msg: TrackNet_pb2.Track) -> Track:
        pass

    @staticmethod
    def train_obj_to_msg(train: Train) -> TrackNet_pb2.Train:
        pass

    
    @staticmethod
    def train_msg_to_obj(msg: TrackNet_pb2.Train) -> Train:
        pass


    @staticmethod
    def location_obj_to_msg(location: Location) -> TrackNet_pb2.Location:
        pass

    
    @staticmethod
    def location_msg_to_obj(msg: TrackNet_pb2.Location) -> Location:
        pass


    @staticmethod
    def route_obj_to_msg(route: Route) -> TrackNet_pb2.Route:
        pass

    
    @staticmethod
    def route_msg_to_obj(msg: TrackNet_pb2.Route) -> Route:
        pass


    

