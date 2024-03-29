import TrackNet_pb2
from classes.railmap import Railmap
from classes.junction import Junction
from classes.train import Train
from converters.enum_converter import EnumConverter


class RailmapConverter:
    @staticmethod
    def convert_railmap_obj_to_pb(railmap: Railmap) -> TrackNet_pb2.Railmap:
        railmap_pb = TrackNet_pb2.Railmap()
        for junction in railmap.junctions.values():
            junction_pb = TrackNet_pb2.Junction()
            junction_pb.id = junction.name
            for parked_train_id in junction.parked_trains.keys():
                junction_pb.parked_trains_ids.append(parked_train_id)

            railmap_pb.junctions.append(junction_pb)

        for track in railmap.tracks.values():
            track_pb = TrackNet_pb2.Track()
            track_pb.id = track.name
            track_pb.condition = EnumConverter.track_condition_enum_to_pb(
                track.condition
            )
            track_pb.speed = EnumConverter.train_speed_enum_to_pb(track.speed)
            for train_id in track.trains.keys():
                track_pb.train_ids.append(train_id)

            railmap_pb.tracks.append(track_pb)

        return railmap_pb

    # This function is named update because it updates the railmap object with the protobuf object
    # it doesnt create a new object, instead it updates the existing object
    @staticmethod
    def update_railmap_with_pb(
        railmap_pb: TrackNet_pb2.Railmap, railmap: Railmap, trains: dict[str, Train]
    ):
        for junction_pb in railmap_pb.junctions:
            junction_name = junction_pb.id
            for parked_train_id in junction_pb.parked_trains_ids:
                train_obj = trains[parked_train_id]
                railmap.junctions[junction_name].park_train(train_obj)

        for track_pb in railmap_pb.tracks:
            track_name = track_pb.id
            railmap.tracks[track_name].condition = (
                EnumConverter.track_condition_pb_to_enum(track_pb.condition)
            )
            railmap.tracks[track_name].speed = EnumConverter.train_speed_pb_to_enum(
                track_pb.speed
            )
            for train_id in track_pb.train_ids:
                train_obj = trains[train_id]
                railmap.tracks[track_name].add_train(train_obj)
