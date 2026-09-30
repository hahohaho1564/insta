"""슬라이드 원고를 1080x1350 JPEG로 렌더링. 스튜디오와 같은 템플릿(templates/)을 사용."""
import base64
import io
import json
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
IMAGE_KEYS = {"img": "imagePrompt", "aImg": "aImagePrompt", "bImg": "bImagePrompt"}


def _data_url(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _page_html(slide: dict, category: str, badge: str) -> str:
    css = (TPL / "slides.css").read_text(encoding="utf-8")
    js = (TPL / "slides.js").read_text(encoding="utf-8")
    payload = json.dumps({"slide": slide, "category": category, "badge": badge}, ensure_ascii=False)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800;900&display=swap" rel="stylesheet">
<style>html,body{{margin:0;padding:0;background:#fff}} {css}</style></head>
<body><div id="root"></div>
<script>{js}</script>
<script>
const P = {payload};
state.category = P.category; state.badge = P.badge;
document.getElementById("root").innerHTML = renderSlide(P.slide);
</script></body></html>"""


def render_post(post_dir: Path, script: dict, prefix: str) -> list[Path]:
    """post_dir/images/ 의 사진을 넣어 렌더링하고 post_dir/{prefix}_01.jpg ... 를 만든다."""
    img_dir = post_dir / "images"
    outs = []
    exe = os.environ.get("CHROMIUM_PATH")  # 로컬 테스트용
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        for i, slide in enumerate(script["slides"], start=1):
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            s = {k: v for k, v in slide.items()}
            for key in IMAGE_KEYS:
                f = img_dir / f"{i:02d}_{key}.jpg"
                if f.exists():
                    s[key] = _data_url(f)
            page.set_content(_page_html(s, script["category"], script.get("badge", "")), wait_until="networkidle")
            page.evaluate("() => document.fonts.ready.then(() => true)")
            png = page.locator(".sl").screenshot(type="png")
            out = post_dir / f"{prefix}_{i:02d}.jpg"
            Image.open(io.BytesIO(png)).convert("RGB").save(out, "JPEG", quality=92)
            outs.append(out)
            page.close()
        browser.close()
    return outs
