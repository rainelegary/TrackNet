# TrackNet

TrackNet is a distributed simulation of a railway network where clients, representing individual trains, connect to proxies. These proxies relay requests to servers, which generate responses back to the clients through the proxies. This setup simulates a real-world railway system with an emphasis on distributed computing principles.

## Getting Started

To use TrackNet, first clone the repository using the following command:

```bash
git clone https://github.com/rainelegary/TrackNet.git
```

Navigate to the TrackNet folder before running any of the following commands.

## System Requirements

Before you begin, ensure your system meets the following requirements:

- **Python**: Python 3 is required to run the TrackNet components. You can verify your Python version by running `python --version` or `python3 --version` in your terminal.
- **Google Protocol Buffers for Python**: This is necessary for data serialization. Install it using the following command:

    ```bash
    pip install protobuf
    ```

- **Internet Connection**: An active internet connection is required for certain operations, such as cloning the repository and installing dependencies.

## Notice for University Environment

If you are running a proxy or server on university computers, please note that **all proxies and servers must also be hosted on university computers**. The university's network configuration prevents these computers from connecting to server sockets hosted on external machines. This restriction does not apply to clients, which can be run on either university computers or local machines, as they do not need to create server sockets.

## How to Run the Code

### Component Setup

The proper sequence for running the code is to start the main proxy, followed by the backup proxy, then the server(s), and finally the client(s).

#### Main Proxy

To run the main proxy:

```bash
python3 proxy.py -main -listeningPort 1234
```

#### Backup Proxy

To run the backup proxy:

```bash
python3 proxy.py -backup -listeningPort 12345 -proxy_address <main_proxy_address> -proxyPort 1234
```

Replace `<main_proxy_address>` with the address of the main proxy.

#### Server

To run a server with default settings:

```bash
python3 server.py -proxy1 <proxy1_address> -proxy2 <proxy2_address> -proxyPort1 1234 -proxyPort2 12345
```

To run a server with a custom listening port:

```bash
python3 server.py -proxy1 <proxy1_address> -proxy2 <proxy2_address> -proxyPort1 1234 -proxyPort2 12345 -listeningPort <custom_port>
```

Replace `<proxy1_address>`, `<proxy2_address>`, and `<custom_port>` with the appropriate addresses and port number.

#### Client

To run a client with optional start and destination:

```bash
python3 client.py -proxy1 <proxy1_address> -proxy2 <proxy2_address> -proxyPort1 1234 -proxyPort2 12345 -start <start_location> -destination <destination_location>
```

If the start and destination are not provided, the default route will be used.

### Example Locations

- Main proxy: `csa1.ucalgary.ca 1234`
- Backup proxy: `csa2.ucalgary.ca 12345`
- First server: `csa1.ucalgary.ca 12346`
- Second server: `csa2.ucalgary.ca 12346`
- Client: Any location

### Running with One Client and Backup Proxy

Refer to the component setup instructions above, replacing the example addresses and ports with those specified in this section.

### Running Two Clients Without Backup Proxy

For scenarios without a backup proxy, follow the component setup instructions, omitting the backup proxy setup.

## Documentation

- **Simulation Speed**: The simulation operates at a speed where 60 simulation minutes equal 1 real-time minute.
- **Train Speed**: Can be 0, 1, or 2 km per real-time second.
- **Location Representation**: Each train has a front and back location, each identified by a track ID and progress along the track.
- **Track ID**: Represented as a tuple `(nodeA_id, nodeB_id)` in ascending order by ID.