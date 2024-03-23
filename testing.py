#!/usr/bin/env python3

from classes.railway import Railway
from classes.track import Track
from classes.train import Train
from classes.junction import Junction
from classes.route import Route
from classes.location import Location
import TrackNet_pb2
from message_converter import MessageConverter
from utils import *
from  classes.enums import TrainState, TrackCondition
from classes.railway import Railway
from datetime import datetime
from message_converter import MessageConverter
from converter import Converter

print("Running tests")

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [
        ("A", "B", 10),
        ("B", "C", 20),
        ("C", "D", 30),
        ("A", "D", 40)
    ]
}

railway = Railway(
            trains=None,
            junctions=initial_config["junctions"],
            tracks=initial_config["tracks"]
        )

print("Serialization and deserialization of Track object")

train = Train(None, 10, railway.map.junctions["A"], railway.map.junctions["B"], TrainState.PARKED, None, 100, railway.map.junctions["B"], railway.map.junctions["A"])
train.route = Route(railway.map.find_shortest_path("A", "C"))
train.route.current_junction_index = 1

# train.location.set_next_track_front_cart(railway.map.tracks["Track (A, B)"])
# train.location.front_cart["position"] = 100
# train.location.set_junction_front_cart(railway.map.junctions["B"])

# train.location.set_next_track_back_cart(railway.map.tracks["Track (B, C)"])
# train.location.back_cart["position"] = 90
# train.location.set_junction_back_cart(railway.map.junctions["C"])

print("Printing the train object")
train.print_train()
print("**************************************************")

trainpb = Converter.convert_train_obj_to_pb(train)
print("Printing the protobuf object")
print(trainpb)
print("**************************************************")

trainConverted = Converter.convert_train_pb_to_obj(trainpb, railway.map.junctions)
print("Printing the train object")
trainConverted.print_train()







# create_railway_update_message()
print()




