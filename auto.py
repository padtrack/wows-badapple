"""
Launches replays from {start} to {end}, inclusive
"""

import argparse
import os
import time

import psutil


PROCESS_NAME = "WorldOfWarships64.exe"
FORMAT = "generated\\bad_apple_{}.wowsreplay"
DURATION = 30 * 60
BUFFER = 3 * 60
PLAY_TIME = DURATION + BUFFER
WAIT_TIME = 30


def main(start: int, end: int):
    for num in range(start, end + 1):
        os.startfile(FORMAT.format(num))
        time.sleep(PLAY_TIME)
        for proc in psutil.process_iter():
            if proc.name() == PROCESS_NAME:
                proc.kill()
        time.sleep(WAIT_TIME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", type=int, required=True)
    parser.add_argument("-e", "--end", type=int, required=True)
    namespace = parser.parse_args()
    main(namespace.start, namespace.end)
