from flask import Flask, request
from time import time as now
import os
from trailrouter import find
from poi_enricher import *

app = Flask(__name__)

def coord_http_to_py(s):
    return (s["lat"], s["long"])
def coord_py_to_http(s):
    return {"lat": s[0], "long": s[1]}

@app.route("/test")
def test():
    return {
        "timestamp": now(),
        "msg": "yes, your request reached me"
    }
    
@app.route("/time", methods = ["POST"])
def time():
    inp = request.json
    start = coord_http_to_py(inp["start"])
    end = coord_http_to_py(inp["end"])
    
    result = find([start, end], target_distance=1)    
    route = result["routes"][0]
    
    return {
        "time": round(route["duration"] / 1000 / 60)
    }
    
@app.route("/locate", methods = ["POST"])
def locate():
    inp = request.json
    attempt = inp["name"]
    return coord_py_to_http(geocode_place_name(attempt))

@app.route("/routefmt", methods = ["POST"])
def routefmt():
    inp = request.json
    start = coord_http_to_py(inp["start"])
    end = coord_http_to_py(inp["end"])
    fmt = inp["fmt"]  # json | gpx | kml
    
    return find([start, end], output=fmt)
    
@app.route("/longroute", methods = ["POST"])
def longroute():
    inp = request.json
    start = coord_http_to_py(inp["start"])
    end = coord_http_to_py(inp["end"])
    total_time = inp["total_time"]
    AVERAGE_WALKING_SPEED = 4.8
    
    # Calculate target distance and ensure it's an integer
    target_distance_meters = int(AVERAGE_WALKING_SPEED * (total_time / 60) * 1000)
    
    try:
        enriched_data = enrich_routes_with_location_info(
            [start, end],
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