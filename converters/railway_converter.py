import TrackNet_pb2
from classes.railway import Railway
from converters.train_converter import TrainConverter
from converters.railmap_converter import RailmapConverter


class RailwayConverter:
    @staticmethod
    def convert_railway_obj_to_pb(railway: Railway) -> TrackNet_pb2.Railway:
        railway_pb = TrackNet_pb2.Railway()

        railmap_pb = RailmapConverter.convert_railmap_obj_to_pb(railway.map)
        railway_pb.map.CopyFrom(railmap_pb)

        for train in railway.trains.values():
            train_pb = TrainConverter.convert_train_obj_to_pb(train)
            railway_pb.trains.append(train_pb)

        railway_pb.train_counter = railway.train_counter

        return railway_pb

    @staticmethod
    def update_railway_with_pb(railway_pb: TrackNet_pb2.Railway, railway: Railway):
        railway.train_counter = railway_pb.train_counter
        trains = {}
        for train in railway_pb.trains:
            train_obj = TrainConverter.convert_train_pb_to_obj(
                train, railway.map.junctions, railway.map.tracks
            )
            trains[train_obj.name] = train_obj

        RailmapConverter.update_railmap_with_pb(railway_pb.map, railway.map, trains)
        railway.trains = trains
