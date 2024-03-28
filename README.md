# TrackNet

## How to run the code

main proxy: csa1.ucalgary.ca 1234
backup proxy: csa2.ucalgary.ca 12345
first server: csa1.ucalgary.ca 12346
second server: csa2.ucalgary.ca 12346

to run main proxy: 
    python3 proxy.py -main -listeningPort 1234

to run backup proxy: 
    python3 proxy.py -backup -listeningPort 12345 -proxy_address csa1.ucalgary.ca -proxyPort 1234

to run server: 
    python3 server.py -proxy1 csa1.ucalgary.ca -proxy2 csa2.ucalgary.ca -proxyPort1 1234 -proxyPort2 12345

to run server with custom listening port: 
    python3 server.py -proxy1 csa1.ucalgary.ca -proxy2 csa2.ucalgary.ca -proxyPort1 1234 -proxyPort2 12345 -listeningPort 12346

to run client: 
    python3 client.py -proxy1 csa1.ucalgary.ca -proxy2 csa2.ucalgary.ca -proxyPort1 1234 -proxyPort2 12345


## Documentation
Simulation speed - simulation-time:real-time = 60:1
Train speed is an element of {0, 1, 2} km per real-time second

Train has a front location and a back location.
Each location is represented solely as a track id and progress along track.

Each track's ID is a tuple (nodeA_id, nodeB_id) in ascending order by id.

## Todo

### Short term (next demo)

Anything in the code-base marked with "TODO POC"
Create Command data structure for conflcit analyzer
Write a function that turns a command data structure into a message for the server to send
Allow client to handle park command, using train.stay_parked field
Talk about proof of concept in project document


### Medium term todo

Add more details to Route class
Upgrade conflict analyzer
Updated Reroute function in ConflictAnalyzer


### Long term todo

Anything in the code-base marked with "TODO"
Add proxies
Add replication
Add server-to-server, proxy-to-proxy, and client-to-proxy communication
Conflict analyzer
Make pre-determined track conditions that everyone has immediate access to without communication
Scheduler
Time synchronization
Allow for train reversal




