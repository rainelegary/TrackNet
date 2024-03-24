import TrackNet_pb2
from classes.enums import TrackCondition, TrainSpeed, TrainState


class EnumConverter:
    @staticmethod
    def train_state_enum_to_pb(
        train_state: TrainState,
    ) -> TrackNet_pb2.Train.TrainState:
        return {
            TrainState.RUNNING: TrackNet_pb2.Train.TrainState.RUNNING,
            TrainState.SLOW: TrackNet_pb2.Train.TrainState.SLOW,
            TrainState.STOPPED: TrackNet_pb2.Train.TrainState.STOPPED,
            TrainState.PARKED: TrackNet_pb2.Train.TrainState.PARKED,
            TrainState.PARKING: TrackNet_pb2.Train.TrainState.PARKING,
            TrainState.UNPARKING: TrackNet_pb2.Train.TrainState.UNPARKING,
        }[train_state]

    @staticmethod
    def train_state_pb_to_enum(
        train_state: TrackNet_pb2.Train.TrainState,
    ) -> TrainState:
        return {
            TrackNet_pb2.Train.TrainState.RUNNING: TrainState.RUNNING,
            TrackNet_pb2.Train.TrainState.SLOW: TrainState.SLOW,
            TrackNet_pb2.Train.TrainState.STOPPED: TrainState.STOPPED,
            TrackNet_pb2.Train.TrainState.PARKED: TrainState.PARKED,
            TrackNet_pb2.Train.TrainState.PARKING: TrainState.PARKING,
            TrackNet_pb2.Train.TrainState.UNPARKING: TrainState.UNPARKING,
        }[train_state]

    @staticmethod
    def track_condition_enum_to_pb(
        track_condition: TrackCondition,
    ) -> TrackNet_pb2.TrackCondition:
        return {
            TrackCondition.BAD: TrackNet_pb2.TrackCondition.BAD,
            TrackCondition.GOOD: TrackNet_pb2.TrackCondition.GOOD,
        }[track_condition]

    @staticmethod
    def track_condition_pb_to_enum(
        track_condition: TrackNet_pb2.TrackCondition,
    ) -> TrackCondition:
        return {
            TrackNet_pb2.TrackCondition.BAD: TrackCondition.BAD,
            TrackNet_pb2.TrackCondition.GOOD: TrackCondition.GOOD,
        }[track_condition]

    @staticmethod
    def train_speed_enum_to_pb(train_speed: TrainSpeed) -> TrackNet_pb2.TrainSpeed:
        return {
            TrainSpeed.STOPPED: TrackNet_pb2.TrainSpeed.STOPPED,
            TrainSpeed.SLOW: TrackNet_pb2.TrainSpeed.SLOW,
            TrainSpeed.FAST: TrackNet_pb2.TrainSpeed.FAST,
        }[train_speed]

    @staticmethod
    def train_speed_pb_to_enum(train_speed: TrackNet_pb2.TrainSpeed) -> TrainSpeed:
        return {
            TrackNet_pb2.TrainSpeed.STOPPED: TrainSpeed.STOPPED,
            TrackNet_pb2.TrainSpeed.SLOW: TrainSpeed.SLOW,
            TrackNet_pb2.TrainSpeed.FAST: TrainSpeed.FAST,
        }[train_speed]
