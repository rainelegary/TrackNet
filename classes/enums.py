
from enum import Enum

"""
These are all the enumerated types that can be used for status codes. 
They are the same mappings as the Protobuf enumerated types, and are
used within the python classes.
"""

class TrackCondition(Enum):
    BAD = 0
    GOOD = 1

class ServerResponse_Status(Enum): # this is the status the server sends to client as a command
    REDUCE_SPEED = 0
    INCREASE_SPEED = 1
    REROUTE = 2
    STOP = 3
    CLEAR = 4


class TrainState(Enum):
    RUNNING = 0
    SLOW = 1
    STOPPED = 2
    PARKED = 3
    PARKING = 4
    UNPARKING = 5

class TrackSpeed(Enum):
    STOPPED = 0
    SLOW = 5
    FAST = 10
