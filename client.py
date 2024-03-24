import argparse
import socket
import traceback
import TrackNet_pb2
import logging
import signal
import time
import random
import threading
import utils
import os
from utils import *
from classes import *
from classes.enums import *
from classes.railmap import Railmap
from classes.route import Route
from classes.trainmovement import TrainMovement
from datetime import datetime
from message_converter import MessageConverter
import random


# Global Variables
proxy1_address = None
proxy2_address = None
proxy1_port_num = None
proxy2_port_num = None

proxyDetailsProvided = False
cmdLineProxyDetails = []

setup_logging()  ## only need to call at main entry point of application
LOGGER = logging.getLogger("Client")

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [("A", "B", 10), ("B", "C", 10), ("C", "D", 10), ("A", "D", 40)],
}
# signal.signal(signal.SIGTERM, exit_gracefully)
# signal.signal(signal.SIGINT, exit_gracefully)


class Client():
    
    def __init__(self, host: str ="csx2.ucalgary.ca", port: int =5555):
        """ A client class responsible for simulating a train's interaction with a server, including sending its state and receiving updates.

        :param host: The hostname or IP address of the server to connect to.
        :param port: The port number to connect to on the server.
        :ivar host: Hostname or IP address of the server.
        :ivar port: Port number for the server connection.
        :ivar sock: Socket object for the client. Initially set to None.
        :ivar train: A Train object representing the client's train.
        :ivar probabilty_of_good_track: The probability (as a percentage) that the track condition is good.
        """
        self.host = host
        self.port = port
        self.sock = None
        self.probabilty_of_good_track = 95
        self.railmap = Railmap(
            junctions=initial_config["junctions"], tracks=initial_config["tracks"]
        )
        self.last_time_updated = datetime.now()

        self.origin, self.destination = self.railmap.get_origin_destination_junction()
        self.train = TrainMovement(
            length=self.generate_random_train_length(),
            junction_front=self.origin,
            junction_back=self.origin,
        )
        self.generate_route()
        print("Route: ", end="")
        for junc in self.train.route.junctions:
            print("->", junc.name, end=" ")
        print()
        print()
                    
        threading.Thread(target=self.update_position, args=(), daemon=True).start() 
        

        if proxyDetailsProvided:
            proxy_items = cmdLineProxyDetails
        else:
            proxy_items = list(proxy_details.items())

        index = random.randint(0, len(proxy_items) - 1)
        self.current_proxy = proxy_items[index]  # First item
        self.backup_proxy = proxy_items[(index + 1) % (len(proxy_items))]  # Second item   
        print (f"Current proxy: {self.current_proxy}")     
        print (f"Backup proxy: {self.backup_proxy}")     
        self.run()

    def generate_random_train_length(self):
        ## TODO
        return 5

    def generate_route(self):
        self.train.route = Route(
            self.railmap.find_shortest_path(self.origin.name, self.destination.name)
        )
        self.train.location.set_track(self.train.route.get_next_track())
        self.train.prev_junction = self.origin
        self.train.next_junction = self.train.route.get_next_junction()
        LOGGER.debug(f"init track={self.train.route.get_next_track()}")
        LOGGER.debug("Route created")

    def get_track_condition(self):
        """Determines the track condition based on a predefined probability.

        :return: Returns GOOD track condition with a 95% probability and BAD track condition with a 5% probability.
        :rtype: TrackNet_pb2.ClientState.TrackCondition
        """
        return (
            TrackNet_pb2.TrackCondition.GOOD
            if random.random() < self.probabilty_of_good_track
            else TrackNet_pb2.TrackCondition.BAD
        )

    def update_position(self):
        ## TODO decided how often to update
        while not utils.exit_flag and not (self.train.route.destination_reached()):
            time.sleep(2)

            #            if self.train.route.destination_reached():
            #                #self.stay_parked = True
            #                LOGGER.debug(f"*****************DESTINATION REACHED*******************")
            #                utils.exit_flag = True
            #                break

            if self.train.state in [TrainState.PARKED, TrainState.STOPPED]:
                continue
            else:
                elapsed_time = (datetime.now() - self.last_time_updated).total_seconds()

                # Adjust the speed to achieve desired movement
                speed_factor = 10  # Adjust this factor as needed
                effective_speed = self.train.get_speed() * speed_factor
                distance_moved = effective_speed * (
                    elapsed_time / 3600
                )  # Assuming speed is in km/h

                self.train.update_location(distance_moved)
                self.last_time_updated = datetime.now()

        LOGGER.debug(f"*****************DESTINATION REACHED*******************")
        os._exit(0)  # Exit the program immediately with a status of 0
        # utils.exit_flag = True

    def set_client_state_msg(
        self, state: TrackNet_pb2.ClientState, clientIP, clientPort
    ):
        """Populates a `ClientState` message with the current state of the train, including its id, length, speed, location, track condition, and route.

        :param state: The `ClientState` message object to be populated with the train's current state.
        """

        state.client.host = clientIP
        state.client.port = clientPort

        if self.train.name is not None:
            state.train.id = self.train.name
        state.train.length = self.train.length
        state.train.state = self.train.state.value
        state.speed = self.train.get_speed()
        self.train.location.set_location_message(state.location)
        state.condition = self.get_track_condition()

        if self.train.route is not None:
            for junction_obj in self.train.route.junctions:
                state.route.junction_ids.append(junction_obj.name)

    def set_route(self, route: TrackNet_pb2.Route):
        new_route = []
        for junc in route.junction_ids:
            new_route.append(self.railmap.junctions[junc])
        self.train.route = Route(new_route)
        self.train.location.set_track(self.train.route.get_next_track())
        LOGGER.debug(f"init track={self.train.route.get_next_track()}")

    #Made new function below
    def run_working(self):
        """Initiates the client's main loop, continuously sending its state to the server and processing the server's response. It handles connection management, state serialization, and response deserialization. Based on the server's response, it adjusts the train's speed, reroutes, or stops as necessary.

        The method uses a loop that runs until an `exit_flag` is set. It manages the socket connection, sends the train's state, and processes responses from the server. The method also handles rerouting, speed adjustments, and stopping the train based on the server's instructions.
        """
        while not utils.exit_flag:
            try:
                self.sock = create_client_socket(self.host, self.port)
                client_ip, client_port = self.sock.getsockname()
                print(f"{client_ip}:{client_port}")
                if self.sock is not None:
                    LOGGER.debug("Connected")
                    client_state = TrackNet_pb2.ClientState()

                    self.set_client_state_msg(client_state, client_ip, client_port)
                    LOGGER.debug(f"state={client_state.location}")

                    message = TrackNet_pb2.InitConnection()
                    message.sender = TrackNet_pb2.InitConnection.Sender.CLIENT
                    message.client_state.CopyFrom(client_state)

                    if send(self.sock, message.SerializeToString()):
                        data = receive(self.sock)
                        resp = TrackNet_pb2.InitConnection()
                        server_resp = TrackNet_pb2.ServerResponse()

                        if data is not None:
                            resp.ParseFromString(data)
                            server_resp.CopyFrom(resp.server_response)

                            if self.train.name is None:
                                self.train.name = server_resp.train.id
                                LOGGER.debug(f"Initi. {self.train.name}")

                            if self.train.route is None:
                                if not server_resp.HasField("new_route"):
                                    LOGGER.warning(
                                        f"Server has not yet provided route for train."
                                    )
                                    ## cannot take instructions until route is assigned
                                    self.sock.close()
                                    continue

                            if (
                                server_resp.status
                                == TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED
                            ):
                                LOGGER.debug(
                                    f"CHANGE_SPEED {self.train.name} to {server_resp.speed}"
                                )
                                self.train.set_speed(server_resp.speed)

                            elif (
                                server_resp.status
                                == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE
                            ):
                                LOGGER.debug(f"REROUTING {self.train.name}")
                                self.set_route(server_resp.route)

                            elif (
                                server_resp.status
                                == TrackNet_pb2.ServerResponse.UpdateStatus.STOP
                            ):
                                LOGGER.debug(f"STOPPING {self.train.name}")
                                self.train.stop()

                            elif (
                                server_resp.status
                                == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR
                            ):
                                if self.train.state == TrainState.PARKED:
                                    LOGGER.debug("UNPARKING")
                                    self.train.unpark(server_resp.speed)
                                elif self.train.state == TrainState.STOPPED:
                                    LOGGER.debug("RESUMING MOVEMENT")
                                    self.train.resume_movement(server_resp.speed)
                                elif (
                                    self.train.state == TrainState.RUNNING
                                    and self.train.current_speed
                                    == TrainSpeed.SLOW.value
                                ):
                                    LOGGER.debug("SPEEDING UP")
                                    self.train.set_speed(TrainSpeed.FAST.value)

                        # self.sock.close()
                else:
                    LOGGER.debug(f"no connection")

            except Exception as exc:
                LOGGER.warning(f"run(): {exc}")

            time.sleep(2)

    def run (self):
        """Initiates the client's main loop, continuously sending its state to the server and processing the server's response. It handles connection management, state serialization, and response deserialization. Based on the server's response, it adjusts the train's speed, reroutes, or stops as necessary.

        The method uses a loop that runs until an `exit_flag` is set. It manages the socket connection, sends the train's state, and processes responses from the server. The method also handles rerouting, speed adjustments, and stopping the train based on the server's instructions.
        """

        connected_to_main_proxy = True
        connected_to_proxy = False

        while not utils.exit_flag:
            try:
                # Attempt to connect or reconnect if necessary
                if not connected_to_proxy:
                    #set current proxy to 
                    proxy_host, proxy_port = self.current_proxy
                    self.sock = create_client_socket(proxy_host, proxy_port)
                    client_ip, client_port = self.sock.getsockname()
                    #self.sock.settimeout(10)  # Set a 10-second timeout for the socket

                    if (
                        not self.sock
                    ):  # If connection failed, switch to backup and retry
                        print(
                            "Connection with main proxy failed, switching to backup proxy."
                        )
                        self.current_proxy = self.backup_proxy
                        connected_to_main_proxy = False
                        
                        continue  # Skip the rest of this iteration
                    else:
                        connected_to_proxy = True
                else:

                    client_state = TrackNet_pb2.ClientState()

                    self.set_client_state_msg(client_state, client_ip, client_port)
                    LOGGER.debug(f"state={client_state.location}")

                    message = TrackNet_pb2.InitConnection()
                    message.sender = TrackNet_pb2.InitConnection.Sender.CLIENT
                    message.client_state.CopyFrom(client_state)

                    LOGGER.debug(f" Sending client state to proxy ")

                    if send(self.sock, message.SerializeToString()):
                        try:
                            data = receive(self.sock,returnException=True,timeout=2)
                            resp = TrackNet_pb2.InitConnection()
                            server_resp = TrackNet_pb2.ServerResponse()

                            if data is not None:
                                resp.ParseFromString(data)
                                server_resp.CopyFrom(resp.server_response)
                                self.handle_server_response (server_resp)
                            
                        except socket.timeout:
                            LOGGER.warning("Socket timeout. Switching to backup proxy.")
                            self.sock.close()
                            self.sock = None
                            connected_to_proxy = False
                            self.current_proxy = self.backup_proxy
                        except Exception as e:
                            LOGGER.warning(f"Exception thrown after sending client state {e}, Will switch to backup proxy {self.backup_proxy}")
                            self.sock.close()
                            self.sock = None
                            connected_to_proxy = False
                            self.current_proxy = self.backup_proxy

                    
                    else:
                       
                       LOGGER.debug(f"Unable to send the client state to the proxy server. Switch to backup proxy: {self.backup_proxy} ")
                       connected_to_proxy = False 
                       self.sock.close()
                       self.sock = None
                       self.current_proxy = self.backup_proxy
        
            except Exception as e:
                LOGGER.error(f"Unexpected error in the main loop: {e}  ")
                break  # Exit the loop on unexpected error

            time.sleep(5)


    def handle_server_response (self, server_resp):
        if self.train.name is None:
            self.train.name = server_resp.train.id
            LOGGER.debug(f"Initi. {self.train.name}")

        if self.train.route is None:
            if not server_resp.HasField("new_route"):
                LOGGER.warning(f"Server has not yet provided route for train.")
                ## cannot take instructions until route is assigned
                self.sock.close()
                return

        if server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED:
            LOGGER.debug(f"CHANGE_SPEED {self.train.name} to {server_resp.speed}")
            self.train.set_speed(server_resp.speed)

        elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE:
            LOGGER.debug(f"REROUTING {self.train.name}")
            self.set_route(server_resp.route)

        elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP:
            LOGGER.debug(f"STOPPING {self.train.name}")
            self.train.stop()
                            
        elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR:
            if self.train.state == TrainState.PARKED:
                LOGGER.debug("UNPARKING")
                self.train.unpark(server_resp.speed)
            elif self.train.state == TrainState.STOPPED:
                LOGGER.debug("RESUMING MOVEMENT")
                self.train.resume_movement(server_resp.speed)
            elif self.train.state == TrainState.RUNNING and self.train.current_speed == TrainSpeed.SLOW.value:
                LOGGER.debug("SPEEDING UP")
                self.train.set_speed(TrainSpeed.FAST.value)    
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process Server args")

    parser.add_argument('-proxy1', type=str, help='Address for proxy1')
    parser.add_argument('-proxy2', type=str, help='Address for proxy2')
    parser.add_argument('-proxyPort1', type=int, help='Proxy 1 port number')
    parser.add_argument('-proxyPort2', type=int, help='Proxy 2 port number')
    
    
    args = parser.parse_args()

    proxy1_address = args.proxy1
    proxy2_address = args.proxy2
    proxy1_port_num = args.proxyPort1
    proxy2_port_num = args.proxyPort2

    LOGGER.debug(f"Proxy 1 address {proxy1_address}")
    LOGGER.debug(f"Proxy 2 address {proxy2_address}")
    LOGGER.debug(f"Proxy 1 port number {proxy1_port_num}")
    LOGGER.debug(f"Proxy 2 port number {proxy2_port_num}")

    if proxy1_port_num == None:
        proxy1_port_num =5555
    
    if proxy2_port_num == None:
        proxy2_port_num = 5555

    if proxy1_address == None and proxy2_address == None:
        #use proxydetails
        proxyDetailsProvided = False
        LOGGER.debug(f"Proxy details not provided, will use util values")
    else:
        proxyDetailsProvided = True
        LOGGER.debug(f"Proxy details provided, Proxy 1: {proxy1_address}:{proxy1_port_num} and Proxy 2: {proxy2_address}:{proxy2_port_num}")
        if proxy1_address != None:
            cmdLineProxyDetails.append((proxy1_address, proxy1_port_num))
        if proxy2_address != None:
            cmdLineProxyDetails.append((proxy2_address, proxy2_port_num))
    Client()
