from classes.railway import Railway
from classes.train import Train
from classes.route import Route
from classes.location import Location
from utils import *
from classes.enums import TrainState
from classes.railway import Railway
from converters.train_converter import TrainConverter

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [("A", "B", 10), ("B", "C", 20), ("C", "D", 30), ("A", "D", 40)],
}

railway = Railway(
    trains=None, junctions=initial_config["junctions"], tracks=initial_config["tracks"]
)


print("Serialization and deserialization of Train object")
train = Train(
    name="Train1",
    length=100,
    state=TrainState.SLOW,
    location=Location(),
    route=Route(railway.map.find_shortest_path("A", "C")),
    current_speed=0,
    next_junction=None,
    prev_junction=None,
)
train.route = Route(railway.map.find_shortest_path("A", "C"))
train.route.current_junction_index = 1

train.location.front_cart["track"] = railway.map.tracks["Track (A, B)"]
train.location.front_cart["position"] = 100
train.location.set_junction_front_cart(railway.map.junctions["B"])
train.location.back_cart["track"] = railway.map.tracks["Track (B, C)"]
train.location.back_cart["position"] = 90
train.location.set_junction_back_cart(railway.map.junctions["C"])

print("Printing the train object")
train.print_train()
print("**************************************************")

trainpb = TrainConverter.convert_train_obj_to_pb(train)
print("Printing the protobuf object")
print(trainpb)
print("**************************************************")

trainConverted = TrainConverter.convert_train_pb_to_obj(
    trainpb, railway.map.junctions, railway.map.tracks
)
print("Printing the train object")
trainConverted.print_train()
