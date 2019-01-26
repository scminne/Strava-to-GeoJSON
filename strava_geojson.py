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
import folium
import webbrowser

import numpy as np
import matplotlib.cm as cm

from scipy.signal import medfilt

# functions
def rgb2hex(c):
    hex = '#%02x%02x%02x'%(int(c[0]*255), int(c[1]*255), int(c[2]*255))
    return(hex)

def gpx2geojson(gpx_file, geojson_file, param):
    # parameters
    rider_weight = param[0] # kg
    bike_weight =param[1] # kg

    # constants
    rider_bike_frontal_area = 0.632 # m^2 (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    rider_bike_drag_coeff = 1.15 # unitless (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    bike_drivetrain_loss = 7/100 # % (from https://en.wikipedia.org/wiki/Bicycle_performance#Mechanical_efficiency)
    bike_rr_coeff = 0.006 # unitless (from https://en.wikipedia.org/wiki/Bicycle_performance#Rolling_resistance)
    air_density = 1.225 # kg/m^3
    g = 9.80665 # m/s^2

    if rider_weight <= 0 or bike_weight <= 0:
        get_power_data = False
    else:
        get_power_data = True

    # initialize lists
    lat_lon_data = []
    elevation_data = []
    timestamp_data = []

    # read GPX file
    with open(gpx_file, 'r') as file:
        gpx = gpxpy.parse(file)

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lat_lon_data.append([point.latitude, point.longitude])

                    elevation_data.append(point.elevation)

                    timestamp_data.append(point.time.timestamp()) # convert time to timestamps (s)

    # convert to NumPy arrays
    lat_lon_data = np.array(lat_lon_data)  # [deg, deg]
    elevation_data = np.array(elevation_data) # [m]
    timestamp_data = np.array(timestamp_data) # [s]

    # calculate trackpoints distance, slope, speed and power
    distance_data = np.zeros(timestamp_data.shape) # [m]
    slope_data = np.zeros(timestamp_data.shape) # [%]
    speed_data = np.zeros(timestamp_data.shape) # [m/s]

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

            power = (1/(1-bike_drivetrain_loss))*(g*(rider_weight+bike_weight)*(np.sin(np.arctan(slope))+bike_rr_coeff*np.cos(np.arctan(slope)))+(0.5*rider_bike_drag_coeff*rider_bike_frontal_area*air_density*np.power(speed, 2)))*speed

            if power > 0:
                power_data[i] = power

    # create GeoJSON feature collection
    features = []

    for i in np.arange(1, timestamp_data.shape[0]):
        line = geojson.LineString([(lat_lon_data[i-1, 1], lat_lon_data[i-1, 0]), (lat_lon_data[i, 1], lat_lon_data[i, 0])]) # (lon,lat) to (lon,lat) format

        if get_power_data:
            feature = geojson.Feature(geometry = line, properties = {'elevation': float('%.1f'%elevation_data[i]), 'slope': float('%.1f'%(slope_data[i]*100)), 'speed': float('%.1f'%(speed_data[i]*2.236936)), 'power': float('%.1f'%power_data[i])})
        else:
            feature = geojson.Feature(geometry = line, properties = {'elevation': float('%.1f'%elevation_data[i]), 'slope': float('%.1f'%(slope_data[i]*100)), 'speed': float('%.1f'%(speed_data[i]*2.236936))})

        features.append(feature)

    feature_collection = geojson.FeatureCollection(features)

    # write GeoJSON file
    with open(geojson_file, 'w') as file:
        geojson.dump(feature_collection, file)

    return

def geojson2folium(geojson_file, data_vis):
    # read GeoJSON file
    with open(geojson_file, 'r') as file:
        geojson_data = geojson.load(file)

    # Folium style function
    if data_vis == 'track': # show some color...
        f = lambda x: {'color': '#FC4C02', 'weight': 5}
    else: # show color from matplotlib colormap
        cmap = cm.get_cmap('jet')

        cmin = min(feature['properties'][data_vis] for feature in geojson_data['features'])
        cmax = max(feature['properties'][data_vis] for feature in geojson_data['features'])

        f = lambda x: {'color': rgb2hex(cmap((x['properties'][data_vis]-cmin)/(cmax-cmin))), 'weight': 5} # cmap needs normalized data

    # Folium tooltip
    if data_vis == 'track':
        t = None
    elif data_vis == 'elevation':
        t = folium.features.GeoJsonTooltip(fields = [data_vis], aliases = ['Elevation (m)'])
    elif data_vis == 'slope':
        t = folium.features.GeoJsonTooltip(fields = [data_vis], aliases = ['Slope (%)'])
    elif data_vis == 'speed':
        t = folium.features.GeoJsonTooltip(fields = [data_vis], aliases = ['Speed (mph)'])
    elif data_vis == 'power':
        t = folium.features.GeoJsonTooltip(fields = [data_vis], aliases = ['Power (watt)'])

    # add GeoJSON data to Folium map
    map = folium.Map()

    folium.GeoJson(geojson_data, style_function = f, tooltip = t).add_to(map)

    map.fit_bounds(map.get_bounds())

    # save map to html file
    html = 'strava_geojson.html'

    map.save(html)

    # open html file in default browser
    webbrowser.open(html, new = 2, autoraise = True)

    return

def main(args): # main script
    # parse arguments
    gpx_filename = args.gpxfile
    geojson_filename = args.geojsonfile
    data_vis = args.data
    rider_weight = args.riderweight*0.45359237 # lbs to kg
    bike_weight = args.bikeweight*0.45359237 # lbs to kg

    if not gpx_filename[-4:] == '.gpx':
        print('ERROR: --input is not a GPX file')
        quit()

    if not geojson_filename[-8:] == '.geojson' and not geojson_filename == '':
        print('ERROR: --output is not a GeoJSON file')
        quit()

    if data_vis not in ('none', 'track', 'elevation', 'slope', 'speed', 'power'):
        print('ERROR: --visualize option be none, track, elevation, slope, speed or power')
        quit()

    if data_vis == 'power' and (rider_weight <= 0 or bike_weight <= 0):
        print('ERROR: --rider_weight and --bike_weight must be specified to visualize power')
        quit()

    # get GPX and GeoJSON filenames
    gpx_file = glob.glob(gpx_filename)[0] # read only 1 file

    if not gpx_file:
        print('ERROR: no GPX file found')
        quit()

    geojson_file = geojson_filename if geojson_filename else gpx_file[:-4]+'.geojson' # use GPX filename if not specified

    # write GeoJSON file
    gpx2geojson(gpx_file, geojson_file, [rider_weight, bike_weight])

    # visualize GeoJSON file with Folium
    if data_vis is not 'none':
        geojson2folium(geojson_file, data_vis)

if __name__ == '__main__':
    # command line parameters
    parser = argparse.ArgumentParser(description = 'Extract track, elevation, slope, speed and power data from Strava GPX files, export to GeoJSON files and visualize in browser', epilog = 'Report issues to https://github.com/remisalmon/Strava-to-GeoJSON')
    parser.add_argument('--input', dest = 'gpxfile', default = '*.gpx', help = 'input .gpx file')
    parser.add_argument('--output', dest = 'geojsonfile', default = '', help = 'output .geojson file')
    parser.add_argument('--visualize', dest = 'data', default = 'none', help = 'open the .geojson file in the default browser as a color-coded map; DATA = track, elevation, slope, speed, power or none (default: none)')
    parser.add_argument('--rider-weight', dest = 'riderweight', type = float, default = 0, help = 'rider weight for power calculation, RIDERWEIGHT in lbs (default: 0)')
    parser.add_argument('--bike-weight', dest = 'bikeweight', type = float, default = 0, help = 'bike weight for power calculation, BIKEWEIGHT in lbs (default: 0)')
    args = parser.parse_args()

    main(args)
