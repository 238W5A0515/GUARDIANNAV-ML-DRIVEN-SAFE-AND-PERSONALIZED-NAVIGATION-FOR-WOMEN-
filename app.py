from flask import Flask, render_template, request, jsonify
import folium
import pandas as pd
import os
from sklearn.cluster import KMeans
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import openrouteservice

# Initialize Flask app
app = Flask(__name__)

# Load dataset
data_folder = 'D:/PYTHON/dataset'  # Set your dataset folder path

# Load multiple CSV files and concatenate
all_files = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if f.endswith('.csv')]
crime_data = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)

# Filter crime data for relevant crimes
filtered_data = crime_data[crime_data['Crime type'] == 'Violence and sexual offences']
filtered_data = filtered_data.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)

# KMeans clustering
coordinates = filtered_data[['Latitude', 'Longitude']]
kmeans = KMeans(n_clusters=5, random_state=0)
filtered_data['Cluster'] = kmeans.fit_predict(coordinates)
cluster_centers = kmeans.cluster_centers_

# OpenRouteService client setup
ORS_API_KEY = '5b3ce3597851110001cf62488b8e1c3e264b4c7ea1ffa6209115e7a2'
client = openrouteservice.Client(key=ORS_API_KEY)

# Geolocator setup
geolocator = Nominatim(user_agent="safe-route-app")

def is_near_cluster(coord, clusters, crime_data, radius=0.5):
    for cluster in clusters:
        if geodesic((coord[1], coord[0]), cluster).km < radius:
            return True
    for _, crime in crime_data.iterrows():
        if geodesic((coord[1], coord[0]), (crime['Latitude'], crime['Longitude'])).km < radius:
            return True
    return False

def get_safe_route(start_coords, end_coords, clusters, crime_data, radius=0.5):
    try:
        route = client.directions(
            coordinates=[start_coords, end_coords],
            profile='driving-car',
            format='geojson'
        )
        route_coords = route['features'][0]['geometry']['coordinates']

        safe_route_coords = []
        for coord in route_coords:
            if not is_near_cluster(coord, clusters, crime_data, radius):
                safe_route_coords.append(coord)

        if not safe_route_coords:
            print("All waypoints are near high-risk zones. Returning the original route.")
            return route_coords
        
        return safe_route_coords
    except Exception as e:
        print("Error fetching route:", e)
        return []

@app.route('/geocode', methods=['POST'])
def geocode():
    data = request.get_json()
    try:
        location = geolocator.geocode(data['address'])
        if location:
            return jsonify({'lat': location.latitude, 'lon': location.longitude}), 200
        else:
            return jsonify({'error': 'Location not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    map_html = None
    if request.method == 'POST':
        start_lat = float(request.form['start_lat'])
        start_lon = float(request.form['start_lon'])
        end_lat = float(request.form['end_lat'])
        end_lon = float(request.form['end_lon'])

        start_coords = [start_lon, start_lat]
        end_coords = [end_lon, end_lat]

        safe_route_coords = get_safe_route(start_coords, end_coords, cluster_centers, filtered_data, radius=0.5)
        safe_route_coords_corrected = [[coord[1], coord[0]] for coord in safe_route_coords]

        route_map = folium.Map(location=[start_lat, start_lon], zoom_start=13)
        if safe_route_coords_corrected:
            folium.PolyLine(safe_route_coords_corrected, color="green", weight=5, opacity=0.7, tooltip="Safe Route").add_to(route_map)

        folium.Marker(location=[start_lat, start_lon], icon=folium.Icon(color='blue'), tooltip="Start Location").add_to(route_map)
        folium.Marker(location=[end_lat, end_lon], icon=folium.Icon(color='purple'), tooltip="End Location").add_to(route_map)

        for cluster in cluster_centers:
            folium.CircleMarker(
                location=[cluster[0], cluster[1]],
                radius=10,
                color="red",
                fill=True,
                fill_opacity=0.6,
                tooltip="High-Risk Area"
            ).add_to(route_map)

        for _, row in filtered_data.iterrows():
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=3,
                color="orange",
                fill=True,
                fill_opacity=0.5,
                tooltip="Crime Location"
            ).add_to(route_map)

        map_html = route_map._repr_html_()

    return render_template('index.html', map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)
