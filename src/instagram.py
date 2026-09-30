"""인스타그램 공식 API(Graph API)로 캐러셀 게시."""
import time

import requests


class InstagramError(Exception):
    pass


def _call(method: str, url: str, **params):
    r = requests.request(method, url, data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    body = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in body:
        msg = body.get("error", {}).get("message", r.text[:300])
        raise InstagramError(msg)
    return body


def _wait_ready(base: str, container_id: str, token: str, timeout_s: int = 300):
    start = time.time()
    while time.time() - start < timeout_s:
        st = _call("GET", f"{base}/{container_id}", fields="status_code", access_token=token).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise InstagramError(f"미디어 처리 실패: {st}")
        time.sleep(5)
    raise InstagramError("미디어 처리가 너무 오래 걸립니다.")


def publish_carousel(ig_user_id: str, token: str, image_urls: list[str], caption: str, version: str) -> dict:
    if not 2 <= len(image_urls) <= 10:
        raise InstagramError("캐러셀은 2~10장이어야 합니다.")
    base = f"https://graph.facebook.com/{version}"
    children = []
    for url in image_urls:
        c = _call("POST", f"{base}/{ig_user_id}/media", image_url=url, is_carousel_item="true", access_token=token)
        children.append(c["id"])
    for cid in children:
        _wait_ready(base, cid, token)
    carousel = _call("POST", f"{base}/{ig_user_id}/media", media_type="CAROUSEL",
                     children=",".join(children), caption=caption, access_token=token)
    _wait_ready(base, carousel["id"], token)
    published = _call("POST", f"{base}/{ig_user_id}/media_publish", creation_id=carousel["id"], access_token=token)
    info = _call("GET", f"{base}/{published['id']}", fields="permalink", access_token=token)
    return {"media_id": published["id"], "permalink": info.get("permalink", "")}
