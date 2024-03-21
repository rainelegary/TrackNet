#!/usr/bin/env python3

from classes.railway import Railway
from classes.track import Track
import TrackNet_pb2
from message_converter import MessageConverter

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

print("Serialization and deserialization of Track object")
track_obj = Track("A", "D", 40)
print("Initial track object: ")
track_obj.print_track()

print("\nConverted to protobuf message:")
track_pb = MessageConverter.track_obj_to_msg(track_obj)
print(track_pb)

print("Convert protobuf message back to object:")
track_obj2 = MessageConverter.track_msg_to_obj(track_pb)
track_obj2.print_track()







