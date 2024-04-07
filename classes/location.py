import TrackNet_pb2
import logging
from classes.junction import Junction
from classes.track import Track

LOGGER = logging.getLogger(__name__)


class Location:
    """Used to store a train's location on a track, including its front and 
    back cart positions relative to junctions and tracks.

    The server uses methods from this class to update a trains position within 
    the dispatch area based on the data it receives from the client of the train.

    Attributes
    ----------
    front_cart: A dictionary containing the front cart's track, junction, and position. 
        - When the cart position is ``0``, 
        the junction is the current junction, and
        the track is last track the cart was on.

        - When the cart position is greater than ``0``, 
        the track is the current track, and
        the junction is last junction the cart was at.

    back_cart: A dictionary similar to ``front_cart``, but for the back cart. When moving, the junction is the one the cart is heading from.
    """

    def __init__(self,front_junction: Junction=None, back_junction: Junction=None,
        front_track: Track=None, back_track: Track=None, front_position: float=0, back_position: float=0):
        """Initializes a Location instance.

        :param front_junction: The junction towards which the front cart is heading. Defaults to None.
        :param back_junction: The junction from which the back cart is coming. Defaults to None.
        :param front_track: The current track of the front cart. Defaults to None.
        :param back_track: The current track of the back cart. Defaults to None.
        :param front_position: The front cart's position along the track. Defaults to 0.
        :param back_position: The back cart's position along the track. Defaults to 0.
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

    def set_location_message(self, msg: TrackNet_pb2.Location):
        """Sets the location message for network communication based on the current location of the train.

        Used by Client.set_client_state_msg. The server never uses this function.

        :param msg: The TrackNet_pb2.Location message to be updated with the train's location.
        """
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

    def set_position(self, distance_moved: int, train_length: int):
        """Updates the position of the train's front and back carts based on the distance moved.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :param distance_moved: The distance the train has moved.
        :param train_length: The length of the train.
        """
        self.front_cart["position"] += distance_moved
        self.back_cart["position"] = max(0, self.front_cart["position"] - train_length)

    def check_back_cart_departed(self) -> bool:
        """Checks if the back cart has departed from a junction or a starting point.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :return: True if the back cart has departed; False otherwise.
        """
        if self.back_cart["track"] is not None and self.back_cart["position"] > 0:
            return True
        return False

    def check_front_cart_departed(self) -> bool:
        """Checks if the front cart has departed from a junction or a starting point.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :return: True if the front cart has departed; False otherwise.
        """
        if self.front_cart["track"] is not None and self.front_cart["position"] > 0:
            return True
        return False

    def check_front_junction_reached(self) -> bool:
        """Checks if the front cart has reached the next junction.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :return: True if the front junction is reached; False otherwise.
        """
        if (
            self.front_cart["track"] is not None
            and self.front_cart["position"] >= self.front_cart["track"].length
        ):
            return True
        return False

    def check_back_junction_reached(self) -> bool:
        """Checks if the back cart has reached the junction.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :return: True if the back junction is reached; False otherwise.
        """
        if (
            self.back_cart["track"] is not None
            and self.back_cart["position"] >= self.back_cart["track"].length
        ):
            return True
        return False

    def set_junction_front_cart(self, junction: Junction):
        """Sets the junction for the front cart.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :param junction: The junction to be set for the front cart.
        """
        self.front_cart["junction"] = junction

    def set_junction_back_cart(self, junction: Junction):
        """Sets the junction for the back cart.

        Used by TrainMovement.update_positon(). The is how ther client updates the train position, 
        the server never uses this function.

        :param junction: The junction to be set for the back cart.
        """
        self.back_cart["junction"] = junction

    def set_track(self, track: Track):
        """Sets the track for both the front and back carts.

        :param track: The track to be set for both carts.
        """
        self.front_cart["track"] = track
        self.back_cart["track"] = track

    def set_to_park(self):
        """Parks the train at junction

        Used by TrainMovement.handle_arrival_at_junction(). The is how ther client updates the train position, 
        the server never uses this function.
        """
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