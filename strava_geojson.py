"""
Remi Salmon - salmon.remi@gmail.com - January 22, 2019

https://github.com/remisalmon/Strava-to-GeoJSON
"""

# imports
import glob
import re
import datetime
import geojson

import numpy as np
import matplotlib.cm as cm

from scipy.signal import medfilt
from matplotlib.colors import to_hex

# functions
def main(): # main script
    # parameters
    vis_colormap = 'jet'
    vis_data = 'speed' # 'none', 'elevation', 'slope' or 'speed'
    vis_medium = 'geojsonio' # 'raw', 'geojsonio' or 'umap'

    # find and read GPX file
    gpx_file = glob.glob('*.gpx')[0]

    if not gpx_file:
        print('ERROR: no GPX file')
        quit()

    lat_lon_data = []
    elevation_data = []
    timestamp_data = []

    gpx_read_time = False # don't read the first timestamp

    with open(gpx_file, 'r') as file:
        for line in file:
            if '<trkpt' in line: # get trackpoints latitude, longitude
                tmp = re.findall('-?\d*\.?\d+', line)

                lat = float(tmp[0])
                lon = float(tmp[1])

                lat_lon_data.append([lat, lon])

            elif '<ele' in line: # get trackpoints elevation
                tmp = re.findall('\d+\.\d+', line)

                elevation = float(tmp[0])

                elevation_data.append(elevation)

            elif '<time' in line: # get trackpoints timestamp
                tmp = re.findall('\d+.*Z', line)

                tmp = datetime.datetime.strptime(tmp[0], '%Y-%m-%dT%H:%M:%SZ') # convert string to datetime object

                timestamp = tmp.timestamp()

                if gpx_read_time:
                    timestamp_data.append(timestamp)
                else:
                    gpx_read_time = True

    # convert to NumPy arrays
    lat_lon_data = np.array(lat_lon_data)  # [deg, deg]
    elevation_data = np.array(elevation_data) # [m]
    timestamp_data = np.array(timestamp_data) # [sec]

    # calculate trackpoints distance, slope and speed
    distance_data = np.zeros(timestamp_data.shape) # [m]
    slope_data = np.zeros(timestamp_data.shape) # [%]

    for i in np.arange(1, timestamp_data.shape[0]):
        lat1 = np.radians(lat_lon_data[i-1, 0])
        lat2 = np.radians(lat_lon_data[i, 0])
        lon1 = np.radians(lat_lon_data[i-1, 1])
        lon2 = np.radians(lat_lon_data[i, 1])

        delta_lat = abs(lat2-lat1)
        delta_lon = abs(lon2-lon1)

        a = np.power(np.sin(delta_lat/2), 2)+np.cos(lat1)*np.cos(lat2)*np.power(np.sin(delta_lon/2), 2)
        c = 2.0*np.arctan2(np.sqrt(a), np.sqrt(1-a))

        distance_data[i] = 6371e3*c # haversine formula

        delta_elevation = elevation_data[i]-elevation_data[i-1]

        slope_data[i] = 100*(delta_elevation/distance_data[i])

        distance_data[i] = np.sqrt(np.power(distance_data[i], 2)+np.power(delta_elevation, 2)) # recalculate distance to take into account the slope

    speed_data = np.zeros(timestamp_data.shape) # [mph]

    for i in np.arange(1, timestamp_data.shape[0]):
        if timestamp_data[i] != timestamp_data[i-1]:
            speed = distance_data[i]/(timestamp_data[i]-timestamp_data[i-1])

            speed_data[i] = speed*2.236936 # convert m/s to mph
        else:
            speed_data[i] = 0

    # filter speed and slope data (default Strava filters)
    slope_data = medfilt(slope_data, 5)
    speed_data = medfilt(speed_data, 5)

    # normalize data for visualization
    elevation_data_norm = (elevation_data-elevation_data.min())/(elevation_data.max()-elevation_data.min())
    slope_data_norm = (slope_data-slope_data.min())/(slope_data.max()-slope_data.min())
    speed_data_norm = (speed_data-speed_data.min())/(speed_data.max()-speed_data.min())

    # create GeoJSON feature collection
    features = []
    cmap = cm.get_cmap(vis_colormap)

    for i in np.arange(1, timestamp_data.shape[0]):
        line = geojson.LineString([(lat_lon_data[i-1, 1], lat_lon_data[i-1, 0]), (lat_lon_data[i, 1], lat_lon_data[i, 0])])

        if vis_data == 'none':
            color = '#FC4C02'
        elif vis_data == 'elevation':
            color = to_hex(cmap(elevation_data_norm[i]))
        elif vis_data == 'slope':
            color = to_hex(cmap(slope_data_norm[i]))
        elif vis_data == 'speed':
            color = to_hex(cmap(speed_data_norm[i]))

        if vis_medium == 'raw':
            feature = geojson.Feature(geometry = line, properties = {"elevation (m)": str(elevation_data[i]), "slope (%)": str(slope_data[i]), "speed (mph)": str(speed_data[i])}) # export all data
        elif vis_medium == 'geojsonio':
            feature = geojson.Feature(geometry = line, properties = {"stroke": color, "stroke-width": 5}) # export color for geojson.io
        elif vis_medium == 'umap':
            feature = geojson.Feature(properties = {"_umap_options": {"color": color, "weight": 5, "opacity": 1}}, geometry = line) # export color for umap.openstreetmap.fr

        features.append(feature)

    feature_collection = geojson.FeatureCollection(features)

    # write GeoJSON file
    geojson_file = gpx_file[:-4]+'.geojson'

    with open(geojson_file, 'w') as file:
        geojson.dump(feature_collection, file)

if __name__ == '__main__':
    main()
