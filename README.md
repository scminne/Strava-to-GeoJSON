# strava_geojson.py

Extract track elevation, slope, speed and power from Strava GPX files, export to GeoJSON and visualize in browser

Designed for Strava :bicyclist: cycling activities

## Features

* Calculate the elevation (m), slope (%), speed (mph) and power (watt) at each trackpoint of the GPX file
* Export the track elevation, slope, speed and power to a GeoJSON file
* Interactive visualization of the GeoJSON file on a color-coded map

## Usage

* Download the GPX file of your Strava activity  
(see https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export#GPX)
* Run `python3 strava_geojson.py` to export the tack data to a GeoJSON file  
(to export the power data, use the `--rider-weight` and `--bike-weight` options)
* Run `python3 strava_geojson.py --visualize` to visualize the tack data in your browser  
(automatically opens in a new browser tab and saved to `strava_geojson.html`)

## Examples

Map of trackpoints speed (`strava_geojson.py --visualize`):

![example.png](Example/example.png)

Raw GeoJSON data (`strava_geojson.py`):

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
                         [--visualize] [--rider-weight RIDERWEIGHT]
                         [--bike-weight BIKEWEIGHT] [--SI-units]

Extract track, elevation, slope, speed and power data from Strava GPX files,
export to GeoJSON files and visualize in browser

optional arguments:
  -h, --help            show this help message and exit
  --input GPXFILE       input .gpx file
  --output GEOJSONFILE  output .geojson file
  --visualize           visualize the .geojson file on an interactive map
                        (opens new browser tap)
  --rider-weight RIDERWEIGHT
                        rider weight for power calculation, RIDERWEIGHT in lbs
                        (default: 0)
  --bike-weight BIKEWEIGHT
                        bike weight for power calculation, BIKEWEIGHT in lbs
                        (default: 0)
  --SI-units            use SI units for speed (km/h) and --rider-weight,
                        --bike-weight inputs (kg) if specified
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
## Setup

Run `pip install -r requirements.txt`
