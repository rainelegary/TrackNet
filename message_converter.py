
import TrackNet_pb2
from classes.railway import Railway
from classes.railmap import RailMap
from classes.train import Train
from classes.route import Route
from classes.track import Track
from classes.junction import Junction
from classes.location import Location
from classes.enums import TrackCondition, TrainSpeed, TrainState, ServerResponse_Status


class MessageConverter:
    
    @staticmethod
    def railway_obj_and_ts_to_railway_update_msg(railway: Railway, timestamp: str) -> TrackNet_pb2.RailwayUpdate:
        msg = TrackNet_pb2.RailwayUpdate()
        msg.railway = MessageConverter.railway_obj_to_msg(railway)
        msg.timestamp = timestamp
        return msg

    
    @staticmethod
    def railway_update_msg_to_railway_obj_and_ts(msg: TrackNet_pb2.RailwayUpdate) -> "tuple[Railway, str]":
        railway = MessageConverter.railway_msg_to_obj(msg.railway)
        timestamp = msg.timestamp
        return (railway, timestamp)


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
        railway = Railway()
        railway.map = MessageConverter.railmap_msg_to_obj(msg.map)
        railway.trains

    
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
        msg.condition = MessageConverter.track_condition_py_to_proto(track.condition)
        msg.speed = MessageConverter.train_speed_py_to_proto(track.speed)
        return msg

    
    @staticmethod
    def track_msg_to_obj(msg: TrackNet_pb2.Track) -> Track:
        pass


    @staticmethod
    def track_condition_py_to_proto(track_condition: TrackCondition) -> TrackNet_pb2.TrackCondition:
        return {
            TrackCondition.BAD: TrackNet_pb2.TrackCondition.BAD,
            TrackCondition.GOOD: TrackNet_pb2.TrackCondition.GOOD
        }[track_condition]

    
    @staticmethod
    def track_condition_proto_to_py(track_condition: TrackNet_pb2.TrackCondition) -> TrackCondition:
        pass


    @staticmethod
    def train_obj_to_msg(train: Train) -> TrackNet_pb2.Train:
        msg = TrackNet_pb2.Train()
        msg.id = train.name
        msg.length = train.length
        msg.state = MessageConverter.train_state_py_to_proto(train.state)
        msg.location = MessageConverter.location_obj_to_msg(train.location)
        msg.route = MessageConverter.route_obj_to_msg(train.route)
        return msg
    
    @staticmethod
    def train_msg_to_obj(msg: TrackNet_pb2.Train) -> Train:
        pass


    # Railway
        # Railmap
            # Junctions
                # Neighbours
                # 
        # Train
            # Route
                # Junction ID


    @staticmethod
    def train_state_py_to_proto(train_state: TrainState) -> TrackNet_pb2.Train.TrainState:
        return {
            TrainState.RUNNING: TrackNet_pb2.Train.TrainState.RUNNING,
            TrainState.SLOW: TrackNet_pb2.Train.TrainState.SLOW,
            TrainState.STOPPED: TrackNet_pb2.Train.TrainState.STOPPED,
            TrainState.PARKED: TrackNet_pb2.Train.TrainState.PARKED,
            TrainState.PARKING: TrackNet_pb2.Train.TrainState.PARKING,
            TrainState.UNPARKING: TrackNet_pb2.Train.TrainState.UNPARKING,
        }[train_state]

    
    @staticmethod
    def train_state_proto_to_py(train_state: TrackNet_pb2.Train.TrainState) -> TrainState:
        pass


    @staticmethod
    def train_speed_py_to_proto(train_speed: TrainSpeed) -> TrackNet_pb2.TrainSpeed:
        return {
            TrainSpeed.STOPPED: TrackNet_pb2.TrainSpeed.STOPPED,
            TrainSpeed.SLOW: TrackNet_pb2.TrainSpeed.SLOW,
            TrainSpeed.FAST: TrackNet_pb2.TrainSpeed.FAST,
        }[train_speed]

    
    @staticmethod
    def train_speed_proto_to_py(train_speed: TrackNet_pb2.TrainSpeed) -> TrainSpeed:
        pass


    @staticmethod
    def location_obj_to_msg(location: Location) -> TrackNet_pb2.Location:
        msg = TrackNet_pb2.Location()
        msg.front_junction_id = location.front_cart["junction"].name
        msg.front_track_id = location.front_cart["track"].name
        msg.front_position = location.front_cart["position"]
        msg.back_junction_id = location.back_cart["junction"].name
        msg.back_track_id = location.back_cart["track"].name
        msg.back_position = location.back_cart["position"]
        return msg

    
    @staticmethod
    def location_msg_to_obj(msg: TrackNet_pb2.Location) -> Location:
        pass


    @staticmethod
    def route_obj_to_msg(route: Route) -> TrackNet_pb2.Route:
        msg = TrackNet_pb2.Route()
        msg.junctions.extend(junction.name for junction in route.junctions)
        msg.current_junction_index = route.current_junction_index
        msg.destination = route.destination.name
        return msg

    
    @staticmethod
    def route_msg_to_obj(msg: TrackNet_pb2.Route) -> Route:
        
        pass
        


    

