"""
Find frames with only "black" pixels in them
for post-editing to inject
"""

from PIL import Image
import glob


def main():
    black_frames = []

    for file in glob.glob("assets/*.png"):
        image = Image.open(file)

        count = 0
        for x in range(image.size[0]):
            for y in range(image.size[1]):
                p = image.getpixel((x, y))

                if p[0] > 25:
                    count += 1

        if not count:
            black_frames.append(int(file[file.index("/") + 1 : file.index(".")]))

    print(sorted(black_frames))


if __name__ == "__main__":
    main()
