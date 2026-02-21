import json, csv, re
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile
from urllib.request import urlopen
from dateutil import tz
from datetime import datetime

stations = {}
platforms = {}
routes = {}
trips = {}

# temporary
calendar = {}
stops = {}

gtfs = urlopen('https://developer.cumtd.com/gtfs/google_transit.zip')
zf = ZipFile(BytesIO(gtfs.read()))

def get_offset(time):
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(time.split(':'))))

with zf.open('stops.txt') as f:
    reader = csv.DictReader(TextIOWrapper(f, 'utf-8'))

    for stop in reader:
        platform_id = stop['stop_id']
        station_id = platform_id.split(':')[0]
        if station_id not in stations:
            stations[station_id] = {
                'station_id': station_id,
                'name': re.sub(r"\([^()]*\)", "", stop['stop_name']).strip(),
                'url': stop['stop_url'],
                'platforms': [],
                'lat': 0.0,
                'lon': 0.0
            }
        
        lat, lon = float(stop['stop_lat']), float(stop['stop_lon'])

        platforms[platform_id] = {
            'platform_id': platform_id,
            'station': station_id,
            'name': stop['stop_name']
        }

        stations[station_id]['platforms'].append(stop['stop_id'])
        stations[station_id]['lat'] += lat
        stations[station_id]['lon'] += lon

for station in stations.values():
    num_platforms = len(station['platforms'])
    station['lat'] /= num_platforms
    station['lon'] /= num_platforms

with zf.open('routes.txt') as f:
    reader = csv.DictReader(TextIOWrapper(f, 'utf-8'))

    for route in reader:
        route_id = route['route_id']
        routes[route_id] = {
            'route_id': route_id,
            'route_short_name': route['route_short_name'],
            'route_long_name': route['route_long_name'],
            'route_desc': route['route_desc']
        }

# MTD does not use regularly scheduled dates as in calendar.txt
with zf.open('calendar_dates.txt') as f:
    reader = csv.DictReader(TextIOWrapper(f, 'utf-8'))

    for cal_date in reader:
        service_id = cal_date['service_id']
        if int(cal_date['exception_type']) != 1:
            continue
        
        if service_id not in calendar:
            calendar[service_id] = []
        
        dt = datetime.strptime(cal_date['date'], '%Y%m%d').replace(tzinfo=tz.gettz('America/Chicago'))

        calendar[service_id].append(int(round(dt.astimezone(tz.tzutc()).timestamp())))

with zf.open('stop_times.txt') as f:
    reader = csv.DictReader(TextIOWrapper(f, 'utf-8'))

    for stop in reader:
        trip_id = stop['trip_id']

        assert(trip_id not in stops or int(stops[trip_id][-1]['sequence']) < int(stop['stop_sequence']))

        if trip_id not in stops:
            stops[trip_id] = []

        stops[trip_id].append({
            'departure_offset': get_offset(stop['departure_time']),
            'arrival_offset': get_offset(stop['arrival_time']),
            'sequence': int(stop['stop_sequence']),
            'platform': stop['stop_id'],
            'station': platforms[stop['stop_id']]['station']
        })

with zf.open('trips.txt') as f:
    reader = csv.DictReader(TextIOWrapper(f, 'utf-8'))

    for trip in reader:
        trip_id = trip['trip_id']
        trips[trip_id] = {
            'trip_id': trip['trip_id'],
            'route': trip['route_id'],
            'shape': trip['shape_id'],
            'services': calendar[trip['service_id']],
            'stops': stops[trip_id],
            'duration': stops[trip_id][-1]['arrival_offset'] - stops[trip_id][0]['departure_offset']
        }

with open("jtfs_stations.json", "w") as outfile:
    json.dump(stations, outfile)

with open("jtfs_platforms.json", "w") as outfile:
    json.dump(platforms, outfile)

with open("jtfs_routes.json", "w") as outfile:
    json.dump(routes, outfile)

with open("jtfs_trips.json", "w") as outfile:
    json.dump(trips, outfile)