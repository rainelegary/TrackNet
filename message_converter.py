
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
        (MessageConverter.railway_obj_to_msg(railway,msg))
        
        return msg

    
    @staticmethod
    def railway_update_msg_to_railway_obj_and_ts(msg: TrackNet_pb2.RailwayUpdate) -> "tuple[Railway, str]":
        railway = MessageConverter.railway_msg_to_obj(msg.railway)
        timestamp = msg.timestamp
        return (railway, timestamp)

    @staticmethod
    def railway_obj_to_msg(railway: Railway, RailWayMsg:TrackNet_pb2.RailwayUpdate) -> TrackNet_pb2.Railway:
        msg = TrackNet_pb2.Railway()
        (MessageConverter.railmap_obj_to_msg(railway.map,RailWayMsg.railway.map))
        for train_name, train in railway.trains.items():
            MessageConverter.train_obj_to_msg(train,RailWayMsg.railway.trains[train_name])
        RailWayMsg.railway.train_counter = len(railway.trains)
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
    def railmap_obj_to_msg(railmap: RailMap, RailWayMsg_railway_map:TrackNet_pb2.Railmap) -> TrackNet_pb2.Railmap:
        msg = TrackNet_pb2.Railmap()
        for junction_name, junction in railmap.junctions.items():
            #jun = MessageConverter.junction_obj_to_msg(junction,)
            MessageConverter.junction_obj_to_msg(junction,RailWayMsg_railway_map.junctions[junction_name])

            # RailWayMsg_railway_map.junctions[junction_name].id = jun.id
            # for k, n in jun.neighbors:
            #     RailWayMsg_railway_map.junctions[junction_name].neighbors[k] = n
            # RailWayMsg_railway_map.junctions[junction_name].parked_trains.CopyFrom(jun.parked_trains)
        for track_name, track in railmap.tracks.items():
            MessageConverter.track_obj_to_msg(track,RailWayMsg_railway_map.tracks[track_name])
        return msg
    """
    @staticmethod
    def railmap_obj_to_msg(railmap: RailMap) -> TrackNet_pb2.Railmap:
        msg = TrackNet_pb2.Railmap()
        
        # For junctions: Assuming junctions is a map field where values are message types
        for junction_name, junction in railmap.junctions.items():
            # Create or get the message to modify
            junction_msg = msg.junctions[junction_name]
            # Since direct assignment isn't supported, use MergeFrom to copy the content
            # This assumes you have a method that returns a new message object for a junction
            junction_msg.MergeFrom(MessageConverter.junction_obj_to_msg(junction))
        
        # For tracks: Assuming tracks is a map field where values are message types
        for track_name, track in railmap.tracks.items():
            # Similar approach as with junctions
            track_msg = msg.tracks[track_name]
            # Use MergeFrom to copy the content
            track_msg.MergeFrom(MessageConverter.track_obj_to_msg(track))
            
        return msg
    """
    @staticmethod
    def railmap_obj_to_msg2(railmap: RailMap) -> TrackNet_pb2.Railmap:
        msg = TrackNet_pb2.Railmap()
        for junction_name, junction in railmap.junctions.items():
            msg.junctions[junction_name].CopyFrom(MessageConverter.junction_obj_to_msg(junction))
        for track_name, track in railmap.tracks.items():
            msg.tracks[track_name].CopyFrom(MessageConverter.track_obj_to_msg(track))
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
    def junction_obj_to_msg(junction: Junction, junctionProto:TrackNet_pb2.Junction ) -> TrackNet_pb2.Junction:
        msg = TrackNet_pb2.Junction()
        junctionProto.id = junction.name
        for junction_name, track_object in junction.neighbors.items():
            print()
            print("!!!!!!!!!!!!!!!!",track_object.name, ":",junction_name)
            print(type(junction_name))
            print(type(track_object.name))
            print()
            #junctionProto.neighbors[junction_name] = (track_object.name)
        
        for (parkedTrain,_) in junction.parked_trains.items():
            #junctionProto.parked_trains.append(parkedTrain)
            pass

        return msg

    
    @staticmethod
    def junction_msg_to_obj(msg: TrackNet_pb2.Junction, track_refs: "dict[str, Track]") -> Junction:
        pass
    

    @staticmethod
    def track_obj_to_msg(track: Track, trackProto:TrackNet_pb2.Track) -> TrackNet_pb2.Track:
        
        msg = TrackNet_pb2.Track()
        trackProto.junction_a = track.junctions[0].name
        trackProto.junction_b = track.junctions[1].name
        trackProto.id = track.name
        for (runningTrains, _) in track.trains.items():
            #trackProto.trains.append(runningTrains)
            pass

        trackProto.condition = MessageConverter.track_condition_py_to_proto(track.condition)
        trackProto.speed = MessageConverter.train_speed_py_to_proto(track.speed)
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
        return {
            TrackNet_pb2.TrackCondition.BAD: TrackCondition.BAD,
            TrackNet_pb2.TrackCondition.GOOD: TrackCondition.GOOD,
        }[track_condition]


    @staticmethod
    def train_obj_to_msg(train: Train , trainProto:TrackNet_pb2.Train ) -> TrackNet_pb2.Train:
        msg = TrackNet_pb2.Train()
        trainProto.id = train.name
        trainProto.length = train.length
        trainProto.state = MessageConverter.train_state_py_to_proto(train.state)
        MessageConverter.location_obj_to_msg(train.location,trainProto.location)
        MessageConverter.route_obj_to_msg(train.route,trainProto.route)
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
    def location_obj_to_msg(location: Location, locationProto:TrackNet_pb2.Location) -> TrackNet_pb2.Location:
        msg = TrackNet_pb2.Location()
        locationProto.front_junction_id = location.front_cart["junction"].name
        locationProto.front_track_id = location.front_cart["track"].name
        locationProto.front_position = location.front_cart["position"]
        locationProto.back_junction_id = location.back_cart["junction"].name
        locationProto.back_track_id = location.back_cart["track"].name
        locationProto.back_position = location.back_cart["position"]
        return msg

    
    @staticmethod
    def location_msg_to_obj(msg: TrackNet_pb2.Location, junction_refs: "dict[str, Junction]", track_refs: "dict[str, Track]") -> Location:

        # need junction objects
        # need track objects

        pass


    @staticmethod
    def route_obj_to_msg(route: Route, RouteProto:TrackNet_pb2.Route) -> TrackNet_pb2.Route:
        msg = TrackNet_pb2.Route()
        #RouteProto.junctions.extend(junction.name for junction in route.junctions)
        RouteProto.current_junction_index = route.current_junction_index
        RouteProto.destination = route.destination.name
        return msg

    
    @staticmethod
    def route_msg_to_obj(msg: TrackNet_pb2.Route, junction_refs: "dict[str, Junction]") -> Route:
        route = Route()
        for junction_name in msg.junctions:
            #route.junctions.append(junction_refs[junction_name])
            pass
        route.current_junction_index = msg.current_junction_index
        route.destination = route.junctions[len(route.junctions) - 1]

        return route
        


    

