# Copyright (c) 2019 Remi Salmon
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# imports
import argparse
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

def main(args): # main script
    # parameters
    gpx_filename = args.gpxfile
    geojson_filename = args.geojsonfile
    vis_data = 'none' if args.alldata else args.data # 'track', 'elevation', 'slope', 'speed', 'power' or 'none'
    vis_website = args.website # 'geojsonio' or 'umap'
    rider_weight = args.riderweight*0.45359237 # lbs to kg
    bike_weight = args.bikeweight*0.45359237 # lbs to kg

    if not gpx_filename[-4:] == '.gpx':
        print('ERROR: not a GPX input file')
        quit()

    if not geojson_filename[-8:] == '.geojson' and not geojson_filename == '':
        print('ERROR: not a GeoJSON output file')
        quit()

    if rider_weight <= 0 or bike_weight <= 0:
        if vis_data == 'power':
            print('ERROR: --rider-weight and --bike_weight must be specified to visualize power')
            quit()
        else:
            get_power_data = False
    else:
        get_power_data = True

    # constants
    vis_colormap = 'jet'
    rider_bike_frontal_area = 0.632 # m^2 (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    rider_bike_drag_coeff = 1.15 # unitless (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    bike_drivetrain_loss = 7 # % (from https://en.wikipedia.org/wiki/Bicycle_performance#Mechanical_efficiency)
    bike_rr_coeff = 0.006 # unitless (from https://en.wikipedia.org/wiki/Bicycle_performance#Rolling_resistance)
    air_density = 1.225 # kg/m^3
    g = 9.80665 # m/s^2

    # find and read the GPX file
    gpx_file = glob.glob(gpx_filename)[0] # read only 1 file

    if not gpx_file:
        print('ERROR: no GPX file found')
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

        a = np.power(np.sin(delta_lat/2.0), 2)+np.cos(lat1)*np.cos(lat2)*np.power(np.sin(delta_lon/2.0), 2)
        c = 2.0*np.arctan2(np.sqrt(a), np.sqrt(1.0-a))

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

    if get_power_data:
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
    if get_power_data:
        power_data_norm = (power_data-power_data.min())/(power_data.max()-power_data.min())

    # create GeoJSON feature collection
    features = []
    cmap = cm.get_cmap(vis_colormap)

    for i in np.arange(1, timestamp_data.shape[0]):
        line = geojson.LineString([(lat_lon_data[i-1, 1], lat_lon_data[i-1, 0]), (lat_lon_data[i, 1], lat_lon_data[i, 0])]) # (lon,lat) to (lon,lat) format

        if vis_data == 'track': # show some color...
            color = '#FC4C02'
        elif vis_data == 'elevation':
            color = rgb2hex(cmap(elevation_data_norm[i]))
        elif vis_data == 'slope':
            color = rgb2hex(cmap(slope_data_norm[i]))
        elif vis_data == 'speed':
            color = rgb2hex(cmap(speed_data_norm[i]))
        elif vis_data == 'power':
            color = rgb2hex(cmap(power_data_norm[i]))

        if vis_data == 'none': # dump all data
            if get_power_data:
                feature = geojson.Feature(geometry = line, properties = {"elevation (m)": "%.1f"%elevation_data[i], "slope (%)": "%.1f"%(slope_data[i]*100), "speed (mph)": "%.1f"%(speed_data[i]*2.236936), "power (watt)": "%.1f"%power_data[i]}) # export all data
            else:
                feature = geojson.Feature(geometry = line, properties = {"elevation (m)": "%.1f"%elevation_data[i], "slope (%)": "%.1f"%(slope_data[i]*100), "speed (mph)": "%.1f"%(speed_data[i]*2.236936)}) # export all data
        elif vis_website == 'geojsonio':
            feature = geojson.Feature(geometry = line, properties = {"stroke": color, "stroke-width": 5}) # export color for geojson.io
        elif vis_website == 'umap':
            feature = geojson.Feature(properties = {"_umap_options": {"color": color, "weight": 5, "opacity": 1}}, geometry = line) # export color for umap.openstreetmap.fr

        features.append(feature)

    feature_collection = geojson.FeatureCollection(features)

    # write GeoJSON file
    geojson_file = geojson_filename if geojson_filename else gpx_file[:-4]+'.geojson' # use GPX filename if not specified

    with open(geojson_file, 'w') as file:
        geojson.dump(feature_collection, file)

if __name__ == '__main__':
    # command line parameters
    parser = argparse.ArgumentParser(description = 'Extract (speed, power, elevation, slope) data from Strava GPX files and export to GeoJSON ', epilog = 'Report issues to https://github.com/remisalmon/Strava-to-GeoJSON')
    parser.add_argument('--input', dest = 'gpxfile', default = '*.gpx', help = 'input .gpx file')
    parser.add_argument('--output', dest = 'geojsonfile', default = '', help = 'output .geojson file')
    parser.add_argument('--vis-data', dest = 'data', default = 'track', help = 'data to visualize on the color-coded GeoJSON file: track, elevation, slope, speed, power (default: track)')
    parser.add_argument('--vis-website', dest = 'website', default = 'geojsonio', help = 'platform to visualize the color-coded GeoJSON file: geojsonio or umap (default: geojsonio)')
    parser.add_argument('--all-data', dest = 'alldata', action = 'store_true', help = 'export all data to the GeoJSON file (disregards --vis-data)')
    parser.add_argument('--rider-weight', dest = 'riderweight', type = float, default = 0, help = 'rider weight for power calculation, in lbs (default: 0)')
    parser.add_argument('--bike-weight', dest = 'bikeweight', type = float, default = 0, help = 'bike weight for power calculation, in lbs (default: 0)')
    args = parser.parse_args()

    main(args)
