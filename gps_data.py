#GPS project implementation by Ryan Ackerley & Aidan Roullet
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import pathlib
from datetime import datetime, timedelta
from geopy.distance import geodesic
import simplekml


# Tunable thresholds 
MIN_MOVING_SPEED_MS = 0.3            # below this we consider "not moving"
MIN_MOVING_SPEED_MS_LEFT = 0.5       # below this we consider "not moving"
STOP_SPEED_MS = 0.7                  # speed considered a stop
STOP_MIN_DURATION_S = 3.0            # minimum seconds stopped to consider a stop event
STOP_MAX_DURATION_S = 300.0          # max seconds of a "stop" to mark (parked longer is ignored)
OUTLIER_MAX_JUMP_M = 400.0           # if jump between consecutive points > this, discard point as outlier
OUTLIER_MAX_SPEED_MS = 60.0          # If computed speed between points > this, treat as outlier
DUPLICATE_DIST_M = 0.5               # if two consecutive points are within this distance, treat as duplicate
HEADING_VALID_SPEED_MS = 0.5         # heading is meaningful only above this speed
LEFT_TURN_MIN_DEG = 25.0             # minimum signed change (negative) to be considered a left turn
LEFT_TURN_MAX_DEG = 120.0            # max signed change (negative) to be considered a left turn
LEFT_TURN_WINDOW = 4                 # number of points on either side when computing turn
MAX_POINTS_PER_TRACK = 10000         # split LineString if exceeded
FIX_ALTITUDE_M = 3.0                 # altitude to use for KML points


def clean_data(folder_filename):
    path = pathlib.Path(folder_filename)
    GPRMC_COLUMNS = ["type_rmc","time_rmc","status_rmc","lat_rmc","lat_dir_rmc",
                     "lon_rmc","lon_dir_rmc","speed_knots_rmc","track_deg_rmc",
                     "date_rmc","mag_var_rmc","mag_dir_rmc","checksum_rmc"]

    GPGGA_COLUMNS = ["type_gga","time_gga","lat_gga","lat_dir_gga","lon_gga",
                     "lon_dir_gga","fix_quality_gga","num_sats_gga","hdop_gga",
                     "altitude_gga","altitude_unit_gga","geoid_sep_gga",
                     "geoid_unit_gga","age_diff_gga","checksum_gga"]

    GPRMC_df = pd.DataFrame(columns=GPRMC_COLUMNS + ['source_file'])
    GPGGA_df = pd.DataFrame(columns=GPGGA_COLUMNS + ['source_file'])

    for file in path.glob("*.txt"):
        with open(file, 'r') as f:
            content = f.read()
            GPRMC_file, GPGGA_file = [], []
            for line in content.split('$'):
                values = line.strip().split(',')
                if len(values) == 13 and values[0]=='GPRMC':
                    values.append(file.name)
                    GPRMC_file.append(values)
                elif len(values)==15 and values[0]=='GPGGA':
                    values.append(file.name)
                    GPGGA_file.append(values)
            if GPRMC_file:
                GPRMC_df = pd.concat([GPRMC_df, pd.DataFrame(GPRMC_file, columns=GPRMC_COLUMNS + ['source_file'])], ignore_index=True)
            if GPGGA_file:
                GPGGA_df = pd.concat([GPGGA_df, pd.DataFrame(GPGGA_file, columns=GPGGA_COLUMNS + ['source_file'])], ignore_index=True)
    return GPRMC_df, GPGGA_df

def parse_nmea_time(t):
    if pd.isna(t):
        return pd.NaT
    t = f"{t:09.3f}" 
    hh = int(t[0:2])
    mm = int(t[2:4])
    ss = float(t[4:])
    return pd.to_timedelta(f"{hh:02d}:{mm:02d}:{ss:06.3f}") #simple pandas delta converter for explicitness

def merge_data(gprmc, gpgga):
    gprmc['time'] = gprmc['time_rmc'].astype(float).apply(parse_nmea_time)
    gpgga['time'] = gpgga['time_gga'].astype(float).apply(parse_nmea_time)
    gprmc = gprmc.dropna(subset=['time_rmc'])
    gpgga = gpgga.dropna(subset=['time_gga'])
    gprmc = gprmc.sort_values('time')
    gpgga = gpgga.sort_values('time')
    merged = pd.merge_asof(gprmc,gpgga,on='time',direction='nearest',tolerance=pd.Timedelta('0.5s')) #changed this so merge works better
    return merged

def convert_to_decimal(row):
    try:
        lat_raw, lon_raw = row['lat_rmc'], row['lon_rmc']
        lat_dir, lon_dir = row['lat_dir_rmc'], row['lon_dir_rmc']
        lat = float(lat_raw[:2]) + float(lat_raw[2:])/60
        lon = float(lon_raw[:3]) + float(lon_raw[3:])/60
        if lat_dir=='S': lat=-lat # South is negative
        if lon_dir=='W': lon=-lon # West is negative
        return pd.Series([lat, lon])
    except:
        return pd.Series([np.nan, np.nan])

def apply_conversion(df):
    df[['latitude','longitude']] = df.apply(convert_to_decimal, axis=1)
    return df.dropna(subset=['latitude','longitude']) # Drop where nan

def parse_rmc_datetime(time_str, date_str):
    try:
        t = float(time_str)
        hh = int(t // 10000)
        mm = int((t % 10000) // 100)
        ss = int(t % 100)
        day = int(date_str[:2])
        month = int(date_str[2:4])
        year = 2000 + int(date_str[4:6])
        return datetime(year,month,day,hh,mm,ss)
    except:
        return None

def add_timestamp(df):
    df['timestamp'] = [parse_rmc_datetime(t,d) for t,d in zip(df['time_rmc'], df['date_rmc'])]
    df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df


def compute_speed(df):
    speeds = [0.0]
    for i in range(1,len(df)):
        prev = (df.loc[i-1,'latitude'], df.loc[i-1,'longitude'])
        curr = (df.loc[i,'latitude'], df.loc[i,'longitude'])
        dt = (df.loc[i,'timestamp'] - df.loc[i-1,'timestamp']).total_seconds()
        dist = geodesic(prev,curr).meters
        speeds.append(dist/dt if dt>0 else 0)
    df['speed_m_s'] = speeds
    return df

def detect_stops(df):
    df['is_slow'] = df['speed_m_s'] <= STOP_SPEED_MS
    df['slow_group'] = (df['is_slow'] != df['is_slow'].shift()).cumsum()
    slow_groups = df[df['is_slow']].groupby('slow_group').agg(
        start_time=('timestamp','first'),
        end_time=('timestamp','last'),
        lat=('latitude','first'),
        lon=('longitude','first'),
        n_points=('timestamp','count')
    )
    slow_groups['duration_s'] = (slow_groups['end_time']-slow_groups['start_time']).dt.total_seconds()
    stops = slow_groups[(slow_groups['duration_s']>=STOP_MIN_DURATION_S) & 
                        (slow_groups['duration_s']<=STOP_MAX_DURATION_S)].reset_index(drop=True)
    return stops

def detect_left_turns(df):

    df['track_deg'] = df['track_deg_rmc'].astype(float) #first convert to float type explicitly
    df['delta_track'] = df['track_deg'].diff().fillna(0) #then calculate the difference change from the previous
    df['rolling_angle_change'] = df['delta_track'].rolling(LEFT_TURN_WINDOW, min_periods=1).median() #then look at it through a rolling window, grabbing the median will help eliminate jumps
    df['curv'] = df['rolling_angle_change'].rolling(LEFT_TURN_WINDOW, min_periods=1).sum() #you can then sum data to find the expected curvature

    #evaluate from here for left turns, and then group together using another rolling window
    df['is_left'] = (df['curv'] < -LEFT_TURN_MIN_DEG) & (df['curv'] > -LEFT_TURN_MAX_DEG) & (df['speed_m_s'] > MIN_MOVING_SPEED_MS_LEFT)
    df['is_left'] = df['is_left'].rolling(LEFT_TURN_WINDOW, min_periods=1).max().astype(bool)
    df['left_groups'] = (df['is_left'] != df['is_left'].shift()).cumsum() #group creation
    left_turns = df[df['is_left']].groupby('left_groups').agg(
        start_time=('timestamp','first'),
        end_time=('timestamp','last'),
        lat=('latitude','first'),
        lon=('longitude','first'),
        n_points=('timestamp','count')
    )

    #print(left_turns['n_points'])
    left_turns = left_turns[left_turns['n_points'] >= 8] #filter for too small groups, this too can be tuned
    return left_turns

def export_kml(df, stops, left_turns, filename='route.kml'):
    kml = simplekml.Kml()
    
    # Full path line
    coords = [(lon, lat, FIX_ALTITUDE_M) for lat, lon in zip(df['latitude'], df['longitude'])]
    ls = kml.newlinestring(name='Route', coords=coords)
    ls.style.linestyle.color = simplekml.Color.yellow
    ls.style.linestyle.width = 3

    # Stops go here
    for _, s in stops.iterrows():
        p = kml.newpoint(name=f"Stopped {s['duration_s']:.1f}s", coords=[(s['lon'], s['lat'], FIX_ALTITUDE_M)])
        p.style.iconstyle.color = simplekml.Color.red
        p.style.iconstyle.scale = 1.3

    for _, l in left_turns.iterrows():
        p = kml.newpoint(name=f'Left Turn!', coords=[(l['lon'], l['lat'], FIX_ALTITUDE_M)])
        p.style.iconstyle.color = simplekml.Color.green
        p.style.iconstyle.scale = 1.3



    kml.save(filename)
    print(f"KML saved: {filename}")



def process_file(file_path):
    gprmc, gpgga = clean_data(file_path.parent)
    gprmc_file = gprmc[gprmc['source_file']==file_path.name].copy()
    gpgga_file = gpgga[gpgga['source_file']==file_path.name].copy()

    df = merge_data(gprmc_file, gpgga_file)
    df = apply_conversion(df)
    df = add_timestamp(df)
    df = compute_speed(df)

    stops = detect_stops(df)
    left_turns = detect_left_turns(df) #can be tuned more

    kml_filename = file_path.stem + ".kml"
    export_kml(df, stops, left_turns, filename=kml_filename)
    print(f"Processed {file_path.name}: {len(df)} points, {len(stops)} stops.") 


def main():
    folder = pathlib.Path('gps_data')
    for file_path in folder.glob("*.txt"):
        process_file(file_path)
    return 0



if __name__ == "__main__":
    main()
