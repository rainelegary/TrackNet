
import TrackNet_pb2
from classes.railway import Railway
from classes.railmap import RailMap
from classes.train import Train
from classes.route import Route
from classes.track import Track
from classes.junction import Junction
from classes.location import Location
from classes.enums import TrackCondition, TrainSpeed, TrainState
from message_converter import MessageConverter


class Converter:
    @staticmethod
    def convert_railway_obj_to_pb(railway_obj: Railway) -> TrackNet_pb2.Railway:
        railway_pb = TrackNet_pb2.Railway()

        # Serialize Train


        # Serialize Junctions
        for junction_name, junction_obj in railway_obj.map.junctions.items():
            print(junction_name, junction_obj)
            junction_pb = railway_pb.railway.map.junctions[junction_name] # Access the junction by key to modify it directly.
            junction_pb.id = junction_name
            for trainID in junction_obj.parked_trains.keys():
                junction_pb.parked_trains_ids.append(trainID)

        return railway_pb
    
    @staticmethod
    def convert_location_obj_to_pb(location_obj: Location) -> TrackNet_pb2.Location:
        location_pb = TrackNet_pb2.Location()
        if(location_obj.front_cart["junction"]):
            location_pb.front_junction_id = location_obj.front_cart["junction"].name
        
        if(location_obj.back_cart["junction"]):
            location_pb.back_junction_id = location_obj.back_cart["junction"].name

        if(location_obj.front_cart["track"]):
            location_pb.front_track_id = location_obj.front_cart["track"].name
        
        if(location_obj.back_cart["track"]):
            location_pb.back_track_id = location_obj.back_cart["track"].name

        location_pb.front_position = location_obj.front_cart["position"]
        location_pb.back_position = location_obj.back_cart["position"]

        return location_pb

    @staticmethod
    def convert_route_obj_to_pb(route_obj: Route) -> TrackNet_pb2.Route:
        route_pb = TrackNet_pb2.Route()
        for junction in route_obj.junctions:
            route_pb.junctions_ids.append(junction.name)
        route_pb.current_junction_index = route_obj.current_junction_index
        return route_pb

    @staticmethod
    def convert_train_obj_to_pb(train_obj: Train) -> TrackNet_pb2.Train:
        train_pb = TrackNet_pb2.Train()
        if train_obj.name:
            train_pb.id = train_obj.name 
        
        if train_obj.length:
            train_pb.length = train_obj.length
        
        if train_obj.state:
            train_pb.state = MessageConverter.train_state_py_to_proto(train_obj.state)

        if train_obj.current_speed:
            train_pb.speed = train_obj.current_speed 
        
        if train_obj.next_junction:
            train_pb.next_junction_id = train_obj.next_junction.name

        if train_obj.prev_junction:
            train_pb.prev_junction_id = train_obj.prev_junction.name

        # Serialize the train's Location
        if train_obj.location:
            location_pb = Converter.convert_location_obj_to_pb(train_obj.location)
            train_pb.location.CopyFrom(location_pb)

            # Serialize the train's Route
        if train_obj.route:
            route_pb = Converter.convert_route_obj_to_pb(train_obj.route)
            train_pb.route.CopyFrom(route_pb)
        
        return train_pb
    

    @staticmethod
    def convert_train_pb_to_obj(train_pb: TrackNet_pb2.Train, junctions) -> Train:
        train_name = train_pb.id if train_pb.id else None
        train_length = train_pb.length if train_pb.length else 0
        train_state = MessageConverter.train_state_proto_to_py(train_pb.state) if train_pb.state else None
        train_speed = train_pb.speed if train_pb.speed else 0
        junction_front = junctions[train_pb.next_junction_id] if train_pb.next_junction_id else None
        junction_back = junctions[train_pb.prev_junction_id] if train_pb.prev_junction_id else None
        next_junction = junctions[train_pb.next_junction_id] if train_pb.next_junction_id else None
        prev_junction = junctions[train_pb.prev_junction_id] if train_pb.prev_junction_id else None

        route = None
        if(train_pb.route.junctions_ids):
            route_junctions = []
            route_current_junction_index = train_pb.route.current_junction_index if train_pb.route.current_junction_index else 0
            for junction_id in train_pb.route.junctions_ids:
                route_junctions.append(junctions[junction_id])
            
            route = Route(junctions=route_junctions, current_junction_index=route_current_junction_index)


        train_obj = Train(
            name=train_name,
            length=train_length,
            state=train_state,
            current_speed=train_speed,
            junction_front=junction_front,
            junction_back=junction_back,
            next_junction=next_junction,
            prev_junction=prev_junction,
            route=route
        )
        return train_obj


    ##########

    # def convert_railway_pb_to_obj(railway_pb: TrackNet_pb2.Railway):
    #     railway = Railway(
    #             trains=None,
    #             junctions=initial_config["junctions"],
    #             tracks=initial_config["tracks"]
    #         )
        
    #     # Add trains

    #         # Add location
    #         # Add Route: 
    #             # Add junctions to route & add current_junction_index
    #     # Track: Add trains, update condition and speed

    #     # Junction: Add parked trains to junction.
    #     for junction in railway_pb.railway.map.junctions:
    #         railway.map.junctions[junction.id] = junction
    #         for trainID in junction.parked_trains_ids:
    #             train = Train(trainID, 10)
    #             railway.map.junctions[junction.id].park_train(train)
    #     return railway






    
    

    

