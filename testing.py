from classes import *
import time


# Create a  map
my_map = Map()

# Add junctions
my_map.add_junction("A")
my_map.add_junction("B")
my_map.add_junction("C")

# Add tracks between junctions
my_map.add_track("A", "B", 10)
my_map.add_track("B", "A", 10)  
my_map.add_track("B", "C", 15)
my_map.add_track("C", "B", 15)  

# Create trains and park them at junctions
my_map.add_train("1",5)
my_map.add_train("2",5)
my_map.add_train("3",8)
my_map.park_train_at_junction("1","A")
my_map.park_train_at_junction("2", "B")


print()
print("printing the map: ")
# Print the map's tracks and junctions
my_map.print_map()

print()
print()


# Create a new map with more junctions and tracks 
railway_map = Map()

# Add junctions
junction_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
for name in junction_names:
    railway_map.add_junction(name)

# Add tracks between junctions
tracks_info = [
    ('A', 'B', 3),  # Track from Junction A to B with length 100 
    ('B', 'C', 7),  # Track from Junction B to C with length 150 
    ('C', 'D', 120),  # Track from Junction C to D with length 120 
    ('D', 'E', 130),  # Track from Junction D to E with length 120 
    ('E', 'F', 80),   # Track from Junction E to F with length 120 
    ('F', 'G', 60),   # Track from Junction F to G with length 120 
    # Can add more tracks for testing
]
for start, end, length in tracks_info:
    railway_map.add_track(start, end, length)

# Create and place trains on tracks
train_counter = 1
for track_label in ['A->B', 'B->C', 'C->D', 'D->E', 'E->F', 'F->G']:  
    train_name = f"Train_{train_counter}"
    railway_map.add_train(train_name, 10) 
    railway_map.add_train_to_track(train_name, track_label)
    train_counter += 1

# park one of the trains at a junction
railway_map.park_train_at_junction("Train_1", "B")

# Print the current map state
railway_map.print_map()

railway_map.add_train("Express", 0.1)
# Define a route using junction objects from the map
route = [railway_map.junctions["A"], railway_map.junctions["B"], railway_map.junctions["C"]]
railway_map.trains["Express"].set_route(route)
railway_map.trains["Express"].set_speed(100)
railway_map.add_train_to_track("Express", "A->B") 
while (railway_map.trains["Express"].current_junction_index < len(route) - 1):
    railway_map.trains["Express"].move_along_route()
    time.sleep(2)
