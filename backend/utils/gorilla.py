import struct


class _BitWriter:
    def __init__(self) -> None:
        self._buffer = bytearray()
        self._current_byte = 0
        self._bits_filled = 0

    def write_bit(self, bit: int) -> None:
        self._current_byte = (self._current_byte << 1) | (bit & 1)
        self._bits_filled += 1

        if self._bits_filled == 8:
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bits_filled = 0

    def write_bits(self, value: int, width: int) -> None:
        for shift in range(width - 1, -1, -1):
            self.write_bit((value >> shift) & 1)

    def to_bytes(self) -> bytes:
        if self._bits_filled:
            self._current_byte <<= 8 - self._bits_filled
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bits_filled = 0

        return bytes(self._buffer)


def _float_to_uint64(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def compress_float64_sequence(values: list[float]) -> bytes:
    if not values:
        return struct.pack(">I", 0)

    writer = _BitWriter()
    writer.write_bits(len(values), 32)

    previous = _float_to_uint64(values[0])
    writer.write_bits(previous, 64)

    previous_leading = 0
    previous_trailing = 0
    has_previous_window = False

    for value in values[1:]:
        current = _float_to_uint64(value)
        xor = previous ^ current

        if xor == 0:
            writer.write_bit(0)
            previous = current
            continue

        writer.write_bit(1)

        leading = 64 - xor.bit_length()
        trailing = (xor & -xor).bit_length() - 1

        can_reuse_window = (
            has_previous_window
            and leading >= previous_leading
            and trailing >= previous_trailing
        )

        if can_reuse_window:
            writer.write_bit(0)
            significant_bits = 64 - previous_leading - previous_trailing
            significant_value = xor >> previous_trailing
            writer.write_bits(significant_value, significant_bits)
        else:
            writer.write_bit(1)
            significant_bits = 64 - leading - trailing
            significant_value = xor >> trailing

            writer.write_bits(leading, 6)
            writer.write_bits(significant_bits % 64, 6)
            writer.write_bits(significant_value, significant_bits)

            previous_leading = leading
            previous_trailing = trailing
            has_previous_window = True

        previous = current

    return writer.to_bytes()
