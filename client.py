import argparse
import socket
import sys
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
import random
from classes.location import Location

# Global Variables
proxy1_address = None
proxy2_address = None
proxy1_port_num = None
proxy2_port_num = None

proxyDetailsProvided = False
cmdLineProxyDetails = []

setup_logging()  ## only need to call at main entry point of application
LOGGER = logging.getLogger("Client")

# initial_config = {
#     "junctions": ["A", "B", "C", "D"],
#     "tracks": [("A", "B", 10), ("B", "C", 10), ("C", "D", 10), ("A", "D", 40)],
# }
# signal.signal(signal.SIGTERM, exit_gracefully)
# signal.signal(signal.SIGINT, exit_gracefully)


class Client():
    """A client class responsible for simulating a train's interaction with a server, including sending its state and receiving updates. This class manages the connection to the server, serializes train state information, sends it to the server, and handles responses to adjust the train's movement or route accordingly.

    Attributes
    ----------
    host : str
      The hostname or IP address of the server to connect to. Defaults to "csx2.ucalgary.ca".

    port : int
      The port number on the server to connect to. Defaults to 5555.

    sock : socket.socket
      Socket object for the client. Initially set to None.

    train : TrainMovement
      A TrainMovement object representing the client's train.

    probabilty_of_good_track : int
      The probability (as a percentage) that the track condition is good. Defaults to 95.
    """
    
    def __init__(self, host: str ="csx2.ucalgary.ca", port: int =5555, origin=None, destination=None):
        """ Initializes the client instance, setting up the railway map, generating a route for the train, and starting a thread to update the train's position. It also initializes proxy connection details if provided through command line arguments.

        :param host: The hostname or IP address of the server to connect to.
        :param port: The port number on the server to connect to.
        """
        self.host = host
        self.port = port
        self.sock = None
        self.client_ip = None
        self.client_port = None
        self.probabilty_track_stay_good = 0.95
        self.probability_track_stay_bad = 0.8

        self.sentInitClientState = False

        self.railmap = Railmap(
            junctions=initial_config["junctions"], tracks=initial_config["tracks"]
        )
        self.last_time_updated = datetime.now()
        
        if origin == None:
            self.origin, self.destination = self.railmap.get_origin_destination_junction()
        else:
            self.origin = self.railmap.junctions[origin]
            self.destination = self.railmap.junctions[destination]
        self.train = TrainMovement(
            length=self.generate_random_train_length(),
            location = Location(front_junction=self.origin, back_junction=self.origin)
        )
        self.generate_route()

        debug_str = "Route:"
        for junc in self.train.route.junctions:
            debug_str = debug_str + "->" + junc.name
        LOGGER.info(debug_str + "\n\n")
                    
        threading.Thread(target=self.update_position, args=(), daemon=True).start() 

        if proxyDetailsProvided:
            proxy_items = cmdLineProxyDetails
        else:
            proxy_items = list(proxy_details.items())

        #index = random.randint(0, len(proxy_items) - 1)
        index = random.choice([0,1])
        self.current_proxy = proxy_items[index]  # First item
        self.backup_proxy = proxy_items[(index + 1) % (len(proxy_items))]  # Second item   
        LOGGER.info(f"Current proxy: {self.current_proxy}")     
        LOGGER.info(f"Backup proxy: {self.backup_proxy}")
        try:
            self.run()
        except KeyboardInterrupt:
            LOGGER.debug(f"Keyboard interupt was detected, will close")
            sys.exit(1)
        except Exception as e:
            LOGGER.debug(f"Exception: {e} was thrown, will close")
            sys.exit(1)
            

    def generate_random_train_length(self) -> int:
        """Generates a random train length between 1 and 5.

        :return: A random integer representing the train's length.
        """
        return random.randint(1, 5) 

    def generate_route(self):
        """Generates a route for the train based on the railway map. """
        self.train.route = Route(self.railmap.find_shortest_path(self.origin.name, self.destination.name))
        self.train.location.set_track(self.train.route.get_next_track())
        self.train.prev_junction = self.origin
        self.train.next_junction = self.train.route.get_next_junction()
        LOGGER.debug(f"init track={self.train.route.get_next_track().name}")
        LOGGER.debug("Route created")

    def get_track_condition(self) -> TrackNet_pb2.TrackCondition:
        """Determines the track condition based on a predefined probability.

        :return: Returns track condition as GOOD or BAD
        :rtype: TrackNet_pb2.ClientState.TrackCondition
        """
        return (
            TrackNet_pb2.TrackCondition.GOOD
            if random.random() < self.probabilty_track_stay_good
            else TrackNet_pb2.TrackCondition.BAD
        )

    def update_position(self):
        """A loop that runs continuously to update the train's position and checks if the destination is reached. """
        while not utils.exit_flag and not (self.train.route.destination_reached()):
            self.last_time_updated = datetime.now()
            time.sleep(2)

            if self.train.state in [TrainState.PARKED, TrainState.STOPPED]:
                #LOGGER.debug(f"Trains is parked")
                continue
            else:
                elapsed_time = (datetime.now() - self.last_time_updated).total_seconds()

                # Adjust the speed to achieve desired movement
                speed_factor = 10  # Adjust this factor as needed
                effective_speed = self.train.get_speed() * speed_factor
                distance_moved = effective_speed * (elapsed_time / 3600)  # Assuming speed is in km/h
                #LOGGER.debug(f"Distance moved by train: {distance_moved}")
                self.train.update_location(distance_moved)
            

        LOGGER.debug(f"*****************DESTINATION REACHED*******************")
        os._exit(0)  # Exit the program immediately with a status of 0

    def set_client_state_msg(self, state: TrackNet_pb2.ClientState, clientIP, clientPort):
        """Populates a `ClientState` message with the current state of the train.

        :param state: The `ClientState` message object to be populated.
        :param clientIP: IP address of the client.
        :param clientPort: Port number of the client.
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

            state.route.current_junction_index = self.train.route.current_junction_index

    def set_route(self, route: TrackNet_pb2.Route):
        """Sets a new route for the train based on the route information received from the server.

        :param route: A protobuf Route message detailing the new route.
        """
        new_route = []
        for junc in route.junction_ids:
            new_route.append(self.railmap.junctions[junc])
        self.train.route = Route(new_route, route.current_junction_index)
        self.train.location.set_track(self.train.route.get_next_track())
        LOGGER.debug(f"init track={self.train.route.get_next_track()}")

    def run(self):
        """Initiates the client's main loop, managing the socket connection, 
        sending the train's state, and processing responses from the server."""
        connected_to_main_proxy = True
        connected_to_proxy = False

        while not utils.exit_flag:
            try:
                # Attempt to connect or reconnect if necessary
                if not connected_to_proxy:
                    #set current proxy to 
                    proxy_host, proxy_port = self.current_proxy
                    self.sock = create_client_socket(proxy_host, proxy_port)
                    
                    #self.sock.settimeout(10)  # Set a 10-second timeout for the socket

                    if (not self.sock):  # If connection failed, switch to backup and retry
                        LOGGER.debug("Connection with main proxy failed, switching to backup proxy.")
                        temp = self.current_proxy
                        self.current_proxy = self.backup_proxy
                        self.backup_proxy = temp

                        connected_to_main_proxy = False
                        
                        continue  # Skip the rest of this iteration
                    else:
                        connected_to_proxy = True
                        self.client_ip, self.client_port = self.sock.getsockname()

                else:
                    
                    client_state = TrackNet_pb2.ClientState()
                    
                    self.set_client_state_msg(client_state, self.client_ip, self.client_port)
                    LOGGER.debug(f"state:\n{client_state.location}")
                    self.train.print_train()

                    message = TrackNet_pb2.InitConnection()
                    message.sender = TrackNet_pb2.InitConnection.Sender.CLIENT
                    message.client_state.CopyFrom(client_state)

                    if (self.sentInitClientState == True) and (self.train.name is None):
                        LOGGER.debug("Will not send anymore client states untill train id is set (a server response is handled")
                        try:
                            data = receive(self.sock,returnException=True,timeout=2)
                            resp = TrackNet_pb2.InitConnection()
                            server_resp = TrackNet_pb2.ServerResponse()

                            if data is not None:
                                resp.ParseFromString(data)
                                server_resp.CopyFrom(resp.server_response)
                                self.handle_server_response(server_resp)
                            
                        except socket.timeout:
                            #LOGGER.warning("Socket timeout. Switching to backup proxy.")
                            LOGGER.debug(f"Socket timeout. Will wait for a server response")

                        except Exception as e:
                            LOGGER.warning(f"Exception thrown after sending client state {e}, Will switch to backup proxy {self.backup_proxy}")
                            self.sock.close()
                            self.sock = None
                            connected_to_proxy = False
                            temp = self.current_proxy
                            self.current_proxy = self.backup_proxy
                            self.backup_proxy = temp

                    else:
                        if send(self.sock, message.SerializeToString()):
                            LOGGER.debug(f" Sent client state to proxy ")
                            self.sentInitClientState = True
                            try:
                                data = receive(self.sock,returnException=True,timeout=2)
                                resp = TrackNet_pb2.InitConnection()
                                server_resp = TrackNet_pb2.ServerResponse()

                                if data is not None:
                                    resp.ParseFromString(data)
                                    server_resp.CopyFrom(resp.server_response)
                                    self.handle_server_response(server_resp)
                                
                            except socket.timeout:
                                #LOGGER.warning("Socket timeout. Switching to backup proxy.")
                                LOGGER.debug(f"Socket timeout. Will resend a client state")
                                #self.sock.close()
                                #self.sock = None
                                #connected_to_proxy = False
                                #self.current_proxy = self.backup_proxy

                            except Exception as e:
                                LOGGER.warning(f"Exception thrown after sending client state {e}, Will switch to backup proxy {self.backup_proxy}")
                                self.sock.close()
                                self.sock = None
                                connected_to_proxy = False
                                temp = self.current_proxy
                                self.current_proxy = self.backup_proxy
                                self.backup_proxy = temp

                        
                        else:
                            LOGGER.debug(f"Unable to send the client state to the proxy server. Switch to backup proxy: {self.backup_proxy} ")
                            connected_to_proxy = False 
                            self.sock.close()
                            self.sock = None
                            temp = self.current_proxy
                            self.current_proxy = self.backup_proxy
                            self.backup_proxy = temp
        
            except Exception as e:
                traceback.print_exception(e)
                LOGGER.error(f"Unexpected error in the main loop: {e}  ")

                break  # Exit the loop on unexpected error

            time.sleep(5)

    def handle_server_response (self, server_resp: TrackNet_pb2.ServerResponse):
        """Handles the response received from the server, adjusting the train's speed, route, or stopping the train as instructed by the server.

        :param server_resp: The server response as a protobuf message.
        """
        LOGGER.debug(f"handling server response: {server_resp} none: {server_resp==None}")
        if self.train.name is None:
            self.train.name = server_resp.train.id
            LOGGER.debug(f"Initi. {self.train.name}")

        if self.train.route is None:
            if not server_resp.HasField("new_route"):
                LOGGER.warning(f"Server has not yet provided route for train.")
                ## cannot take instructions until route is assigned
                self.sock.close()
                return
            
        if server_resp.HasField("status"):
            if server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CHANGE_SPEED:
                LOGGER.debug(f"CHANGE_SPEED {self.train.name} to {server_resp.speed}")
                self.train.stay_parked = False
                self.train.set_speed(server_resp.speed)

            elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.REROUTE:
                LOGGER.debug(f"REROUTING {self.train.name}")
                self.set_route(server_resp.route)

            elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.STOP:
                LOGGER.debug(f"STOPPING {self.train.name}")
                self.train.stop()
                                
            elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.CLEAR:
                self.train.stay_parked = False
                if self.train.state == TrainState.PARKED:
                    LOGGER.debug("UNPARKING")
                    self.train.leave_junction()
                elif self.train.state == TrainState.STOPPED:
                    LOGGER.debug("RESUMING MOVEMENT")
                    self.train.resume_movement(server_resp.speed)
                elif self.train.state == TrainState.RUNNING and self.train.current_speed == TrainSpeed.SLOW.value:
                    LOGGER.debug("SPEEDING UP")
                    self.train.set_speed(TrainSpeed.FAST.value)
            
            elif server_resp.status == TrackNet_pb2.ServerResponse.UpdateStatus.PARK:
                self.train.stay_parked = True
        else:
            LOGGER.debug(f"Server response has no status")

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process Server args")

    parser.add_argument('-proxy1', type=str, help='Address for proxy1')
    parser.add_argument('-proxy2', type=str, help='Address for proxy2')
    parser.add_argument('-proxyPort1', type=int, help='Proxy 1 port number')
    parser.add_argument('-proxyPort2', type=int, help='Proxy 2 port number')
    parser.add_argument('-start', type=str, help='Start junction')
    parser.add_argument('-destination', type=str, help='Destination junction')
    
    
    args = parser.parse_args()

    proxy1_address = args.proxy1
    proxy2_address = args.proxy2
    proxy1_port_num = args.proxyPort1
    proxy2_port_num = args.proxyPort2
    start_junction = args.start
    destination_junction = args.destination

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
    Client(origin=start_junction, destination=destination_junction)
