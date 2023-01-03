"""
Extracts frames from recordings
"""

import argparse
import collections
import glob
import os
import time
import subprocess

import cv2 as cv
import numpy as np
from PIL import Image


X_BOUND = 1560, 1860
Y_BOUND = 760, 990
SEEK_FRAMES = 30
WHITE_VALUE_THRESHOLD = 200
WHITE_PIXELS_BASELINE = 250


def has_white_pixels(frame: np.ndarray):
    converted = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    count = 0

    for x in range(*X_BOUND):
        for y in range(*Y_BOUND):
            if converted[y, x][2] > WHITE_VALUE_THRESHOLD:
                count += 1

            if count > WHITE_PIXELS_BASELINE:
                return True
    else:
        return False


def main(num: int, input_path: str, output_path: str):
    start = time.time()
    cap = cv.VideoCapture(input_path)
    buffer = collections.deque(maxlen=SEEK_FRAMES)
    last_has_white = False
    frames_extracted = 0
    frames_index = 0

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        buffer.append(frame)
        if not (frames_index % SEEK_FRAMES):
            has_white = has_white_pixels(frame)
            if not last_has_white and has_white:
                while not has_white_pixels(buffered_frame := buffer.popleft()):
                    pass

                image = Image.fromarray(
                    buffered_frame[:, :, ::-1].astype("uint8"), "RGB"
                )
                image.save(f"temp/{num}-{frames_extracted:02d}.png")

                frames_extracted += 1
            last_has_white = has_white

        frames_index += 1
        # print(f"\rExtracted: {frames_extracted} Frame: {frames_index}", end="")

    cap.release()
    end = time.time()
    print(f"\n{end - start:.01f}s")

    subprocess.call(
        [
            "ffmpeg",
            "-framerate",
            "10",
            "-i",
            f"temp/{num}-%02d.png",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "1",
            output_path,
        ]
    )

    for file in glob.glob(f"temp/{num}-*"):
        os.remove(file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", required=True, type=int)
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    namespace = parser.parse_args()
    main(namespace.num, namespace.input, namespace.output)
