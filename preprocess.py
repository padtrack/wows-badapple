"""
Builds frames from video
"""

import json

from PIL import Image, ImageFilter
import cv2 as cv


VIDEO = "assets/BadApple.mp4"
FORMAT = "assets/{}.png"
RESCALE_TO = 120, 90


def main():
    cap = cv.VideoCapture(VIDEO)
    filenames = []
    index = 0

    while cap.isOpened():
        ret, frame = cap.read()

        if index % 3 == 0:
            image = Image.fromarray(frame.astype("uint8"), "RGB")
            image = image.resize(RESCALE_TO)
            image = image.filter(ImageFilter.FIND_EDGES)
            filename = FORMAT.format(index)
            with open(filename, "wb") as fp:
                image.save(fp, "PNG")
            filenames.append(filename)

        if not ret:
            break

        index += 1

    cap.release()

    with open("assets/manifest.json", "w") as fp:
        json.dump(filenames, fp, indent=4)


if __name__ == "__main__":
    main()
