"""
Builds replays from frames
"""

import argparse
import copy
import io
import json
import struct

from PIL import Image

from replay_unpack.clients.wows.network.packets import PACKETS_MAPPING
from replay_unpack.core.packets import EntityMethod
from custom import *


DURATION = 30 * 60
FRAME_PERIOD = 20
START_TIME = 200  # time when kleber hits corner
WHITE_VALUE_THRESHOLD = 25
# WHITE_VALUE_THRESHOLD = 120  # credits
MAP_CENTER = 600, 600
SCALED_SIZE = 120, 90
SCALE_FACTOR = 7
PLAYER_ID = 403447948
PING_TYPE_ID = 18  # might be different for not 0.11.11


def fixed_version(raw):
    return raw[: raw.rfind(",")].replace(",", "_")


def main(manifest_path: str, replay_path: str, output_path: str):
    replay_data = CustomReader(replay_path).get_replay_data()
    player = CustomPlayer(
        fixed_version(replay_data.engine_data["clientVersionFromExe"])
    )
    player.play(replay_data.decrypted_data)
    packet_type = next(x for x, y in PACKETS_MAPPING.items() if y == EntityMethod)

    file_index, frame_index, injected = 0, 0, 0
    packets = copy.copy(player.packets)

    with open(manifest_path) as fp:
        manifest = json.load(fp)

    for filename in manifest:
        image = Image.open(filename)
        time = START_TIME + frame_index * FRAME_PERIOD

        if time > DURATION:
            with (
                open(output_path.format(file_index), "wb") as out_file,
                open(replay_path, "rb") as base_replay,
                io.BytesIO(b"".join([b for t, b in packets])) as new_data,
            ):
                write_replay(
                    out_file,
                    base_replay,
                    replay_data.data_index,
                    new_data,
                )
            packets = copy.copy(player.packets)
            file_index += 1
            frame_index, injected = 0, 0
            time = START_TIME

        for i in range(image.size[0]):
            for j in range(image.size[1]):
                p = image.getpixel((i, j))

                if p[0] > WHITE_VALUE_THRESHOLD:
                    coords = (
                        round(MAP_CENTER[0] + SCALE_FACTOR * (i - SCALED_SIZE[0] / 2)),
                        round(MAP_CENTER[1] + SCALE_FACTOR * (j - SCALED_SIZE[1] / 2)),
                    )

                    byte_array = bytearray(42)

                    struct.pack_into(
                        "<IIfIII?IBIQ",
                        byte_array,
                        0,
                        *(
                            30,
                            packet_type,
                            time,
                            *(
                                player.entity_id,
                                player.index,
                                *(
                                    18,
                                    *(
                                        False,
                                        PLAYER_ID,
                                        PING_TYPE_ID,
                                        coords[0],
                                        coords[1],
                                    ),
                                ),
                            ),
                        ),
                    )

                    index = next(ind for ind, (t, b) in enumerate(packets) if t >= time)
                    packets.insert(index, (time, bytes(byte_array)))
                    injected += 1

        frame_index += 1

    if injected:
        with (
            open(output_path.format(file_index), "wb") as out_file,
            open(replay_path, "rb") as base_replay,
            io.BytesIO(b"".join([b for t, b in packets])) as new_data,
        ):
            write_replay(
                out_file,
                base_replay,
                replay_data.data_index,
                new_data,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--manifest", type=str, required=True)
    parser.add_argument("-r", "--replay", type=str, required=True)
    parser.add_argument("-o", "--output", type=str, required=True)
    namespace = parser.parse_args()
    main(namespace.manifest, namespace.replay, namespace.output)
