#!/usr/bin/env python3

from classes.railway import Railway
from classes.track import Track
from classes.train import Train
from classes.junction import Junction
from classes.route import Route
from classes.location import Location
import TrackNet_pb2
from utils import *
from datetime import datetime
from converters.train_converter import TrainConverter
from converters.railmap_converter import RailmapConverter
from classes.enums import TrackCondition, TrainSpeed

print("Running tests")

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [("A", "B", 10), ("B", "C", 20), ("C", "D", 30), ("A", "D", 40)],
}

railway = Railway(
    trains=None, junctions=initial_config["junctions"], tracks=initial_config["tracks"]
)
trains = {
    "Train1": Train(name="Train1", length=100),
    "Train2": Train(name="Train2", length=200),
    "Train3": Train(name="Train3", length=300),
}
railway.map.junctions["A"].park_train(trains["Train1"])
railway.map.junctions["A"].park_train(trains["Train2"])
railway.map.junctions["C"].park_train(trains["Train3"])

railway.map.tracks["Track (A, B)"].add_train(trains["Train1"])
railway.map.tracks["Track (A, B)"].condition = TrackCondition.BAD
railway.map.tracks["Track (B, C)"].add_train(trains["Train2"])
railway.map.tracks["Track (B, C)"].condition = TrackCondition.BAD
railway.map.tracks["Track (C, D)"].speed = TrainSpeed.SLOW

print("Serialization and deserialization of Railmap object")
print("Printing the railmap object")
print(railway.map.print_map())

railmap_pb = RailmapConverter.convert_railmap_obj_to_pb(railway.map)
# print(railmap_pb)

railwayConverted = Railway(
    trains=None, junctions=initial_config["junctions"], tracks=initial_config["tracks"]
)
RailmapConverter.update_railmap_with_pb(
    railmap_pb, railmap=railwayConverted.map, trains=trains
)
print("Printing the deserialized railmap object")
print(railwayConverted.map.print_map())
