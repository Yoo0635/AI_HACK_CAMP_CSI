from collections import deque
import numpy as np

WINDOW_SIZE = 20
N_SUBCARRIERS = 64


class Preprocessor:
    def __init__(self):
        self._buffer = deque(maxlen=WINDOW_SIZE)

    def push(self, csi_matrix: list[float]) -> "np.ndarray | None":
        self._buffer.append(csi_matrix)
        if len(self._buffer) < WINDOW_SIZE:
            return None
        return self._build_input()

    def _build_input(self) -> np.ndarray:
        buf = np.array(self._buffer, dtype=np.float32)  # (20, 64)

        amp = np.clip(buf / 20.0, 0.0, 1.0)  # (20, 64)

        diff = np.diff(buf, axis=0)  # (19, 64)
        doppler = np.clip(diff / 5.0, -1.0, 1.0)
        doppler = np.vstack([np.zeros((1, N_SUBCARRIERS), dtype=np.float32), doppler])  # (20, 64)

        combined = np.stack([amp, doppler], axis=-1)  # (20, 64, 2)
        return combined[np.newaxis]  # (1, 20, 64, 2)
