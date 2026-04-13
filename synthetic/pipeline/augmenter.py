#!/usr/bin/env python3
"""Audio augmentation component for the synthetic pipeline.

Provides `run_augment(in_dir, out_dir, snr_list, speeds)` which creates
structured augmentation outputs under `out_dir/{snr}/{basename}_s{speed}.wav`.
"""

import argparse
import glob
import os
import shutil
from typing import List

_HAS_SOUNDFILE = True
try:
    import soundfile as sf
    import numpy as np
except Exception:
    _HAS_SOUNDFILE = False


def add_noise_to_signal(sig: "np.ndarray", snr_db: float) -> "np.ndarray":
    sig = sig.astype("float32")
    power_signal = np.mean(sig**2)
    if power_signal <= 0:
        return sig
    snr_lin = 10 ** (snr_db / 10.0)
    noise_power = power_signal / snr_lin
    noise = np.random.normal(scale=np.sqrt(noise_power), size=sig.shape)
    return sig + noise


def speed_perturb(sig: "np.ndarray", sr: int, speed: float) -> "np.ndarray":
    if speed == 1.0:
        return sig
    import librosa

    return librosa.resample(sig, orig_sr=sr, target_sr=int(sr * speed))


def copy_file_variants(
    file_path: str,
    out_dir: str,
    basename: str,
    snr_list: List[float],
    speeds: List[float],
) -> List[str]:
    out_files: List[str] = []
    for snr in snr_list:
        snr_dir = os.path.join(out_dir, str(int(snr)))
        os.makedirs(snr_dir, exist_ok=True)
        for speed in speeds:
            out_path = os.path.join(snr_dir, f"{basename}_s{speed:.2f}.wav")
            try:
                shutil.copy(file_path, out_path)
                out_files.append(out_path)
            except Exception as exc:
                print("copy failed", file_path, exc)
    return out_files


def apply_speed(
    sig: "np.ndarray", sr: int, speed: float
) -> tuple["np.ndarray", int]:
    if speed == 1.0:
        return sig, sr

    try:
        return speed_perturb(sig, sr, speed), int(sr * speed)
    except Exception as exc:
        print("speed perturb failed, skipping perturbation:", exc)
        return sig, sr


def build_augmented_outputs(
    sig: "np.ndarray",
    sr: int,
    out_dir: str,
    basename: str,
    snr_list: List[float],
    speeds: List[float],
) -> List[str]:
    out_files: List[str] = []
    for snr in snr_list:
        snr_dir = os.path.join(out_dir, str(int(snr)))
        os.makedirs(snr_dir, exist_ok=True)
        for speed in speeds:
            out_sig, out_sr = apply_speed(sig, sr, speed)
            out_sig = add_noise_to_signal(out_sig, snr)
            out_path = os.path.join(snr_dir, f"{basename}_s{speed:.2f}.wav")
            sf.write(out_path, out_sig.astype("float32"), out_sr)
            out_files.append(out_path)
    return out_files


def run_augment(
    in_dir: str, out_dir: str, snr_list: List[float], speeds: List[float]
) -> List[str]:
    files: List[str] = glob.glob(os.path.join(in_dir, "*.wav"))
    os.makedirs(out_dir, exist_ok=True)
    out_files: List[str] = []

    for file_path in files:
        basename = os.path.splitext(os.path.basename(file_path))[0]
        if not _HAS_SOUNDFILE:
            out_files.extend(
                copy_file_variants(
                    file_path, out_dir, basename, snr_list, speeds
                )
            )
            continue

        try:
            sig, sr = sf.read(file_path)
            if sig.ndim > 1:
                sig = sig.mean(axis=1)
        except Exception as exc:
            print("skip", file_path, exc)
            continue

        out_files.extend(
            build_augmented_outputs(
                sig, sr, out_dir, basename, snr_list, speeds
            )
        )
    return out_files


def main(argv: List[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in-dir", required=True, help="input audio dir")
    p.add_argument("--out-dir", required=True, help="output dir")
    p.add_argument(
        "--snr",
        nargs="*",
        type=float,
        default=[20.0, 10.0, 0.0],
        help="SNRs in dB",
    )
    p.add_argument(
        "--speeds", nargs="*", type=float, default=[1.0], help="speed factors"
    )
    args = p.parse_args(argv)
    run_augment(args.in_dir, args.out_dir, args.snr, args.speeds)


if __name__ == "__main__":
    main()
