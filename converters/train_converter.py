import TrackNet_pb2
from classes.train import Train
from classes.route import Route
from classes.location import Location
from classes.enums import TrainState


class TrainConverter:

    # SECTION: Serialization
    @staticmethod
    def convert_train_state_obj_to_pb(
        train_state: TrainState,
    ) -> TrackNet_pb2.Train.TrainState:
        return {
            TrainState.RUNNING: TrackNet_pb2.Train.TrainState.RUNNING,
            TrainState.SLOW: TrackNet_pb2.Train.TrainState.SLOW,
            TrainState.STOPPED: TrackNet_pb2.Train.TrainState.STOPPED,
            TrainState.PARKED: TrackNet_pb2.Train.TrainState.PARKED,
            TrainState.PARKING: TrackNet_pb2.Train.TrainState.PARKING,
            TrainState.UNPARKING: TrackNet_pb2.Train.TrainState.UNPARKING,
        }[train_state]

    @staticmethod
    def convert_location_obj_to_pb(location_obj: Location) -> TrackNet_pb2.Location:
        location_pb = TrackNet_pb2.Location()
        if location_obj.front_cart["junction"]:
            location_pb.front_junction_id = location_obj.front_cart["junction"].name

        if location_obj.back_cart["junction"]:
            location_pb.back_junction_id = location_obj.back_cart["junction"].name

        if location_obj.front_cart["track"]:
            location_pb.front_track_id = location_obj.front_cart["track"].name

        if location_obj.back_cart["track"]:
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
            train_pb.state = TrainConverter.convert_train_state_obj_to_pb(
                train_obj.state
            )

        if train_obj.current_speed:
            train_pb.speed = train_obj.current_speed

        if train_obj.next_junction:
            train_pb.next_junction_id = train_obj.next_junction.name

        if train_obj.prev_junction:
            train_pb.prev_junction_id = train_obj.prev_junction.name

        # Serialize the train's Location
        if train_obj.location:
            location_pb = TrainConverter.convert_location_obj_to_pb(train_obj.location)
            train_pb.location.CopyFrom(location_pb)

            # Serialize the train's Route
        if train_obj.route:
            route_pb = TrainConverter.convert_route_obj_to_pb(train_obj.route)
            train_pb.route.CopyFrom(route_pb)

        return train_pb

    # SECTION: Deserialization
    @staticmethod
    def convert_train_pb_to_obj(
        train_pb: TrackNet_pb2.Train, junctions, tracks
    ) -> Train:
        train_name = train_pb.id if train_pb.id else None
        train_length = train_pb.length if train_pb.length else 0
        train_state = (
            TrainConverter.convert_train_state_pb_to_obj(train_pb.state)
            if train_pb.state
            else None
        )
        train_speed = train_pb.speed if train_pb.speed else 0
        next_junction = (
            junctions[train_pb.next_junction_id] if train_pb.next_junction_id else None
        )
        prev_junction = (
            junctions[train_pb.prev_junction_id] if train_pb.prev_junction_id else None
        )
        route = TrainConverter.convert_route_pb_to_obj(train_pb.route, junctions)
        location = TrainConverter.convert_location_pb_to_obj(
            train_pb.location, junctions, tracks
        )

        train_obj = Train(
            name=train_name,
            length=train_length,
            state=train_state,
            current_speed=train_speed,
            location=location,
            route=route,
            next_junction=next_junction,
            prev_junction=prev_junction,
        )

        return train_obj

    @staticmethod
    def convert_route_pb_to_obj(
        route_pb: TrackNet_pb2.Route, junctions
    ) -> Route | None:

        route = None
        if route_pb.junctions_ids:
            route_junctions = []
            route_current_junction_index = (
                route_pb.current_junction_index
                if route_pb.current_junction_index
                else 0
            )
            for junction_id in route_pb.junctions_ids:
                route_junctions.append(junctions[junction_id])

            route = Route(
                junctions=route_junctions,
                current_junction_index=route_current_junction_index,
            )
        return route

    @staticmethod
    def convert_location_pb_to_obj(
        location_pb: TrackNet_pb2.Location, junctions, tracks
    ) -> Location:
        location_front_junction = (
            junctions[location_pb.front_junction_id]
            if location_pb.front_junction_id
            else None
        )
        location_back_junction = (
            junctions[location_pb.back_junction_id]
            if location_pb.back_junction_id
            else None
        )

        location_front_track = (
            tracks[location_pb.front_track_id] if location_pb.front_track_id else None
        )
        location_back_track = (
            tracks[location_pb.back_track_id] if location_pb.back_track_id else None
        )

        location_front_position = (
            location_pb.front_position if location_pb.front_position else 0
        )
        location_back_position = (
            location_pb.back_position if location_pb.back_position else 0
        )

        location_obj = Location(
            front_junction=location_front_junction,
            back_junction=location_back_junction,
            front_track=location_front_track,
            back_track=location_back_track,
            front_position=location_front_position,
            back_position=location_back_position,
        )
        return location_obj

    @staticmethod
    def convert_train_state_pb_to_obj(
        train_state: TrackNet_pb2.Train.TrainState,
    ) -> TrainState:
        return {
            TrackNet_pb2.Train.TrainState.RUNNING: TrainState.RUNNING,
            TrackNet_pb2.Train.TrainState.SLOW: TrainState.SLOW,
            TrackNet_pb2.Train.TrainState.STOPPED: TrainState.STOPPED,
            TrackNet_pb2.Train.TrainState.PARKED: TrainState.PARKED,
            TrackNet_pb2.Train.TrainState.PARKING: TrainState.PARKING,
            TrackNet_pb2.Train.TrainState.UNPARKING: TrainState.UNPARKING,
        }[train_state]
