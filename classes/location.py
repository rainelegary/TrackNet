import datetime
import TrackNet_pb2
import logging
from classes.junction import Junction
from classes.track import Track

LOGGER = logging.getLogger(__name__)


class Location:
    """Used to store a train's location on a track.
    :param heading_junction: the node it's heading towards
    :param prev_junction: the node it's coming from
    """

    def __init__(
        self,
        front_junction: Junction = None,
        back_junction: Junction = None,
        front_track: Track = None,
        back_track: Track = None,
        front_position: float = 0,
        back_position: float = 0,
    ):
        """
        For each cart, each field works as follows.

        When this cart is at a junction:
            track is None
            junction is the current junction
            position is 0

        When this cart is on a track:
            track is the current tracl
            junction is the one we're heading TO if front cart, and junction we're heading FROM if back cart.
            position is progress along track
        """
        self.front_cart = {
            "track": front_track,
            "junction": front_junction,
            "position": front_position,
        }
        self.back_cart = {
            "track": back_track,
            "junction": back_junction,
            "position": back_position,
        }

    def set_position(self, distance_moved, train_length):
        self.front_cart["position"] += distance_moved
        self.back_cart["position"] = max(0, self.front_cart["position"] - train_length)

    def check_back_cart_departed(self):
        if self.back_cart["track"] is not None and self.back_cart["position"] > 0:
            return True
        return False

    def check_front_cart_departed(self):
        if self.front_cart["track"] is not None and self.front_cart["position"] > 0:
            return True
        return False

    def set_location_message(self, msg: TrackNet_pb2.Location):
        if self.front_cart["track"] is not None:
            msg.front_track_id = self.front_cart["track"].name

        if self.front_cart["junction"] is not None:
            msg.front_junction_id = self.front_cart["junction"].name

        msg.front_position = self.front_cart["position"]

        if self.back_cart["track"] is not None:
            msg.back_track_id = self.back_cart["track"].name

        if self.back_cart["junction"] is not None:
            msg.back_junction_id = self.back_cart["junction"].name

        msg.back_position = self.back_cart["position"]

    def is_unparked(self):
        if self.back_cart["position"] > 0:
            return True
        return False

    def back_from_junction_to_track(self):
        self.back_cart["track"] = self.front_cart["track"]
        self.back_cart["junction"] = self.front_cart["junction"]

    def check_front_junction_reached(self):
        if (
            self.front_cart["track"] is not None
            and self.front_cart["position"] >= self.front_cart["track"].length
        ):
            return True
        return False

    def check_back_junction_reached(self):
        # Calculate if the back of the train has reached the end of its track
        if (
            self.back_cart["track"] is not None
            and self.back_cart["position"] >= self.back_cart["track"].length
        ):
            return True
        return False

    def check_back_has_left_junction(self):
        if self.front_cart["track"] is not None and self.back_cart["position"] == 0:
            self.back_cart["track"] = self.front_cart["track"]
            return True
        return False

    def set_track(self, track: Track):
        self.front_cart["track"] = track
        self.back_cart["track"] = track

    def set_junction_front_cart(self, junction):
        self.front_cart["junction"] = junction

    def set_junction_back_cart(self, junction):
        self.back_cart["junction"] = junction

    def set_next_track_front_cart(self, track):
        self.front_cart["track"] = track

    def set_next_track_back_cart(self, track):
        self.back_cart["track"] = track

    def set_to_park(self):
        """Parks the train at junction"""
        self.front_cart["position"] = 0
        self.back_cart["position"] = 0

    def __str__(self):
        front_cart_track = (
            self.front_cart["track"].name
            if self.front_cart["track"]
            else "None"
        )
        front_cart_junction = (
            self.front_cart["junction"].name
            if self.front_cart["junction"]
            else "None"
        )
        front_cart_position = self.front_cart["position"]
        back_cart_track = (
            self.back_cart["track"].name
            if self.back_cart["track"]
            else "None"
        )
        back_cart_junction = (
            self.back_cart["junction"].name
            if self.back_cart["junction"]
            else "None"
        )
        back_cart_position = self.back_cart["position"]
        frontString = (
            f"    Front: Track: {front_cart_track}, Junction: {front_cart_junction}, Position: {front_cart_position}"
        )
        backString = (
            f"    Back: Track: {back_cart_track}, Junction: {back_cart_junction}, Position: {back_cart_position}"
        )


        return frontString +" | "+ backString