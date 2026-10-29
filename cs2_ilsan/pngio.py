"""외부 라이브러리 없이 PNG 쓰기 (numpy + zlib). 블렌더 안팎에서 같이 쓴다."""

import struct
import zlib

import numpy as np


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _write(path, wid, hgt, depth, color_type, raw, level=6):
    ihdr = struct.pack(">IIBBBBB", wid, hgt, depth, color_type, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
                + _chunk(b"IDAT", zlib.compress(raw.tobytes(), level)) + _chunk(b"IEND", b""))


def write_gray16(path, gray16):
    hgt, wid = gray16.shape
    raw = np.empty((hgt, 1 + wid * 2), dtype=np.uint8)
    raw[:, 0] = 0
    raw[:, 1:] = np.ascontiguousarray(gray16.astype(">u2")).view(np.uint8).reshape(hgt, wid * 2)
    _write(path, wid, hgt, 16, 0, raw)


def write_rgb8(path, img):
    """img: (H, W, 3|4) uint8, 행 0 = 위쪽"""
    hgt, wid, ch = img.shape
    raw = np.empty((hgt, 1 + wid * ch), dtype=np.uint8)
    raw[:, 0] = 0
    raw[:, 1:] = img.reshape(hgt, wid * ch)
    _write(path, wid, hgt, 8, 6 if ch == 4 else 2, raw)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def to_u8(c):
    return np.clip(np.round(np.asarray(c) * 255.0), 0, 255).astype(np.uint8)
