"""
Custom replay functions and classes
"""

__all__ = ["CustomPlayer", "CustomReader", "write_replay"]

from typing import BinaryIO, NamedTuple
from io import BytesIO
import struct
import json
import zlib

from Cryptodome.Cipher import Blowfish

from replay_unpack.core.network.net_packet import NetPacket
from replay_unpack.core.packets import EntityMethod
from replay_unpack.clients.wows.player import ReplayPlayer
from replay_unpack.clients.wows.helper import get_definitions, get_controller
from replay_unpack.replay_reader import WOWS_BLOWFISH_KEY, ReplayReader


blowfish = Blowfish.new(WOWS_BLOWFISH_KEY, Blowfish.MODE_ECB)


ReplayInfo = NamedTuple(
    "ReplayInfo",
    [
        ("engine_data", dict),
        ("decrypted_data", bytes),
        ("data_index", int),
    ],
)


def write_replay(
    out_file: BinaryIO,
    base_replay: BinaryIO,
    index: int,
    new_data: BinaryIO,
) -> None:
    header = base_replay.read(index)
    out_file.write(header)

    data = new_data.read()

    compressed = zlib.compress(data, level=9)
    if remainder := len(compressed) % 8:
        compressed += (8 - remainder) * b"\x00"  # pad to ensure 8 byte chunks

    out_file.write(struct.pack("I", len(data)))
    out_file.write(struct.pack("I", len(compressed)))

    split = [compressed[i : i + 8] for i in range(0, len(compressed), 8)]
    unpacked = [struct.unpack("q", chunk)[0] for chunk in split]

    # cipher block chaining

    last = None
    for chunk in unpacked:
        if last is not None:
            encrypted = blowfish.encrypt(struct.pack("q", chunk ^ last))
        else:
            encrypted = blowfish.encrypt(struct.pack("q", chunk))

        last = chunk
        out_file.write(encrypted)


class CustomReader(ReplayReader):
    def get_replay_data(self) -> ReplayInfo:
        with open(self._replay_path, "rb") as f:
            f.read(4)
            blocks_count = struct.unpack("i", f.read(4))[0]

            block_size = struct.unpack("i", f.read(4))[0]
            engine_data = json.loads(f.read(block_size))

            for i in range(blocks_count - 1):
                block_size = struct.unpack("i", f.read(4))[0]
                f.read(block_size)

            index = f.tell()
            decrypted_data = zlib.decompress(self.__decrypt_data(f.read()))

            if self._dump_binary_data:
                self._save_decrypted_data(decrypted_data)

            return ReplayInfo(
                engine_data=engine_data,
                decrypted_data=decrypted_data,
                data_index=index,
            )

    def __decrypt_data(self, dirty_data):
        # noinspection PyProtectedMember,PyUnresolvedReferences
        return ReplayReader._ReplayReader__decrypt_data(self, dirty_data)


class CustomPlayer(ReplayPlayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.packets = []
        self.entity_id = None
        self.index = None

    def _get_definitions(self, version):
        return get_definitions(version)

    def _get_controller(self, version):
        return get_controller(version)

    def play(self, replay_data, strict_mode=False):
        io = BytesIO(replay_data)

        while io.tell() != len(replay_data):
            start = io.tell()
            packet = NetPacket(io)
            end = io.tell()
            io.seek(start)

            self.packets.append((packet.time, io.read(end - start)))

            deserialized = self._deserialize_packet(packet)
            self._process_packet(deserialized)

            if isinstance(deserialized, EntityMethod):
                entity = self._battle_controller.entities[deserialized.entityId]

                # noinspection PyProtectedMember
                if entity._spec.get_name() == "Avatar":
                    self.entity_id = entity.id

                    # noinspection PyProtectedMember
                    self.index = next(
                        index
                        for index, method in enumerate(entity._methods)
                        if method.get_name() == "receive_CommonCMD"
                    )
