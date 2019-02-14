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
    hexc = '#%02x%02x%02x'%(int(c[0]*255), int(c[1]*255), int(c[2]*255))
    return(hexc)

def distLatLon(p1, p2): # distance between p1 and p2 [lat,lon] (in deg)
    lat1 = np.radians(p1[0])
    lat2 = np.radians(p2[0])
    lon1 = np.radians(p1[1])
    lon2 = np.radians(p2[1])

    delta_lat = lat2-lat1
    delta_lon = lon2-lon1

    # Haversine formula
    a = np.power(np.sin(delta_lat/2.0), 2)+np.cos(lat1)*np.cos(lat2)*np.power(np.sin(delta_lon/2.0), 2)
    c = 2.0*np.arctan2(np.sqrt(a), np.sqrt(1.0-a))

    dist = 6371e3*c

    return(dist)

def distLatLonPoint2Line(p0, p1, p2): # distance from p0 to line defined by p1 and p2 [lat,lon] (in deg)
    # Mercator projection
    P0 = np.array([np.radians(p0[1]), np.arcsinh(np.tan(np.radians(p0[0])))])*6371e3
    P1 = np.array([np.radians(p1[1]), np.arcsinh(np.tan(np.radians(p1[0])))])*6371e3
    P2 = np.array([np.radians(p2[1]), np.arcsinh(np.tan(np.radians(p2[0])))])*6371e3

    # distance from point to line
    dist = abs((P2[1]-P1[1])*P0[0]-(P2[0]-P1[0])*P0[1]+P2[0]*P1[1]-P2[1]*P1[0])/np.sqrt(np.power(P2[1]-P1[1], 2)+np.power(P2[0]-P1[0], 2)) # (from https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points)

    return(dist)

def RDP(data, epsilon): # Ramer–Douglas–Peucker algorithm
    if epsilon <= 0:
        return(data)

    dist_max = 0
    index = 0

    for i in np.arange(1, data.shape[0]):
        dist = distLatLonPoint2Line(data[i, :2], data[0, :2], data[-1, :2]) # needs a 2D projection, does not work with cross-track distance

        if dist > dist_max:
            index = i
            dist_max = dist

    if dist_max > epsilon:
        tmp1 = RDP(data[:index+1, :], epsilon)
        tmp2 = RDP(data[index:, :], epsilon)

        data_new = np.vstack((tmp1[:-1], tmp2))
    else:
        data_new = np.vstack((data[0, :], data[-1, :]))

    return(data_new)

def gpx2geojson(gpx_file, geojson_file, param = [0, 0], use_SI = False, use_RDP = False):
    # parameters
    rider_weight = param[0] # kg
    bike_weight = param[1] # kg

    if rider_weight*bike_weight == 0:
        get_power_data = False
    else:
        get_power_data = True

    # constants
    rider_bike_frontal_area = 0.632 # m^2 (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    rider_bike_drag_coeff = 1.15 # unitless (from https://www.cyclingpowerlab.com/cyclingaerodynamics.aspx)
    bike_drivetrain_loss = 7/100 # % (from https://en.wikipedia.org/wiki/Bicycle_performance#Mechanical_efficiency)
    bike_rr_coeff = 0.006 # unitless (from https://en.wikipedia.org/wiki/Bicycle_performance#Rolling_resistance)
    air_density = 1.225 # kg/m^3
    g = 9.80665 # m/s^2

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
        distance_data[i] = distLatLon(lat_lon_data[i-1, :], lat_lon_data[i, :])

        delta_elevation = elevation_data[i]-elevation_data[i-1]

        if distance_data[i] > 0:
            slope_data[i] = delta_elevation/distance_data[i]

        distance_data[i] = np.sqrt(np.power(distance_data[i], 2)+np.power(delta_elevation, 2)) # recalculate distance to take slope into account

    for i in np.arange(1, timestamp_data.shape[0]):
        if timestamp_data[i] != timestamp_data[i-1]:
            speed_data[i] = distance_data[i]/(timestamp_data[i]-timestamp_data[i-1])

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

    # use Ramer–Douglas–Peucker algorithm to reduce the number of trackpoints
    if use_RDP:
        epsilon = 1 # [m]

        tmp = np.hstack((lat_lon_data, np.arange(0, lat_lon_data.shape[0]).reshape((-1, 1)))) # hack

        tmp_new = RDP(tmp, epsilon) # remove trackpoints less than epsilon meters away from the new track

        index = tmp_new[:, 2].astype(int) # hack

        lat_lon_data = lat_lon_data[index, :]
        elevation_data = elevation_data[index]
        timestamp_data = timestamp_data[index]
        distance_data = distance_data[index]
        slope_data = slope_data[index]
        speed_data = speed_data[index]
        if get_power_data:
            power_data = power_data[index]

    # convert units
    if use_SI:
        speed_data = speed_data*3.6 # m/s to km/h
    else:
        speed_data = speed_data*2.236936 # m/s to mph

    slope_data = abs(slope_data*100) # decimal to %

    # create GeoJSON feature collection
    features = []

    for i in np.arange(1, timestamp_data.shape[0]):
        line = geojson.LineString([(lat_lon_data[i-1, 1], lat_lon_data[i-1, 0]), (lat_lon_data[i, 1], lat_lon_data[i, 0])]) # (lon,lat) to (lon,lat) format

        if get_power_data:
            feature = geojson.Feature(geometry = line, properties = {'elevation': float('%.1f'%elevation_data[i]), 'slope': float('%.1f'%slope_data[i]), 'speed': float('%.1f'%speed_data[i]), 'power': float('%.1f'%power_data[i])})
        else:
            feature = geojson.Feature(geometry = line, properties = {'elevation': float('%.1f'%elevation_data[i]), 'slope': float('%.1f'%slope_data[i]), 'speed': float('%.1f'%speed_data[i])})

        features.append(feature)

    feature_collection = geojson.FeatureCollection(features)

    # write GeoJSON file
    with open(geojson_file, 'w') as file:
        geojson.dump(feature_collection, file)

    return

def geojson2folium(geojson_file, use_SI = False):
    # read GeoJSON file
    with open(geojson_file, 'r') as file:
        geojson_data = geojson.load(file)

    # check for power data
    if 'power' in geojson_data[0]['properties']:
        use_power_data = True
    else:
        use_power_data = False

    # set speed unit
    if use_SI:
        speed_unit = '(km/h)'
    else:
        speed_unit = '(mph)'

    # set up Folium map
    fmap = folium.Map(tiles = None, prefer_canvas = True, disable_3d = True)
    folium.TileLayer(tiles = 'Stamen Terrain', name = 'Terrain Map', show = True).add_to(fmap)
    folium.TileLayer(tiles = 'OpenStreetMap', name = 'OpenStreetMap', show = False).add_to(fmap)

    cmap = cm.get_cmap('jet') # matplotlib colormap

    # create new GeoJson objects to reduce GeoJSON data sent to Folium map as layer
    f_track = lambda x: {'color': '#FC4C02', 'weight': 5} # show some color...

    features = []
    for feature in geojson_data['features']:
        line = geojson.LineString(feature['geometry']['coordinates'])

        features.append(geojson.Feature(geometry = line))

    geojson_data_track = geojson.FeatureCollection(features)

    folium.GeoJson(geojson_data_track, style_function = f_track, name = 'Track only', show = True, smooth_factor = 3.0).add_to(fmap)

    cmin_elevation = min(feature['properties']['elevation'] for feature in geojson_data['features'])
    cmax_elevation = max(feature['properties']['elevation'] for feature in geojson_data['features'])
    f_elevation = lambda x: {'color': rgb2hex(cmap((x['properties']['elevation']-cmin_elevation)/(cmax_elevation-cmin_elevation))), 'weight': 5} # cmap needs normalized data
    t_elevation = folium.features.GeoJsonTooltip(fields = ['elevation'], aliases = ['Elevation (m)'])

    features = []
    for feature in geojson_data['features']:
        line = geojson.LineString(feature['geometry']['coordinates'])
        elevation = feature['properties']['elevation']

        features.append(geojson.Feature(geometry = line, properties = {'elevation': elevation}))

    geojson_data_elevation = geojson.FeatureCollection(features)

    folium.GeoJson(geojson_data_elevation, style_function = f_elevation, tooltip = t_elevation, name = 'Elevation (m)', show = False, smooth_factor = 3.0).add_to(fmap)

    cmin_slope = min(feature['properties']['slope'] for feature in geojson_data['features'])
    cmax_slope = max(feature['properties']['slope'] for feature in geojson_data['features'])
    f_slope = lambda x: {'color': rgb2hex(cmap((x['properties']['slope']-cmin_slope)/(cmax_slope-cmin_slope))), 'weight': 5} # cmap needs normalized data
    t_slope = folium.features.GeoJsonTooltip(fields = ['slope'], aliases = ['Slope (%)'])

    features = []
    for feature in geojson_data['features']:
        line = geojson.LineString(feature['geometry']['coordinates'])
        slope = feature['properties']['slope']

        features.append(geojson.Feature(geometry = line, properties = {'slope': slope}))

    geojson_data_slope = geojson.FeatureCollection(features)

    folium.GeoJson(geojson_data_slope, style_function = f_slope, tooltip = t_slope, name = 'Slope (%)', show = False, smooth_factor = 3.0).add_to(fmap)

    cmin_speed = min(feature['properties']['speed'] for feature in geojson_data['features'])
    cmax_speed = max(feature['properties']['speed'] for feature in geojson_data['features'])
    f_speed = lambda x: {'color': rgb2hex(cmap((x['properties']['speed']-cmin_speed)/(cmax_speed-cmin_speed))), 'weight': 5} # cmap needs normalized data
    t_speed = folium.features.GeoJsonTooltip(fields = ['speed'], aliases = ['Speed '+speed_unit])

    features = []
    for feature in geojson_data['features']:
        line = geojson.LineString(feature['geometry']['coordinates'])
        speed = feature['properties']['speed']

        features.append(geojson.Feature(geometry = line, properties = {'speed': speed}))

    geojson_data_speed = geojson.FeatureCollection(features)

    folium.GeoJson(geojson_data_speed, style_function = f_speed, tooltip = t_speed, name = 'Speed '+speed_unit, show = False, smooth_factor = 3.0).add_to(fmap)

    if use_power_data:
        cmin_power = min(feature['properties']['power'] for feature in geojson_data['features'])
        cmax_power = max(feature['properties']['power'] for feature in geojson_data['features'])
        f_power = lambda x: {'color': rgb2hex(cmap((x['properties']['power']-cmin_power)/(cmax_power-cmin_power))), 'weight': 5} # cmap needs normalized data
        t_power = folium.features.GeoJsonTooltip(fields = ['power'], aliases = ['Power (watt)'])

        features = []
        for feature in geojson_data['features']:
            line = geojson.LineString(feature['geometry']['coordinates'])
            power = feature['properties']['power']

            features.append(geojson.Feature(geometry = line, properties = {'power': power}))

        geojson_data_power = geojson.FeatureCollection(features)

        folium.GeoJson(geojson_data_power, style_function = f_power, tooltip = t_power, name = 'Power (watt)', show = False, smooth_factor = 3.0).add_to(fmap)

    # add layer control widget
    folium.LayerControl(collapsed = False).add_to(fmap)

    # save map to html file
    fmap.fit_bounds(fmap.get_bounds())

    html_file = geojson_file[:-8]+'.html'

    fmap.save(html_file)

    # open html file in default browser
    webbrowser.open(html_file, new = 2, autoraise = True)

    return

def main(args): # main script
    # parse arguments
    gpx_filename = args.gpxfile # str
    geojson_filename = args.geojsonfile # str
    visualize = args.visualize # bool
    SI = args.SI # bool
    rider_weight = args.riderweight if SI else args.riderweight*0.45359237 # float (kg)
    bike_weight = args.bikeweight if SI else args.bikeweight*0.45359237 # float (kg)

    if not gpx_filename[-4:] == '.gpx':
        print('ERROR: --input is not a GPX file')
        quit()

    if not geojson_filename[-8:] == '.geojson' and not geojson_filename == '':
        print('ERROR: --output is not a GeoJSON file')
        quit()

    if (rider_weight > 0 and bike_weight <= 0) or (rider_weight <= 0 and bike_weight > 0):
        print('ERROR: --rider_weight and --bike_weight must be both specified to calculate power')
        quit()

    # get GPX and GeoJSON filenames
    gpx_file = glob.glob(gpx_filename)[0] # read only 1 file

    if not gpx_file:
        print('ERROR: no GPX file found')
        quit()

    geojson_file = geojson_filename if geojson_filename else gpx_file[:-4]+'.geojson' # use GPX filename if not specified

    # write GeoJSON file
    gpx2geojson(gpx_file, geojson_file, param = [rider_weight, bike_weight], use_SI = SI, use_RDP = visualize)

    # visualize GeoJSON file with Folium
    if visualize:
        geojson2folium(geojson_file, use_SI = SI)

if __name__ == '__main__':
    # command line parameters
    parser = argparse.ArgumentParser(description = 'Extract track, elevation, slope, speed and power data from Strava GPX files, export to GeoJSON files and visualize in browser', epilog = 'Report issues to https://github.com/remisalmon/Strava-to-GeoJSON')
    parser.add_argument('--input', dest = 'gpxfile', default = '*.gpx', help = 'input .gpx file')
    parser.add_argument('--output', dest = 'geojsonfile', default = '', help = 'output .geojson file')
    parser.add_argument('--visualize', dest = 'visualize', action = 'store_true', help = 'visualize the .geojson file on an interactive map (opens new browser tap)')
    parser.add_argument('--rider-weight', dest = 'riderweight', type = float, default = 0, help = 'rider weight for power calculation, RIDERWEIGHT in lbs (default: 0)')
    parser.add_argument('--bike-weight', dest = 'bikeweight', type = float, default = 0, help = 'bike weight for power calculation, BIKEWEIGHT in lbs (default: 0)')
    parser.add_argument('--SI-units', dest = 'SI', action = 'store_true', help = 'use SI units for speed (km/h) and --rider-weight, --bike-weight inputs (kg) if specified')

    args = parser.parse_args()

    main(args)
