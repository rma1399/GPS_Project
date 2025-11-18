#GPS project implementation by Ryan Ackerley &
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import pathlib



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
