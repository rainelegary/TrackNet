#!/usr/bin/env python3

from classes.railway import Railway


print("Creating a railway...")

initial_config = {
    "junctions": ["A", "B", "C", "D"],
    "tracks": [
        ("A", "B", 10),
        ("B", "C", 20),
        ("C", "D", 30),
        ("A", "D", 40)
    ]
}

railway_system = Railway(
    trains=None,
    junctions=initial_config["junctions"],
    tracks=initial_config["tracks"]
)

print(railway_system.find_shortest_path("B", "D"))


for junc in railway_system.junctions.values():
    print(f"Junction: {junc.name} neighbors:  {junc.neighbors.keys()}")
    