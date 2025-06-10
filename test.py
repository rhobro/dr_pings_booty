import googlemaps as maps
from polyline import decode
import json

KEY = "AIzaSyB1Mhqz0NlzTycRp0tTfQIJoexp9_rWQiA"
START = (51.49142612816029, -0.20781661388698155)
END = (51.49935665314372, -0.17955355472110562)
COMBO = (START, END)

def coord_to_gm(coord):
    return f"{coord[0]},{coord[1]}"

cli = maps.Client(key=KEY)

output = cli.directions(coord_to_gm(START), coord_to_gm(END), mode="transit")
with open("gm.json", "w") as f:
    f.write(json.dumps(output, indent=4))
route = output[0]
decoded_poly = decode(route["overview_polyline"]["points"], precision=6)

leg = route["legs"][0]

steps = leg["steps"]


def full_points(s):
    start = (s["start_location"]["lat"], s["start_location"]["lng"])
    end = (s["end_location"]["lat"], s["end_location"]["lng"])
    points = decode(s["polyline"]["points"])
    points.insert(0, start)
    points.append(end)
    
    return points

class Start:
    pass

class Walk:
    def __init__(self, raw):
        self.distance = s["distance"]["value"]
        self.duration = s["duration"]["value"]
        self.points = full_points(s)
        
    def append(self, other):
        self.distance += other.distance
        self.duration += other.duration
        self.points.extend(other.points)
        
class Transit:
    def __init__(self, raw):
        self.type = raw["transit_details"]["line"]["vehicle"]["type"]
        self.distance = raw["distance"]["value"]
        self.duration = raw["duration"]["value"]
        self.points = full_points(raw)
        self.line = raw["transit_details"]["line"]["name"]
        self.start_name = raw["transit_details"]["departure_stop"]["name"]
        self.end_name = raw["transit_details"]["arrival_stop"]["name"]
    
    def append(self, other):
        self.distance += other.distance
        self.duration += other.duration
        self.points.extend(other.points)
        


# summarise 
newsteps = [Start()]

for s in steps:    
    if s["travel_mode"] == "WALKING":
        s = Walk(s)
        
        if type(newsteps[-1]) == Walk:
            newsteps[-1].append(s)
        else:
            newsteps.append(s)
            
    elif s["travel_mode"] == "TRANSIT":
        s = Transit(s)
        
        if type(newsteps[-1]) == Transit and newsteps[-1].type == s.type:
            newsteps[-1].append(s)
        else:
            newtypes.append(s)
