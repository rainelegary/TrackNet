
import TrackNet_pb2
from classes.railway import Railway
from classes.railmap import RailMap
from classes.train import Train
from classes.route import Route
from classes.track import Track
from classes.junction import Junction
from classes.location import Location
from classes.enums import TrackCondition


class MessageConverter:
    
    @staticmethod
    def railway_obj_and_ts_to_railway_update_msg(railway: Railway, timestamp: str) -> TrackNet_pb2.RailwayUpdate:
        msg = TrackNet_pb2.RailwayUpdate()
        msg.railway = MessageConverter.railway_obj_to_msg(railway)
        msg.timestamp = timestamp

        return msg

    
    @staticmethod
    def railway_update_msg_to_railway_obj_and_ts(msg: TrackNet_pb2.RailwayUpdate) -> "tuple[Railway, str]":
        pass


    @staticmethod
    def railway_obj_to_msg(railway: Railway) -> TrackNet_pb2.Railway:
        msg = TrackNet_pb2.Railway()
        msg.map = MessageConverter.railmap_obj_to_msg(railway.map)
        for train_name, train in railway.trains.items():
            msg.trains[train_name] = MessageConverter.train_obj_to_msg(train)
        msg.train_counter = len(railway.trains)

        return msg

    
    @staticmethod
    def railway_msg_to_obj(msg: TrackNet_pb2.Railway) -> Railway:
        pass

    
    @staticmethod
    def railmap_obj_to_msg(railmap: RailMap) -> TrackNet_pb2.Railmap:
        msg = TrackNet_pb2.Railmap()
        for junction_name, junction in railmap.junctions.items():
            msg.junctions[junction_name] = MessageConverter.junction_obj_to_msg(junction)
        for track_name, track in railmap.tracks.items():
            msg.tracks[track_name] = MessageConverter.track_obj_to_msg(track)
        
        return msg

    
    @staticmethod
    def railmap_msg_to_obj(msg: TrackNet_pb2.Railmap) -> RailMap:
        pass


    @staticmethod
    def junction_obj_to_msg(junction: Junction) -> TrackNet_pb2.Junction:
        msg = TrackNet_pb2.junction()
        msg.id = junction.name
        msg.neighbors.extend(list(junction.neighbors.keys()))
        msg.parked_trains.extend(list(junction.parked_trains.keys()))

        return msg

    
    @staticmethod
    def junction_msg_to_obj(msg: TrackNet_pb2.Junction) -> Junction:
        pass
    

    @staticmethod
    def track_obj_to_msg(track: Track) -> TrackNet_pb2.Track:
        msg = TrackNet_pb2.Track()
        msg.junction_a = track.junctions[0]
        msg.junction_b = track.junctions[1]
        msg.id = track.name
        msg.trains.extend(list(track.trains.keys()))
        msg.condition = TrackNet_pb2.TrackCondition.BAD if (track.condition == TrackCondition.BAD) else TrackNet_pb2.TrackCondition.GOOD
        msg.speed = track.speed

        return msg

    
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


    

