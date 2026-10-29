"""Blender에 의존하지 않는 순수 로직 (텍스처 채널 패킹, 이름 규칙, 검사).

Blender 밖에서도 테스트할 수 있도록 bpy 를 import 하지 않는다.
"""

import numpy as np

# Cities: Skylines II 임포터가 인식하는 텍스처 접미사 (대소문자 구분)
TEXTURE_SUFFIXES = ("_BaseColor", "_Normal", "_MaskMap", "_ControlMask", "_Emissive")

# MaskMap 채널에 소스가 없을 때 쓰는 기본값 (R=Metallic, G=Coat, B=미사용, A=Glossiness)
MASKMAP_DEFAULTS = (0.0, 0.0, 0.0, 0.5)


def lod_name(asset_name, level):
    """LOD0 은 에셋 이름 그대로, 나머지는 `<이름>_LOD<n>`."""
    return asset_name if level == 0 else f"{asset_name}_LOD{level}"


def texture_name(asset_name, suffix):
    if suffix not in TEXTURE_SUFFIXES:
        raise ValueError(f"알 수 없는 텍스처 접미사: {suffix}")
    return f"{asset_name}{suffix}.png"


def lod_ratios(count, ratio):
    """LOD1..count 에 적용할 누적 Decimate 비율. 예) count=3, ratio=0.5 -> [0.5, 0.25, 0.125]"""
    if not 0.0 < ratio < 1.0:
        raise ValueError("ratio 는 0 과 1 사이여야 합니다")
    return [ratio ** level for level in range(1, count + 1)]


def to_gray(pixels):
    """(H, W, C) float 배열을 (H, W) 회색조로. 이미 회색조 맵이라고 보고 R 채널을 쓴다."""
    pixels = np.asarray(pixels, dtype=np.float32)
    if pixels.ndim == 2:
        return pixels
    return pixels[..., 0]


def pack_channels(size, channels, defaults):
    """채널별 회색조 배열(또는 None)을 (H, W, len(channels)) 배열로 합친다.

    size: (height, width). None 인 채널은 defaults 의 상수로 채운다.
    """
    height, width = size
    out = np.empty((height, width, len(channels)), dtype=np.float32)
    for i, (src, default) in enumerate(zip(channels, defaults)):
        if src is None:
            out[..., i] = default
            continue
        gray = to_gray(src)
        if gray.shape != (height, width):
            raise ValueError(f"채널 {i} 크기 {gray.shape} 가 {size} 와 다릅니다")
        out[..., i] = gray
    return np.clip(out, 0.0, 1.0)


def pack_maskmap(size, metallic=None, coat=None, glossiness=None, roughness=None):
    """MaskMap(RGBA) 생성. roughness 를 주면 1 - roughness 를 Glossiness 로 쓴다."""
    if glossiness is None and roughness is not None:
        glossiness = 1.0 - to_gray(roughness)
    return pack_channels(size, (metallic, coat, None, glossiness), MASKMAP_DEFAULTS)


def pack_controlmask(size, mask1=None, mask2=None, mask3=None):
    """ControlMask(RGB) 생성. 각 채널은 색상 변형 영역 마스크(흰색=적용)."""
    return pack_channels(size, (mask1, mask2, mask3), (0.0, 0.0, 0.0))


def controlmask_overlap(packed, threshold=0.5):
    """두 개 이상의 채널이 threshold 이상인 픽셀 비율 (겹치면 안 됨)."""
    on = np.asarray(packed)[..., :3] >= threshold
    return float(np.mean(on.sum(axis=-1) > 1))


def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def check_textures(sizes):
    """{파일명: (width, height)} 를 받아 경고 문자열 목록을 돌려준다."""
    warnings = []
    for name, (w, h) in sizes.items():
        if w != h:
            warnings.append(f"{name}: 정사각형이 아닙니다 ({w}x{h})")
        if not (is_power_of_two(w) and is_power_of_two(h)):
            warnings.append(f"{name}: 2의 거듭제곱 크기가 아닙니다 ({w}x{h})")
    if len(set(sizes.values())) > 1:
        detail = ", ".join(f"{n}={w}x{h}" for n, (w, h) in sizes.items())
        warnings.append(f"텍스처 해상도가 서로 다릅니다: {detail}")
    return warnings


def png_size(path):
    """PNG 헤더(IHDR)에서 (width, height) 와 채널당 비트 수를 읽는다."""
    with open(path, "rb") as f:
        header = f.read(25)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"PNG 파일이 아닙니다: {path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    bit_depth = header[24]
    return width, height, bit_depth
