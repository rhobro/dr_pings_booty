import requests as rq
import json


def find(
    route,
    green_preference=0.0,
    target_distance=0.0,
    hills_preference=0.0,
    avoid_unsafe=False,
    avoid_unlit=False,
    avoid_repetition=False,
    roundtrip=False,
    output="json"
):
    """Implementing very original algorithms here.

    Args:
        route ([(lat, long)]): List of key points in route.
        green_preference (float, optional): Prefer green areas in route. Defaults to 0.0.
        target_distance (float, optional): Target total distance for route. Defaults to 0.0.
        hills_preference (float, optional): Including steep hills? Defaults to 0.0.
        avoid_unsafe (bool, optional): Avoiding unsafe streets. Defaults to False.
        avoid_unlit (bool, optional): Avoiding unlit streets. Defaults to False.
        avoid_repetition (bool, optional): Avoid repeating the same roads. Defaults to False.
        roundtrip (bool, optional): Route to return to start. Defaults to False.
        output (str, optional): Format in "json", "gpx" or "kml". Defaults to "json".

    Returns:
        str: resulting file content
    """

    endpoint = "https://trailrouter.com/ors/experimentalroutes"
    query = {
        "coordinates": "|".join([f"{c['long']},{c['lat']}" for c in route]),
        # "skip_segments": None, TODO impl
        "green_preference": green_preference,
        "avoid_unsafe_streets": avoid_unsafe,
        "avoid_unlit_streets": avoid_unlit,
        "hills_preference": hills_preference,
        "avoid_repetition": avoid_repetition,
        "roundtrip": roundtrip,
        "output": output
    }

    if target_distance > 0:
        current_target_distance = int(target_distance) # Explicitly cast to int
        print(f"TrailRouter: target_distance type before API call: {type(current_target_distance)}, value: {current_target_distance}")
        query["target_distance"] = current_target_distance

    rsp = rq.get(endpoint, params=query)
    
    # Print the actual URL that was requested for debugging
    print(f"TrailRouter API Request URL: {rsp.request.url}")

    if output in ["gpx", "kml"]:
        return rsp.text
    return rsp.json()


route = [
    {"lat": 51.5225787916085, "long": -0.2584538182768499},
    {"lat": 51.49052175066264, "long": -0.2063941502918089},
    {"lat": 51.49902674764006, "long": -0.17958657749433424},
    {"lat": 51.4988469085482, "long": -0.13938348407508253}
]
with open("test.json", "w") as f:
    f.write(json.dumps(find(route, 1, 25000, 1, True, True, True, False, "json"), indent=4))
