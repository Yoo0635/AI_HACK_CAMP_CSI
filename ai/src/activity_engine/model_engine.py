import numpy as np

try:
    import tflite_runtime.interpreter as tflite
except ModuleNotFoundError:
    import tensorflow.lite as tflite

from config import TFLITE_MODEL_PATH

LABELS = ["NORMAL", "MOVE", "FALL"]


class ActivityEngine:
    def __init__(self):
        self._interpreter = tflite.Interpreter(model_path=TFLITE_MODEL_PATH)
        self._interpreter.allocate_tensors()

        self._input_idx  = self._interpreter.get_input_details()[0]["index"]
        self._output_idx = self._interpreter.get_output_details()[0]["index"]

    def predict(self, window: np.ndarray) -> tuple[str, float, float, np.ndarray]:
        """
        window: (1, 20, 64, 2) float32
        returns: (label, confidence, energy, probs)
        """
        self._interpreter.set_tensor(self._input_idx, window)
        self._interpreter.invoke()

        probs = self._interpreter.get_tensor(self._output_idx)[0]  # (3,)
        cls_idx = int(np.argmax(probs))
        confidence = float(probs[cls_idx])
        energy = float(np.mean(window[0, :, :, 0] ** 2))

        return LABELS[cls_idx], confidence, energy, probs
