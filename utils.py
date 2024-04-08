import socket
import logging
import signal
import sys

LOGGER = logging.getLogger("utils")

__all__ = [
    "initial_config",
    "setup_logging",
    "exit_flag",
    "exit_gracefully",
    "create_client_socket",
    "create_server_socket",
    "send",
    "receive",
    "slave_to_master_port",
    "proxy_details",
    "proxy_port"
]


## tracks must be longer then train -> must be greater than 5
initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [
        ("A", "B", 10),
        ("B", "C", 20),
        ("C", "D", 30),
        ("A", "D", 3000)
    ]
}

slave_to_master_port = 4444
proxy_port = 5555

#assumes csx1.ucalgary.ca is the host
proxy_details = {
    "csx2.uc.ucalgary.ca": 5555,
    "csx3.uc.ucalgary.ca": 5555
}

exit_flag = False

LOGGER = logging.getLogger("utils")

def exit_gracefully(signum, frame):
    global exit_flag

    sig_type = 'Unknown'
    if signum == signal.SIGTERM.value:
        sig_type = 'SIGTERM'
    elif signum == signal.SIGINT.value:
        sig_type = 'SIGINT'
    
    print('Trying to exit gracefully. sig:'+sig_type)
    exit_flag = True
    #sys.exit(0)


DEBUGV= 9 
def debugv(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(DEBUGV, message, args, **kws) 


def setup_logging():
    logging.addLevelName(DEBUGV, "DEBUGV")
    logging.Logger.debugv = debugv
    formatter = logging.Formatter(fmt='%(lineno)d %(asctime)s %(levelname)s@%(name)s: %(message)s', datefmt='%H:%M:%S')
    handler = logging.StreamHandler()
    handler.setLevel(DEBUGV)
    # handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    # logging.root.setLevel(logging.DEBUG)
    logging.root.setLevel(DEBUGV)
    logging.root.addHandler(handler)


def int_to_bytes(value: int, length: int) -> bytes:
    """Convert the given int into a bytes object with `length` number of bits. 

    :param value: An int to be converted.
    :param length: The number of bytes this number occupies.
    :returns: A bytes object representing the integer.
    """

    assert type(value) == int
    assert length > 0   # not necessary, but we're working with positive numbers only

    return value.to_bytes(length, 'big')


def bytes_to_int(value: bytes) -> int:
    """Convert the bytes object into an int. 

    :param value: An bytes object to be converted.
    :returns: integer representing the bytes object.
    """
    assert type(value) == bytes
    return int.from_bytes(value, 'big')


def create_client_socket(ip: str, port: int, timeout=1):
    """Create a TCP/IP socket at the given port.

    :param ip: A string representing the IP address to connect to.
    :param port: An integer representing the port to connect to.
    :returns: A connected socket object or None if unsuccessful.
    """

    assert type(ip)   == str
    assert type(port) == int

    socket.setdefaulttimeout(timeout)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while not exit_flag:
        try:
           
            sock.connect((ip, port))
            if sock is not None:
                return sock
        except socket.timeout:
            LOGGER.debug(f"the socket connect timed out while trying to connect")
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            LOGGER.debug(f"Failed to connect to socket at {ip} : {str(port)}")
            return None


def create_server_socket(ip: str, port: int):
    """Create a TCP/IP socket at the given port.

    :parma ip: A string representing the IP address to connect to.
    :param port: An integer representing the port to connect to.

    :returns: A  connected socket object or None if unsuccessful
    """
    assert type(ip) == str
    assert type(port) == int

    global exitFlag

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((ip, port))
        sock.settimeout(4)
        sock.listen(5)
        #print("Server Listening on " + ip + ":" + str(port))

    except Exception as exc:
        print('Socket creation Failed: ' + str(exc))
        exitFlag = True
        return None

    return sock


def send(sock: socket.socket, msg , returnException=False) -> bool:
    """ First Sends the number of bytes in msg padded to 4 bytes, then sends
    provided data across the given socket.

    :param sock: A socket object to use for sending.
    :param msg: A string containing the data to send.
    :returns: True if all data successfully sent over socket, otherwise False
    """
    try:
        assert type(sock) == socket.socket
        assert type(msg) == bytes

        msg_len = int_to_bytes(len(msg), 4)

        sock.sendall(msg_len)
        sock.sendall(msg)

    except KeyboardInterrupt:
        sock.close()
        sys.exit(0)

    except Exception as e:
        if returnException:
            raise e
        else:
            sock.close()
            return False

    return True


def receive(sock: socket.socket, returnException=False, timeout=10) -> bytes:
    """Receives 4 bytes of data (length of incomming message) then receives message.

    :parma sock: A socket object to use for receiving.
    :returns: A string containing the received data or None if an error occured.
    """
    assert type(sock) == socket.socket
    data = b''

    try:
        sock.settimeout(timeout)
        content_length = sock.recv(4)
        data = sock.recv(bytes_to_int(content_length))
    except KeyboardInterrupt:
        LOGGER.debug(f"Keyboard interupt detected, will close")
        sys.exit(1)
    except Exception as e:
        if returnException:
            raise e
        else:
            return None

    return data



