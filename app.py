from flask import Flask, request
from time import time as now
import os
from trailrouter import find
from poi_enricher import *
from flask_cors import CORS, cross_origin
from math import floor

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'





# V2

AVERAGE_WALKING_SPEED = 4.8


@app.route("/v2/route", methods = ["POST"])
def route():
    params = request.json
    coords = params["coords"]
    total_time = params["total_time_min"]
    # speed = params["speed_kmph"]
    speed = AVERAGE_WALKING_SPEED
    fmt = params["fmt"] if "fmt" in params else "json"  # json|kml|gpx
    
    # calculations
    total_dist = floor(speed * (total_time / 60) * 1000)
    total_time_ms = total_time * 60 * 1000
    
    # ask
    routes = find(
        coords,
        target_distance=total_dist,
        output=fmt
    )
    
    if fmt != "json":
        return routes
    
    # json
    routes = routes["routes"]
    # select closest under total time
    selected = routes[0]
    for r in routes[1:]:
        if selected["duration"] < r["duration"] <= total_time_ms:
            selected = r
            
    return clean_route(selected)
    
            
    
def clean_route(r):
    return {
        "distance": r["distance"],
        "duration": r["duration"],
        "ascent": r["ascent"],
        "descent": r["descent"],
        "points": [conv_coord(c) for c in r["geometry"]["coordinates"]],
        # "waypoints": [conv_coord(c) for c in r["waypoints"]]
        # green score?
    }
    
def conv_coord(c):
    return {
        "lat": c[1],
        "long": c[0],
        "height": c[2],
    }




# V1





def coord_http_to_py(s):
    return (s["lat"], s["long"])
def coord_py_to_http(s):
    return {"lat": s[0], "long": s[1]}

@app.route("/test")
@cross_origin()
def test():
    return {
        "timestamp": now(),
        "msg": "yes, your request reached me"
    }
    
@app.route("/time", methods = ["POST"])
@cross_origin()
def time():
    inp = request.json
    coords = [coord_http_to_py(c) for c in inp["coords"]]
    
    result = find(coords, target_distance=1)    
    route = result["routes"][0]
    
    return {
        "time": round(route["duration"] / 1000 / 60)
    }
    
@app.route("/locate", methods = ["POST"])
@cross_origin()
def locate():
    inp = request.json
    attempt = inp["name"]
    return coord_py_to_http(geocode_place_name(attempt))

@app.route("/routefmt", methods = ["POST"])
@cross_origin()
def routefmt():
    inp = request.json
    coords = [coord_http_to_py(c) for c in inp["coords"]]
    total_time = inp["total_time"]
    fmt = inp["fmt"]  # json | gpx | kml
    
    return find(coords, total_time=total_time, output=fmt)
    
@app.route("/longroute", methods = ["POST"])
@cross_origin()
def longroute():
    inp = request.json
    coords = [coord_http_to_py(c) for c in inp["coords"]]
    total_time = inp["total_time"]
    AVERAGE_WALKING_SPEED = 4.8
    
    # Calculate target distance and ensure it's an integer
    target_distance_meters = int(AVERAGE_WALKING_SPEED * (total_time / 60) * 1000)
    
    try:
        enriched_data = enrich_routes_with_location_info(
            coords,
            target_distance=target_distance_meters,
            green_preference=1.0,     
            hills_preference=0.0,
            avoid_unsafe=True,
            avoid_unlit=True,
            avoid_repetition=True,
            roundtrip=False,
            search_radius_m=50
        )
        
        if enriched_data:
            return enriched_data  # Return the enriched route data as JSON
        else:
            return {"error": "Could not generate route"}, 400
            
    except Exception as e:
        print(f"Error in longroute: {e}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))