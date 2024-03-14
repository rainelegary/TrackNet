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


master_resp = TrackNet_pb2.InitConnection()
master_resp.sender = TrackNet_pb2.InitConnection.SERVER_MASTER
master_resp.railway_update.CopyFrom(MessageConverter.railway_obj_and_ts_to_railway_update_msg(self.railway,datetime.utcnow().isoformat()))
print(master_resp)