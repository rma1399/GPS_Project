#GPS project implementation by Ryan Ackerley &
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import pathlib


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
    cols_placeholder1 = range(13) #change these to whatever we choose to call them
    cols_placeholder2 = range(15)
   
    GPMRC = pd.DataFrame(columns=cols_placeholder1)
    GPGGA = pd.DataFrame(columns=cols_placeholder2)
    
    for file in path.glob("*.txt"): #grabs all text files in our directory we pass in
        with open(file, 'r') as f: #there is mixed encoding, so we can not nicely read it into a csv by just skipping lines
            content = f.read()
            GPMRC_file = []
            GPGGA_file = []
            for line in content.split('$'): #not new line because some data is doubled
                values = line.split(',')
                if values[0] == 'GPRMC' and len(values) == 13: #majority expected length for MRC
                    GPMRC_file.append(values)
                elif values[0] == 'GPGGA' and len(values) == 15: #majority expected length for GGA
                    GPGGA_file.append(values)
            
            GPMRC = pd.concat([GPMRC, pd.DataFrame(GPMRC_file, columns=cols_placeholder1)], ignore_index=True)
            GPGGA = pd.concat([GPGGA, pd.DataFrame(GPGGA_file, columns=cols_placeholder2)], ignore_index=True)

    GPMRC.to_csv('GPMRC_GPS_data.csv', index=False)
    GPGGA.to_csv('GPGGA_GPS_data.csv', index=False)
    return 0


def main():

    folder = 'gps_data'

    data = clean_data(folder)


    return 0

main()
