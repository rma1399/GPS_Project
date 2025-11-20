#GPS project implementation by Ryan Ackerley &
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import pathlib
from datetime import datetime, timedelta
from geopy.distance import geodesic
import simplekml


# Tunable thresholds 
MIN_MOVING_SPEED_MS = 0.5            # below this we consider "not moving"
STOP_SPEED_MS = 0.5                  # speed considered a stop
STOP_MIN_DURATION_S = 2.0            # minimum seconds stopped to consider a stop event
STOP_MAX_DURATION_S = 300.0          # max seconds of a "stop" to mark (parked longer is ignored)
OUTLIER_MAX_JUMP_M = 200.0           # if jump between consecutive points > this, discard point as outlier
OUTLIER_MAX_SPEED_MS = 60.0          # If computed speed between points > this, treat as outlier
DUPLICATE_DIST_M = 1.0               # if two consecutive points are within this distance, treat as duplicate
HEADING_VALID_SPEED_MS = 1.0         # heading is meaningful only above this speed
LEFT_TURN_MIN_DEG = 45.0             # minimum signed change (negative) to be considered a left turn
LEFT_TURN_WINDOW = 5                 # number of points on either side when computing turn
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

def merge_data(gprmc, gpgga):
    gprmc['time_rmc'] = pd.to_numeric(gprmc['time_rmc'], errors='coerce')
    gpgga['time_gga'] = pd.to_numeric(gpgga['time_gga'], errors='coerce')
    gprmc = gprmc.dropna(subset=['time_rmc'])
    gpgga = gpgga.dropna(subset=['time_gga'])
    merged = pd.merge(gprmc,gpgga,left_on='time_rmc',right_on='time_gga',how='inner')
    return merged

def convert_to_decimal(row):
    try:
        lat_raw = row['lat_rmc']
        lon_raw = row['lon_rmc']
        lat_dir = row['lat_dir_rmc']
        lon_dir = row['lon_dir_rmc']

        lat = float(lat_raw[:2]) + float(lat_raw[2:]) / 60
        lon = float(lon_raw[:3]) + float(lon_raw[3:]) / 60

        if lat_dir == 'S':
            lat = -lat
        if lon_dir == 'W':
            lon = -lon

        return pd.Series([lat, lon])
    except:
        return pd.Series([np.nan, np.nan])

def apply_conversion(df):
    df[['latitude', 'longitude']] = df.apply(convert_to_decimal, axis=1)
    df = df.dropna(subset=['latitude', 'longitude'])
    return df

def compute_speed(df):
    df['timestamp'] = pd.to_datetime(df['time_rmc'], format='%H%M%S', errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    speeds = [0]
    for i in range(1, len(df)):
        prev = (df.loc[i-1, 'latitude'], df.loc[i-1, 'longitude'])
        curr = (df.loc[i, 'latitude'], df.loc[i, 'longitude'])
        distance_m = geodesic(prev, curr).meters
        time_s = (df.loc[i, 'timestamp'] - df.loc[i-1, 'timestamp']).total_seconds()
        speeds.append(distance_m / time_s if time_s > 0 else 0)

    df['speed_m_s'] = speeds
    return df



def main():

    folder = 'gps_data'

    gprmc, gpgga = clean_data(folder)
    df = merge_data(gprmc, gpgga)


    return 0



if __name__ == "__main__":
    main()
