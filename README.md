# strava_geojson.py

Extract track, elevation, slope, speed and power data from Strava GPX files, export to GeoJSON and visualize in browser

Designed for cycling :bicyclist: activities

## Features

* Calculate the slope (%), speed (mph) and power (watt) at each trackpoint of the GPX file
* Export track, elevation, slope, speed and power data to a GeoJSON file
* In-browser interactive visualization of GeoJSON trackpoint data

## Usage

* Download the GPX file of your Strava activity  
(see https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export#GPX)
* Run `python3 strava_geojson.py` to export all data to a GeoJSON file (for power data, use `--rider-weight` and `--bike-weight`)
* Run `python3 strava_geojson.py --visualize DATA` to visualize a DATA color-coded map in your browser

## Examples

Color-coded trackpoint speed:  
[![example.png](Example/example.png)](https://github.com/remisalmon/Strava-to-GeoJSON/blob/master/Example/example.geojson)

GeoJSON data:  
```
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [...]
  },
  "properties": {
    "elevation": "2203.1",
    "slope": "-1.3",
    "speed": "14.3",
    "power": "83.7"
  }
}
```

## Command-line options

```
usage: strava_geojson.py [-h] [--input GPXFILE] [--output GEOJSONFILE]
                         [--visualize DATA] [--rider-weight RIDERWEIGHT]
                         [--bike-weight BIKEWEIGHT]

Extract track, elevation, slope, speed and power data from Strava GPX files,
export to GeoJSON files and visualize in browser

optional arguments:
  -h, --help            show this help message and exit
  --input GPXFILE       input .gpx file
  --output GEOJSONFILE  output .geojson file
  --visualize DATA      open the .geojson file in the default browser as a
                        color-coded map; DATA = track, elevation, slope,
                        speed, power or none (default: none)
  --rider-weight RIDERWEIGHT
                        rider weight for power calculation, RIDERWEIGHT in lbs
                        (default: 0)
  --bike-weight BIKEWEIGHT
                        bike weight for power calculation, BIKEWEIGHT in lbs
                        (default: 0)

```

## Python dependencies

```
python >= 3.7.1
numpy >= 1.15.4
scipy >= 1.1.0
matplotlib >= 3.0.2
gpxpy >= 1.3.4
geojson >= 2.4.1
folium >= 0.7.0
```

## Todo

* Add multiple data layers to Folium map
