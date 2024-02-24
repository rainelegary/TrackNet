# TrackNet

## Documentation
Simulation speed - simulation-time:real-time = 60:1
Train speed is an element of {0, 1, 2} km per real-time second

Train has a front location and a back location.
Each location is represented solely as a track id and progress along track.

Each track's ID is a tuple (nodeA_id, nodeB_id) in ascending order by id.

## Todo

### Short term todo

Refactor so Route's ist of junctions is named to "junctions" instead of "tracks"
Updated Reroute function in ConflictAnalyzer
Change "self.tracks" variable in railway to a dictionary
Talk about proof of concept in project document
Conflict analyzer

### Long term todo

Add proxies
Add replication
Add server-to-server, proxy-to-proxy, and client-to-proxy communication
Scheduler
Time synchronization
Allow for train reversal




