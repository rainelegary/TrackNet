# TrackNet

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




