#GPS project implementation by Ryan Ackerley &
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import pathlib



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
