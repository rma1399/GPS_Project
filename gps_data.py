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
    cols_placeholder1 = range(15)
    cols_placeholder2 = range(13)
    data1 = pd.DataFrame()
    data1.columns = cols_placeholder1
    data2 = pd.DataFrame()
    data2.columns = cols_placeholder2

    for file in path.glob("*.txt"):
        with open(file, 'r') as f:
            content = f.read()
            GPMRC = []
            GPGGA = []
            for line in content.split('$'):
                values = line.split(',')
                if values[0] == 'GPRMC':
                    GPMRC.append(values)
                elif values[0] == 'GPGGA':
                    GPGGA.append(values)
            
            data1 = pd.merge(left=data1, right=pd.DataFrame(GPMRC, columns=cols_placeholder1))
            data2 = pd.merge(left=data2, right=pd.DataFrame(GPGGA, columns=cols_placeholder2))



    return 0


def main():

    folder = 'gps_data'

    data = clean_data(folder)


    return 0

main()
