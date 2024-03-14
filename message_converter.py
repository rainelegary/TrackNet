
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
        msg.railway.CopyFrom(MessageConverter.railway_obj_to_msg(railway))
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
        msg.map.CopyFrom(MessageConverter.railmap_obj_to_msg(railway.map))
        for train_name, train in railway.trains.items():
            msg.trains[train_name] = MessageConverter.train_obj_to_msg(train)
        msg.train_counter = len(railway.trains)
        return msg

    
    @staticmethod
    def railway_msg_to_obj(msg: TrackNet_pb2.Railway) -> Railway:
        # junctions and tracks
        junctions = list(msg.map.junctions.keys())
        tracks = []
        for track_name in msg.map.tracks.keys():
            track_msg = msg.map.tracks[track_name]
            junction_a = track_msg.junction_a
            junction_b = track_msg.junction_b
            length = track_msg.length
            track = (junction_a, junction_b, length)
            tracks.append(track)

        railway = Railway(None, junctions, tracks)

        # trains
        for train_name in msg.trains.keys():
            train_msg = msg.trains[train_name]
            location_msg = train_msg.location

            length = train_msg.length
            filler_junction = railway.map.junctions.keys()[0]
            train_state = MessageConverter.train_state_proto_to_py(train_msg.state)

            train = railway.create_new_train(length, filler_junction)
            railway.update_train(train, train_state, location_msg)

        return railway
    

    
    @staticmethod
    def railmap_obj_to_msg(railmap: RailMap) -> TrackNet_pb2.Railmap:
        msg = TrackNet_pb2.Railmap()
        for junction_name, junction in railmap.junctions.items():
            msg.junctions[junction_name].CopyFrom(MessageConverter.junction_obj_to_msg(junction))
        for track_name, track in railmap.tracks.items():
            msg.tracks[track_name].CopyFrom(MessageConverter.track_obj_to_msg(track))
        return msg

    
    @staticmethod
    def railmap_msg_to_obj(msg: TrackNet_pb2.Railmap) -> RailMap:

        # similar to generating railmap from initial config

        # junctions

        # tracks

        pass


    @staticmethod
    def junction_obj_to_msg(junction: Junction) -> TrackNet_pb2.Junction:
        msg = TrackNet_pb2.Junction()
        msg.id = junction.name
        for junction_name, track_object in junction.neighbors.items():
            msg.neighbors[junction_name] = track_object.name
        
        msg.parked_trains.extend(list(junction.parked_trains.keys()))
        return msg

    
    @staticmethod
    def junction_msg_to_obj(msg: TrackNet_pb2.Junction, track_refs: "dict[str, Track]") -> Junction:
        pass
    

    @staticmethod
    def track_obj_to_msg(track: Track) -> TrackNet_pb2.Track:
        msg = TrackNet_pb2.Track()
        msg.junction_a = track.junctions[0]
        msg.junction_b = track.junctions[1]
        msg.length = track.length
        msg.id = track.name
        msg.trains.extend(list(track.trains.keys()))
        msg.condition = MessageConverter.track_condition_py_to_proto(track.condition)
        msg.speed = MessageConverter.train_speed_py_to_proto(track.speed)
        return msg

    
    @staticmethod
    def track_msg_to_obj(msg: TrackNet_pb2.Track, train_refs: "dict[str, Train]") -> Track:

        # needs train objects
        
        pass


    @staticmethod
    def track_condition_py_to_proto(track_condition: TrackCondition) -> TrackNet_pb2.TrackCondition:
        return {
            TrackCondition.BAD: TrackNet_pb2.TrackCondition.BAD,
            TrackCondition.GOOD: TrackNet_pb2.TrackCondition.GOOD,
        }[track_condition]

    
    @staticmethod
    def track_condition_proto_to_py(track_condition: TrackNet_pb2.TrackCondition) -> TrackCondition:
        return {
            TrackNet_pb2.TrackCondition.BAD: TrackCondition.BAD,
            TrackNet_pb2.TrackCondition.GOOD: TrackCondition.GOOD,
        }[track_condition]



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
    def train_msg_to_obj(msg: TrackNet_pb2.Train, junction_refs: "dict[str, Junction]", track_refs: "dict[str, Track]") -> Train:

        # needs junction objects for route
        # needs track objects for location and route

        # location

        # route

        pass


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
        return {
            TrackNet_pb2.Train.TrainState.RUNNING: TrainState.RUNNING,
            TrackNet_pb2.Train.TrainState.SLOW: TrainState.SLOW,
            TrackNet_pb2.Train.TrainState.STOPPED: TrainState.STOPPED,
            TrackNet_pb2.Train.TrainState.PARKED: TrainState.PARKED,
            TrackNet_pb2.Train.TrainState.PARKING: TrainState.PARKING,
            TrackNet_pb2.Train.TrainState.UNPARKING: TrainState.UNPARKING, 
        }[train_state]


    @staticmethod
    def train_speed_py_to_proto(train_speed: TrainSpeed) -> TrackNet_pb2.TrainSpeed:
        return {
            TrainSpeed.STOPPED: TrackNet_pb2.TrainSpeed.STOPPED,
            TrainSpeed.SLOW: TrackNet_pb2.TrainSpeed.SLOW,
            TrainSpeed.FAST: TrackNet_pb2.TrainSpeed.FAST,
        }[train_speed]

    
    @staticmethod
    def train_speed_proto_to_py(train_speed: TrackNet_pb2.TrainSpeed) -> TrainSpeed:
        return {
            TrackNet_pb2.TrainSpeed.STOPPED: TrainSpeed.STOPPED,
            TrackNet_pb2.TrainSpeed.SLOW: TrainSpeed.SLOW,
            TrackNet_pb2.TrainSpeed.FAST: TrainSpeed.FAST,
        }[train_speed]


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
    def location_msg_to_obj(msg: TrackNet_pb2.Location, junction_refs: "dict[str, Junction]", track_refs: "dict[str, Track]") -> Location:

        # need junction objects
        # need track objects

        pass


    @staticmethod
    def route_obj_to_msg(route: Route) -> TrackNet_pb2.Route:
        msg = TrackNet_pb2.Route()
        msg.junctions.extend(junction.name for junction in route.junctions)
        msg.current_junction_index = route.current_junction_index
        msg.destination = route.destination.name
        return msg

    
    @staticmethod
    def route_msg_to_obj(msg: TrackNet_pb2.Route, junction_refs: "dict[str, Junction]") -> Route:
        route = Route()
        for junction_name in msg.junctions:
            route.junctions.append(junction_refs[junction_name])
        route.current_junction_index = msg.current_junction_index
        route.destination = route.junctions[len(route.junctions) - 1]

        return route
    

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
        


    

