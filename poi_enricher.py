import requests
import json
import time
from typing import List, Dict, Any, Optional, Union

# Import the find function from trailrouter
from trailrouter import find

# Define significant POI types for popularity assessment with priority levels
# Higher priority types will be preferred when multiple POIs are found
SIGNIFICANT_POI_TYPES = {
    'public_transport': ['station', 'stop_position', 'platform'],  # HIGH PRIORITY
    'railway': ['station', 'halt', 'tram_stop'],  # HIGH PRIORITY  
    'amenity': ['bus_station', 'ferry_terminal'],  # HIGH PRIORITY
    'tourism': ['museum', 'gallery', 'attraction', 'artwork', 'viewpoint'],
    'historic': ['castle', 'monument', 'memorial', 'archaeological_site', 'ruins'],
    'amenity_other': ['place_of_worship', 'theatre', 'cinema', 'library', 'university', 'college', 'hospital',
                     'restaurant', 'cafe', 'pub', 'bar', 'fast_food', 'townhall'],
    'shop': ['supermarket', 'department_store', 'mall'],
    'leisure': ['park', 'garden', 'stadium', 'sports_centre', 'nature_reserve', 'marina', 'beach']
}

# High priority categories (transport-related)
HIGH_PRIORITY_CATEGORIES = ['public_transport', 'railway', 'amenity']

def geocode_place_name(place_name: str) -> Optional[tuple]:
    """Convert a place name to coordinates using Nominatim."""
    nominatim_url = "https://nominatim.openstreetmap.org/search"
    params = {
        'format': 'jsonv2',
        'q': place_name,
        'limit': 1,
        'addressdetails': 1
    }
    headers = {
        'User-Agent': 'DRPingRouteEnricher/1.0 (https://github.com/yourrepo/yourproject)'
    }
    
    try:
        time.sleep(1.1)  # Nominatim rate limit
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        results = response.json()
        
        if results:
            result = results[0]
            lat, lon = float(result['lat']), float(result['lon'])
            print(f"Geocoded '{place_name}' to ({lat:.5f}, {lon:.5f})")
            return (lat, lon)
        else:
            print(f"Could not geocode '{place_name}'")
            return None
            
    except Exception as e:
        print(f"Geocoding error for '{place_name}': {e}")
        return None

def is_poi_popular(poi_tags: Dict[str, str]) -> tuple[bool, int]:
    """
    Checks if a POI is considered popular and returns priority level.
    Returns (is_popular, priority) where lower priority number = higher priority
    """
    if not poi_tags.get('name'):
        return False, 999
    
    # Check for wikipedia/wikidata (medium priority)
    if poi_tags.get('wikipedia') or poi_tags.get('wikidata'):
        return True, 50
    
    # Check transport-related tags first (high priority)
    transport_tags = ['public_transport', 'railway', 'bus', 'highway']
    for tag in transport_tags:
        if tag in poi_tags:
            if tag == 'highway' and poi_tags[tag] == 'bus_stop':
                return True, 1  # Bus stops highest priority
            elif tag == 'railway' and poi_tags[tag] in ['station', 'halt', 'tram_stop']:
                return True, 1  # Railway stations very high priority
            elif tag == 'public_transport':
                return True, 2  # Other public transport high priority
    
    # Check amenity for transport
    if poi_tags.get('amenity') in ['bus_station', 'ferry_terminal']:
        return True, 5
    
    # Check other significant types
    for category, types in SIGNIFICANT_POI_TYPES.items():
        if category in HIGH_PRIORITY_CATEGORIES:
            continue  # Already handled above
        
        for key in poi_tags:
            if key == category and poi_tags[key] in types:
                if category == 'tourism':
                    return True, 20
                elif category == 'historic':
                    return True, 25
                else:
                    return True, 30
    
    return False, 999

def get_road_name_from_nominatim(lat: float, lon: float) -> Optional[str]:
    """Fetches road name for a given lat/lon using Nominatim reverse geocoding."""
    nominatim_url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'format': 'jsonv2',
        'lat': lat,
        'lon': lon,
        'zoom': 18
    }
    headers = {
        'User-Agent': 'DRPingRouteEnricher/1.0 (https://github.com/yourrepo/yourproject)'
    }
    try:
        time.sleep(1.1)
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        address_data = response.json()
        
        # Try to extract road name from various possible fields
        address = address_data.get('address', {})
        road = (address.get('road') or address.get('pedestrian') or 
                address.get('footway') or address.get('path'))
        
        if not road:
            # Fallback to display name parsing
            display_name_parts = address_data.get('display_name', '').split(',')
            if len(display_name_parts) > 0:
                potential_road = display_name_parts[0].strip()
                # Avoid house numbers or very short names
                if len(potential_road) > 3 and not potential_road.isdigit():
                    road = potential_road

        return road
    except Exception as e:
        print(f"Nominatim API error for {lat}, {lon}: {e}")
        return None

def get_nearby_location_info(lat: float, lon: float, radius: int = 50) -> Dict[str, Any]:
    """
    Get popular POIs or road name near a coordinate with better distance filtering.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # More targeted query focusing on transport and significant POIs
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius},{lat},{lon})["public_transport"];
      node(around:{radius},{lat},{lon})["railway"];
      node(around:{radius},{lat},{lon})["highway"="bus_stop"];
      node(around:{radius},{lat},{lon})["amenity"~"^(bus_station|ferry_terminal)$"];
      node(around:{radius},{lat},{lon})["name"]["tourism"];
      node(around:{radius},{lat},{lon})["name"]["historic"];
      node(around:{radius},{lat},{lon})["name"]["amenity"~"^(place_of_worship|theatre|cinema|library|university|college|hospital|restaurant|cafe|pub|bar)$"];
      way(around:{radius},{lat},{lon})["public_transport"];
      way(around:{radius},{lat},{lon})["railway"];
      way(around:{radius},{lat},{lon})["name"]["tourism"];
      way(around:{radius},{lat},{lon})["name"]["historic"];
    );
    out center meta;
    """
    
    popular_pois_found = []
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        processed_poi_ids = set()

        for element in data.get('elements', []):
            if element['id'] in processed_poi_ids:
                continue

            tags = element.get('tags', {})
            poi_name = tags.get('name')

            if not poi_name or poi_name.lower() == 'unnamed':
                continue
            
            is_popular, priority = is_poi_popular(tags)
            if is_popular:
                # Get coordinates
                if element['type'] == 'way' and 'center' in element:
                    poi_el_lat, poi_el_lon = element['center']['lat'], element['center']['lon']
                elif element['type'] == 'relation' and 'center' in element:
                    poi_el_lat, poi_el_lon = element['center']['lat'], element['center']['lon']
                elif element['type'] == 'node':
                    poi_el_lat, poi_el_lon = element.get('lat'), element.get('lon')
                else:
                    continue 
            
                if not poi_el_lat or not poi_el_lon:
                    continue
                    
                # Calculate accurate distance in meters
                from math import radians, cos, sin, asin, sqrt
                def haversine_distance(lat1, lon1, lat2, lon2):
                    # Convert to radians
                    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                    # Haversine formula
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    return 2 * asin(sqrt(a)) * 6371000  # Earth radius in meters
                
                distance = haversine_distance(lat, lon, poi_el_lat, poi_el_lon)
                
                # Skip if actually too far (double-check distance)
                if distance > radius * 1.5:  # Allow some margin but not too much
                    continue
                
                # Determine primary type for display
                primary_type = 'other_popular_place'
                if tags.get('highway') == 'bus_stop':
                    primary_type = 'bus_stop'
                elif tags.get('railway') in ['station', 'halt', 'tram_stop']:
                    primary_type = f"railway_{tags.get('railway')}"
                elif tags.get('public_transport'):
                    primary_type = f"public_transport_{tags.get('public_transport')}"
                elif tags.get('amenity') in ['bus_station', 'ferry_terminal']:
                    primary_type = tags.get('amenity')
                else:
                    # Fallback to other categories
                    for cat, types in SIGNIFICANT_POI_TYPES.items():
                        if cat in tags and tags[cat] in types:
                            primary_type = tags[cat]
                            break
                    if primary_type == 'other_popular_place':
                        primary_type = (tags.get('amenity') or tags.get('shop') or 
                                      tags.get('tourism') or tags.get('leisure') or 
                                      tags.get('historic') or primary_type)

                popular_pois_found.append({
                    'name': poi_name,
                    'type': primary_type,
                    'distance_m': round(distance, 1),
                    'priority': priority,
                    'coordinates': [poi_el_lon, poi_el_lat]
                })
                processed_poi_ids.add(element['id'])
        
        # Sort by priority first (lower number = higher priority), then by distance
        popular_pois_found.sort(key=lambda x: (x['priority'], x['distance_m']))
        popular_pois_found = popular_pois_found[:5]

    except Exception as e:
        print(f"Overpass API error for {lat}, {lon}: {e}")

    if popular_pois_found:
        # Remove priority from output
        for poi in popular_pois_found:
            del poi['priority']
        return {"pois": popular_pois_found, "road_name": None}
    else:
        print(f"No popular POIs near ({lat:.5f}, {lon:.5f}). Fetching road name...")
        road_name = get_road_name_from_nominatim(lat, lon)
        return {"pois": [], "road_name": road_name}

def enrich_routes_with_location_info(
    route_locations: List[Union[tuple, str]],  # Can be coordinates or place names
    output_file_path: str = "test_enriched.json",
    green_preference=0.0,
    target_distance=0.0,
    hills_preference=0.0,
    avoid_unsafe=False,
    avoid_unlit=False,
    avoid_repetition=False,
    roundtrip=False,
    search_radius_m: int = 50  # Reduced default radius
):
    """
    Generates routes, enriches with popular POIs or road names, saves simplified output.
    Accepts either coordinates (lat, lon) or place names as strings.
    """
    
    # Convert place names to coordinates if needed
    route_coordinates = []
    for location in route_locations:
        if isinstance(location, str):
            coords = geocode_place_name(location)
            if coords:
                route_coordinates.append(coords)
            else:
                print(f"Skipping location '{location}' - could not geocode")
                continue
        elif isinstance(location, tuple) and len(location) == 2:
            route_coordinates.append(location)
        else:
            print(f"Invalid location format: {location}")
            continue
    
    if len(route_coordinates) < 2:
        print("Need at least 2 valid locations to generate routes")
        return
    
    print(f"Generating routes via 'find' function with {len(route_coordinates)} waypoints...")
    try:
        route_data = find(
            route_coordinates,
            green_preference=green_preference, target_distance=target_distance,
            hills_preference=hills_preference, avoid_unsafe=avoid_unsafe,
            avoid_unlit=avoid_unlit, avoid_repetition=avoid_repetition,
            roundtrip=roundtrip, output="json"
        )
    except Exception as e:
        print(f"Error calling 'find' function: {e}")
        return

    if not route_data or 'routes' not in route_data:
        print("No routes found or data from 'find' is not in expected format.")
        return

    # Save raw route data to test.json (like trailrouter.py does)
    with open("test.json", 'w') as f:
        json.dump(route_data, f, indent=4)
    print("Saved raw route data to 'test.json'")

    final_routes_output = []
    overall_summary_lines = []

    for route_idx, original_route_info in enumerate(route_data.get('routes', [])):
        print(f"\nProcessing route {route_idx + 1}...")
        
        original_waypoints = original_route_info.get('waypoints', [])
        enriched_waypoints_for_this_route = []
        route_summary = [f"Route {route_idx + 1} Summary:"]

        for wp_idx, waypoint_coords in enumerate(original_waypoints):
            if len(waypoint_coords) >= 2:
                lon, lat = waypoint_coords[0], waypoint_coords[1]
                
                location_info = get_nearby_location_info(lat, lon, radius=search_radius_m)
                
                current_wp_output = {
                    'coordinates': waypoint_coords,
                    'nearby_pois': location_info['pois']
                }
                if location_info['road_name']:
                    current_wp_output['road_name'] = location_info['road_name']
                
                enriched_waypoints_for_this_route.append(current_wp_output)

                # Summary for console
                wp_summary_line = f"  WP {wp_idx+1} ({lat:.4f}, {lon:.4f}): "
                if location_info['pois']:
                    closest_poi = location_info['pois'][0]
                    wp_summary_line += f"{closest_poi['name']} ({closest_poi['type']}, {closest_poi['distance_m']}m)"
                elif location_info['road_name']:
                    wp_summary_line += f"Road: {location_info['road_name']}"
                else:
                    wp_summary_line += "No popular POIs or road name found."
                route_summary.append(wp_summary_line)
            
        final_routes_output.append({"enriched_waypoints": enriched_waypoints_for_this_route})
        overall_summary_lines.extend(route_summary)
    
    print("\n--- Location Info Summary ---")
    for line in overall_summary_lines:
        print(line)

    simplified_output_data = {"routes": final_routes_output}

    with open(output_file_path, 'w') as f:
        json.dump(simplified_output_data, f, indent=4)
    
    print(f"\nEnriched {len(route_data.get('routes', []))} routes and saved to '{output_file_path}'!")


if __name__ == "__main__":
    # Example with place names instead of coordinates
    route_locations = [
        "Imperial College London",  # Southeast London
        "North Acton, Ealing, London"  # West London
    ]
    
    # Or you can still use coordinates:
    # route_locations = [
    #     (51.50153282861582, -0.1920009708586527),
    #     (51.50921128409687, -0.19532925685234137)
    # ]
    
    enrich_routes_with_location_info(
        route_locations=route_locations,
        output_file_path="test_enriched.json",
        target_distance=20000, green_preference=1.0, hills_preference=1.0,
        avoid_unsafe=True, avoid_unlit=True, avoid_repetition=True,
        roundtrip=False,
        search_radius_m=40  # Smaller radius for more relevant results
    ) 