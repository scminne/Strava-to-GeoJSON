# strava_geojson.py

Python script to retrive the (speed, power, elevation, slope) from Strava GPX files and export to GeoJSON

Optimized for cycling :bicyclist: activities

## Features

* Calculate the (speed, power, elevation, slope) at each trackpoint of the GPX file
* Export all trackpoint data to a GeoJSON file
* Export one trackpoint data to a color-coded GeoJSON file
* Color-coded GeoJSON file compatible with [geojson.io](http://geojson.io) and [umap.openstreetmap.fr](https://umap.openstreetmap.fr)

## Examples

Color-coded trackpoint speed (click for interactive map):  
[![example.png](Example/example.png)](https://github.com/remisalmon/Strava-to-GeoJSON/blob/master/Example/example.geojson)

All trackpoint data:  
```
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      ...
    ]
  },
  "properties": {
    "elevation (m)": "2203.1",
    "slope (%)": "-1.3",
    "speed (mph)": "14.3",
    "power (watt)": "83.7"
  }
}
```

## Usage

* Download the GPX file of your Strava activity  
(see https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export#GPX)
* Run `python3 strava_geojson.py --vis-data DATA` to export DATA to a color-coded GeoJSON file
* Run `python3 strava_geojson.py --all-data` to export all data to a GeoJSON file
* [To visualize a color-coded GeoJSON file] Upload the `.geojson` file to [geojson.io](http://geojson.io) (Open->File) or [umap.openstreetmap.fr](https://umap.openstreetmap.fr) (Create a map->Import data)

### Command-line options

```
usage: strava_geojson.py [-h] [--input GPXFILE] [--output GEOJSONFILE]
                         [--vis-data DATA] [--vis-website WEBSITE]
                         [--all-data] [--rider-weight RIDERWEIGHT]
                         [--bike-weight BIKEWEIGHT]

Extract (speed, power, elevation, slope) data from Strava GPX files and export
to GeoJSON

optional arguments:
  -h, --help            show this help message and exit
  --input GPXFILE       input .gpx file
  --output GEOJSONFILE  output .geojson file
  --vis-data DATA       data to visualize on the color-coded GeoJSON file:
                        track, elevation, slope, speed, power (default: track)
  --vis-website WEBSITE
                        platform to visualize the color-coded GeoJSON file:
                        geojsonio or umap (default: geojsonio)
  --all-data            export all data to the GeoJSON file (disregards --vis-
                        data)
  --rider-weight RIDERWEIGHT
                        rider weight for power calculation, in lbs (default:
                        0)
  --bike-weight BIKEWEIGHT
                        bike weight for power calculation, in lbs (default: 0)
```

## Python dependencies

```
python >= 3.7.1
numpy >= 1.15.4
scipy >= 1.1.0
matplotlib >= 3.0.2
gpxpy >= 1.3.4
geojson >= 2.4.1
```
