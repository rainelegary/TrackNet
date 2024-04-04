import socket
import logging
import signal

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
        ("B", "C", 10),
        ("C", "D", 10),
        ("A", "D", 40)
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


def exit_gracefully(signum, frame):
    global exit_flag

    sig_type = 'Unknown'
    if signum == signal.SIGTERM:
        sig_type == 'SIGTERM'
    elif signum == signal.SIGINT:
        sig_type == 'SIGINT'

    print('Trying to exit gracefully. ' + sig_type)
    exit_flag = True

DEBUGV= 9 
def debugv(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(DEBUGV, message, args, **kws) 

def setup_logging():
    logging.addLevelName(DEBUGV, "DEBUGV")
    logging.Logger.debugv = debugv
    formatter = logging.Formatter(fmt='%(lineno)d %(asctime)s %(levelname)s@%(name)s: %(message)s', datefmt='%H:%M:%S')
    handler = logging.StreamHandler()
    #handler.setLevel(DEBUGV)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(handler)


def int_to_bytes(value: int, length: int) -> bytes:
    """Convert the given integer into a bytes object with the specified
       number of bits. Uses network byte order.

    PARAMETERS
    ==========
    value: An int to be converted.
    length: The number of bytes this number occupies.

    RETURNS
    =======
    A bytes object representing the integer.
    """

    assert type(value) == int
    assert length > 0   # not necessary, but we're working with positive numbers only

    return value.to_bytes(length, 'big')


def bytes_to_int(value: bytes) -> int:
    """Convert the given bytes object into an integer. Uses network
       byte order.

    PARAMETERS
    ==========
    value: An bytes object to be converted.

    RETURNS
    =======
    An integer representing the bytes object.
    """

    assert type(value) == bytes
    return int.from_bytes(value, 'big')


def create_client_socket(ip: str, port: int):
    """Create a TCP/IP socket at the specified port.

    PARAMETERS
    ==========
    ip: A string representing the IP address to connect to.
    port: An integer representing the port to connect to.

    RETURNS
    =======
    If successful, a connected socket object.
    Otherwise, return None.
    """

    assert type(ip)   == str
    assert type(port) == int

    #socket.setdefaulttimeout(0.5)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((ip, port))
    except Exception as e:
        print ("Failed to connect to socket at " + ip + ":" + str(port))
        print ("exception: " + str(e))
        return None

    return sock


def create_server_socket(ip: str, port: int):
    """Create a TCP/IP socket at the specified port.

    PARAMETERS
    ==========
    ip: A string representing the IP address to connect to.
    port: An integer representing the port to connect to.

    RETURNS
    =======
    If successful, a connected socket object.
    Otherwise, return None.
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
        print("Server Listening on " + ip + ":" + str(port))

    except Exception as exc:
        print('Socket creation Failed: ' + str(exc))
        exitFlag = True
        return None

    return sock


def send(sock: socket.socket, msg , returnException=False) -> bool:
    """ First Sends the number of bytes in msg padded to 4 bytes, then sends
    provided data across the given socket.

    PARAMETERS
    ==========
    sock: A socket object to use for sending.
    msg:  A string containing the data to send.

    RETURNS
    =======
    True if all data successfully sent over socket.
    False otherwise.
    """
    try:
        assert type(sock) == socket.socket
        assert type(msg) == bytes

        msg_len = int_to_bytes(len(msg), 4)

    
        sock.sendall(msg_len)
        sock.sendall(msg)

    except Exception as e:
        if returnException:
            raise e
        else:
            sock.close()
            return False

    return True


def receive(sock: socket.socket, returnException=False, timeout=10) -> bytes:
    """Receives 4 bytes of data indicating length of incomming message then receives
    message.

    PARAMETERS
    ==========
    sock: A socket object to use for receiving.

    RETURNS
    =======
    A string containing the received data or None if an error occured.
    """
    assert type(sock) == socket.socket
    data = b''

    try:
        sock.settimeout(timeout)
        content_length = sock.recv(4)
        data = sock.recv(bytes_to_int(content_length))

        # bytes_to_recv = bytes_to_int(content_length)
        #while bytes_to_recv > 0:
        #    recv = sock.recv(bytes_to_recv)

        #    bytes_to_recv = bytes_to_recv - len(recv)
        #    data = data + recv

    except Exception as e:
        if returnException:
            raise e
        else:
            return None

    #if not data:
    #    raise ValueError("Received data is empty.")

    return data

