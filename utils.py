import socket
import logging
import signal

__all__ = [
    "setup_logging",
    "exit_flag",
    "exit_gracefully",
    "create_client_socket",
    "create_server_socket",
    "send",
    "receive"
]

exit_flag = False

def exit_gracefully(signum, frame):
    global exitFlag
    global img_sock

    sig_type = 'Unknown'
    if signum == signal.SIGTERM:
        sig_type == 'SIGTERM'
    elif signum == signal.SIGINT:
        sig_type == 'SIGINT'

    print('Trying to exit gracefully. ' + sig_type)
    exitFlag = True

    if img_sock:
        img_sock.close()


def setup_logging():
    formatter = logging.Formatter('%(asctime)s %(levelname)s@%(name)s: %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    
    logging.root.setLevel(logging.INFO)
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

    assert type(ip) == str
    assert type(port) == int

    socket.setdefaulttimeout(0.5)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((ip, port))
    except:
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


def send(sock: socket.socket, msg) -> bool:
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
    assert type(sock) == socket.socket
    assert type(msg) == bytes

    msg_len = int_to_bytes(len(msg), 4)

    try:
        sock.sendall(msg_len)
        sock.sendall(msg)

    except:
        sock.close()
        return False

    return True


def receive(sock: socket.socket) -> bytes:
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
        content_length = sock.recv(4)
        data = sock.recv(bytes_to_int(content_length))
        
        # bytes_to_recv = bytes_to_int(content_length)
        #while bytes_to_recv > 0:
        #    recv = sock.recv(bytes_to_recv)

        #    bytes_to_recv = bytes_to_recv - len(recv)
        #    data = data + recv

    except:
        return None

    return data