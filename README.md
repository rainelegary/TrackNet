# TrackNet

## Documentation
Simulation speed - simulation-time:real-time = 60:1
Train speed is an element of {0, 1, 2} km per real-time second

Train has a front location and a back location.
Each location is represented solely as a track id and progress along track.

Each track's ID is a tuple (nodeA_id, nodeB_id) in ascending order by id.

## Todo

Talk about proof of concept in project document
Add proxies
Add replication
Add server-to-server, proxy-to-proxy, and client-to-proxy communication
Conflict analyzer
Scheduler
Time synchronization
Allow for train reversal
Refactor so Route's ist of junctions is named to "junctions" instead of "tracks"
Updated Reroute function in ConflictAnalyzer



