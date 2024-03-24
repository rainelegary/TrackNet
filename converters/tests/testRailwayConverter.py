from classes.railway import Railway
from classes.train import Train
from classes.route import Route
from classes.location import Location
from utils import *
from classes.enums import TrainState
from classes.railway import Railway
from converters.train_converter import TrainConverter
from converters.railway_converter import RailwayConverter

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [("A", "B", 10), ("B", "C", 20), ("C", "D", 30), ("A", "D", 40)],
}

railway = Railway(
    trains=None, junctions=initial_config["junctions"], tracks=initial_config["tracks"]
)
railway.create_new_train(10, "A")
railway.create_new_train(20, "B")
# railway.map.tracks["Track (A, B)"].add_train(railway.trains["Train0"])

railway_pb = RailwayConverter.convert_railway_obj_to_pb(railway)
# print(railway_pb)

railway2 = Railway(
    trains=None, junctions=initial_config["junctions"], tracks=initial_config["tracks"]
)
RailwayConverter.update_railway_with_pb(railway_pb, railway2)
railway2.map.print_map()
for train in railway2.trains.values():
    train.print_train()
