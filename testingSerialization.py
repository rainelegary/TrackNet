from message_converter import MessageConverter
import TrackNet_pb2
import logging
import socket
import signal 
import threading
from utils import *
from  classes.enums import TrainState, TrackCondition
from classes.railway import Railway
from classes.train import Train
import traceback
from datetime import datetime
import time
import threading
from utils import initial_config, proxy_details
from message_converter import MessageConverter

print("Creating a railway...")

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [
        ("A", "B", 10),
        ("B", "C", 20),
        ("C", "D", 30),
        ("A", "D", 40)
    ]
}

railway_system = Railway(
    trains=None,
    junctions=initial_config["junctions"],
    tracks=initial_config["tracks"]
)


master_resp = TrackNet_pb2.InitConnection()
master_resp.sender = TrackNet_pb2.InitConnection.SERVER_MASTER
master_resp.railway_update.CopyFrom(MessageConverter.railway_obj_and_ts_to_railway_update_msg(railway_system,datetime.utcnow().isoformat()))
print(master_resp)

print(railway_system.print_map())

(deserialObj, ts) = MessageConverter.railway_update_msg_to_railway_obj_and_ts(master_resp.railway_update)

print(deserialObj)


