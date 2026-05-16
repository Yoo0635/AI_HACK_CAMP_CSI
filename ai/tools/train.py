import argparse
import glob
import os
import sys

import numpy as np
from sklearn.utils.class_weight import compute_class_weight

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
from tensorflow.keras import Input, Model, regularizers
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import (
    BatchNormalization, Conv2D, Dense, Dropout,
    LSTM, MaxPooling2D, Reshape,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

LABELS = ["NORMAL", "MOVE", "FALL"]
WINDOW = 20


CHUNK_FRAMES = 150  # 파일이 적을 때 가상 파일로 분할하는 크기


def array_to_chunks(arr: np.ndarray) -> list:
    return [arr[i : i + CHUNK_FRAMES] for i in range(0, len(arr), CHUNK_FRAMES)
            if len(arr[i : i + CHUNK_FRAMES]) >= WINDOW]


def chunks_to_windows(chunks: list, cls_idx: int):
    X, y = [], []
    for chunk in chunks:
        chunk[:, 32] = (chunk[:, 31] + chunk[:, 33]) / 2.0
        for i in range(len(chunk) - WINDOW + 1):
            X.append(chunk[i : i + WINDOW])
            y.append(cls_idx)
    return X, y


def load_windows(data_dir: str, val_ratio: float = 0.2):
    X_train, y_train, X_val, y_val = [], [], [], []

    for cls_idx, label in enumerate(LABELS):
        files = sorted(glob.glob(os.path.join(data_dir, f"{label}_*.npy")))
        if not files:
            print(f"[WARN] {label} 파일 없음")
            continue

        # 파일을 청크로 분해 (파일 수가 적어도 다양한 분할 가능)
        all_chunks = []
        for f in files:
            arr = np.load(f).astype(np.float32)
            all_chunks.extend(array_to_chunks(arr))

        np.random.shuffle(all_chunks)
        n_val = max(1, int(len(all_chunks) * val_ratio))
        val_chunks   = all_chunks[:n_val]
        train_chunks = all_chunks[n_val:]

        tr_X, tr_y = chunks_to_windows(train_chunks, cls_idx)
        va_X, va_y = chunks_to_windows(val_chunks,   cls_idx)

        X_train.extend(tr_X); y_train.extend(tr_y)
        X_val.extend(va_X);   y_val.extend(va_y)

        print(f"  {label}: 청크={len(all_chunks)} → train {len(train_chunks)} ({len(tr_X)}윈도우) / val {len(val_chunks)} ({len(va_X)}윈도우)")

    return (
        np.array(X_train, dtype=np.float32), np.array(y_train, dtype=np.int32),
        np.array(X_val,   dtype=np.float32), np.array(y_val,   dtype=np.int32),
    )


def preprocess(windows: np.ndarray) -> np.ndarray:
    # windows: (N, 20, 64)
    amp = np.clip(windows / 20.0, 0.0, 1.0)

    diff = np.diff(windows, axis=1, prepend=windows[:, :1, :])
    dop = np.clip(diff / 5.0, -1.0, 1.0)

    return np.stack([amp, dop], axis=-1)  # (N, 20, 64, 2)


L2 = 1e-4


def build_model() -> Model:
    inputs = Input(shape=(WINDOW, 64, 2))

    # CNN — 공간 특징 추출
    x = Conv2D(16, (3, 3), activation="relu", padding="same",
               kernel_regularizer=regularizers.l2(L2))(inputs)
    x = BatchNormalization()(x)
    x = MaxPooling2D((1, 2))(x)   # (20, 32, 16)
    x = Dropout(0.2)(x)

    x = Conv2D(32, (3, 3), activation="relu", padding="same",
               kernel_regularizer=regularizers.l2(L2))(x)
    x = BatchNormalization()(x)
    x = MaxPooling2D((1, 2))(x)   # (20, 16, 32)
    x = Dropout(0.2)(x)

    # LSTM — 시계열 패턴
    x = Reshape((WINDOW, 16 * 32))(x)
    x = LSTM(32, kernel_regularizer=regularizers.l2(L2), unroll=True)(x)
    x = Dropout(0.5)(x)

    x = Dense(16, activation="relu", kernel_regularizer=regularizers.l2(L2))(x)
    outputs = Dense(len(LABELS), activation="softmax")(x)

    model = Model(inputs, outputs)
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def representative_dataset_gen(X_rep: np.ndarray):
    def gen():
        for i in range(min(200, len(X_rep))):
            yield [X_rep[i : i + 1]]
    return gen


def main():
    parser = argparse.ArgumentParser(description="CNN+LSTM 학습 및 TFLite INT8 변환")
    parser.add_argument("--data_dir", default="data/raw")
    parser.add_argument("--output", default="models/activity_cnn_int8.tflite")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--val_ratio", type=float, default=0.2)
    args = parser.parse_args()

    print("=== 데이터 로딩 (파일 단위 분할) ===")
    X_raw_tr, y_train, X_raw_val, y_val = load_windows(args.data_dir, args.val_ratio)
    print(f"train={len(X_raw_tr)}  val={len(X_raw_val)}")

    X_train = preprocess(X_raw_tr)
    X_val   = preprocess(X_raw_val)

    cw = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
    class_weight = {i: cw[i] for i in range(len(cw))}
    print(f"클래스 가중치: {class_weight}")

    print("\n=== 모델 학습 ===")
    model = build_model()
    model.summary()

    callbacks = [
        EarlyStopping(patience=8, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(patience=4, factor=0.5, verbose=1),
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    loss, acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\n검증 정확도: {acc:.4f}  손실: {loss:.4f}")

    print("\n=== TFLite INT8 변환 ===")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset_gen(X_train)
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]

    tflite_model = converter.convert()
    with open(args.output, "wb") as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"저장 완료: {args.output}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
