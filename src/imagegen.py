"""사진 내려받기. Claude가 힉스필드에서 만든 사진 주소를 받아 저장한다."""
import io
import os
from pathlib import Path

import requests
from PIL import Image


def download(url: str, out_path: Path) -> bool:
    if os.environ.get("MOCK"):
        _mock(out_path, url)
        return True
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    Image.open(io.BytesIO(r.content)).convert("RGB").save(out_path, "JPEG", quality=92)
    return True


def _mock(out_path: Path, seed: str):
    """테스트용 가짜 사진."""
    import hashlib
    h = hashlib.md5(seed.encode()).digest()
    top, bottom = (h[0], h[1], h[2]), (h[3] // 3, h[4] // 3, h[5] // 3)
    img = Image.new("RGB", (900, 1200))
    px = img.load()
    for y in range(1200):
        t = y / 1199
        c = tuple(int(top[k] * (1 - t) + bottom[k] * t) for k in range(3))
        for x in range(900):
            px[x, y] = c
    img.save(out_path, "JPEG", quality=85)
