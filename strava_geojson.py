"""
Remi Salmon - salmon.remi@gmail.com - January 22, 2019

https://github.com/remisalmon/Strava-to-GeoJSON
"""

# imports
import glob
import gpxpy
import geojson

import numpy as np
import matplotlib.cm as cm

from scipy.signal import medfilt

# functions
def rgb2hex(c):
    hex = '#%02x%02x%02x'%(int(c[0]*255), int(c[1]*255), int(c[2]*255))

    return(hex)

def main(): # main script
    # parameters
    vis_data = 'speed' # 'none', 'elevation', 'slope', 'speed' or 'power'
    vis_medium = 'geojsonio' # 'raw', 'geojsonio' or 'umap'
    rider_weight = 160*0.45359237 # kg
    bike_weight = 32.6*0.45359237 # kg

    # constants
    vis_colormap = 'jet'
    rider_bike_frontal_area = 0.632 # m^2 (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    rider_bike_drag_coeff = 1.15 # unitless (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    bike_drivetrain_loss = 7 # % (from https://en.wikipedia.org/wiki/Bicycle_performance#Mechanical_efficiency)
    bike_rr_coeff = 0.006 # unitless (from https://en.wikipedia.org/wiki/Bicycle_performance#Rolling_resistance)
    air_density = 1.225 # kg/m^3
    g = 9.80665 # m/s^2

    # find and read GPX file
    gpx_file = glob.glob('*.gpx')[0] # read only 1 GPX file

    if not gpx_file:
        print('ERROR: no GPX file')
        quit()

    lat_lon_data = []
    elevation_data = []
    timestamp_data = []

    with open(gpx_file, 'r') as file:
        gpx = gpxpy.parse(file)

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lat_lon_data.append([point.latitude, point.longitude])

                    elevation_data.append(point.elevation)

                    timestamp_data.append(point.time.timestamp())

    # convert to NumPy arrays
    lat_lon_data = np.array(lat_lon_data)  # [deg, deg]
    elevation_data = np.array(elevation_data) # [m]
    timestamp_data = np.array(timestamp_data) # [sec]

    # calculate trackpoints distance, slope, speed and power
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

        slope_data[i] = delta_elevation/distance_data[i]

        distance_data[i] = np.sqrt(np.power(distance_data[i], 2)+np.power(delta_elevation, 2)) # recalculate distance to take slope into account

    speed_data = np.zeros(timestamp_data.shape) # [m/s]

    for i in np.arange(1, timestamp_data.shape[0]):
        if timestamp_data[i] != timestamp_data[i-1]:
            speed_data[i] = distance_data[i]/(timestamp_data[i]-timestamp_data[i-1])
        else:
            speed_data[i] = 0

    # filter speed and slope data (default Strava filters)
    slope_data = medfilt(slope_data, 5)
    speed_data = medfilt(speed_data, 5)

    power_data = np.zeros(timestamp_data.shape) # [watt]

    for i in np.arange(1, timestamp_data.shape[0]):
        speed = speed_data[i]
        slope = slope_data[i]

        power = (1/(1-bike_drivetrain_loss/100))*(g*(rider_weight+bike_weight)*(np.sin(np.arctan(slope))+bike_rr_coeff*np.cos(np.arctan(slope)))+(0.5*rider_bike_drag_coeff*rider_bike_frontal_area*air_density*np.power(speed, 2)))*speed

        if power > 0:
            power_data[i] = power

    # normalize data for visualization
    elevation_data_norm = (elevation_data-elevation_data.min())/(elevation_data.max()-elevation_data.min())
    slope_data_norm = (slope_data-slope_data.min())/(slope_data.max()-slope_data.min())
    speed_data_norm = (speed_data-speed_data.min())/(speed_data.max()-speed_data.min())
    power_data_norm = (power_data-power_data.min())/(power_data.max()-power_data.min())

    # create GeoJSON feature collection
    features = []
    cmap = cm.get_cmap(vis_colormap)

    for i in np.arange(1, timestamp_data.shape[0]):
        line = geojson.LineString([(lat_lon_data[i-1, 1], lat_lon_data[i-1, 0]), (lat_lon_data[i, 1], lat_lon_data[i, 0])])

        if vis_data == 'none':
            color = '#FC4C02'
        elif vis_data == 'elevation':
            color = rgb2hex(cmap(elevation_data_norm[i]))
        elif vis_data == 'slope':
            color = rgb2hex(cmap(slope_data_norm[i]))
        elif vis_data == 'speed':
            color = rgb2hex(cmap(speed_data_norm[i]))
        elif vis_data == 'power':
            color = rgb2hex(cmap(power_data_norm[i]))

        if vis_medium == 'raw':
            feature = geojson.Feature(geometry = line, properties = {"elevation (m)": "%.1f" % elevation_data[i], "slope (%)": "%.1f" % (slope_data[i]*100), "speed (mph)": "%.1f" % (speed_data[i]*2.236936), "power (watt)": "%.1f" % power_data[i]}) # export all data
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
