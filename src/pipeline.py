"""
뷰티판다 카드뉴스 자동화 (추가 비용 0원 버전)

원고와 사진은 Claude가 채팅에서 만들어 '작업함' 이슈에 `/원고` 댓글로 넘깁니다.
  ingest   `/원고` 댓글 → 사진 내려받기 → 카드뉴스 렌더링 → 글마다 검수 이슈
  approve  '승인' 라벨 → 예약 (예정일이 지났거나 급한 글이면 바로 게시)
  publish  (평일 정오) 오늘 올릴 승인된 글 게시
  setup    처음 한 번: 라벨과 작업함 이슈 만들기
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from .imagegen import download as download_image
from .render import IMAGE_KEYS, render_post

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history.json"
KST = dt.timezone(dt.timedelta(hours=9))
MOCK = bool(os.environ.get("MOCK"))
WEEKDAY = "월화수목금토일"
DEFAULT_FOOT = "앞으로도 원장님들께 도움되는\n현실 꿀팁이 계속 올라옵니다"
CAT_LABEL = {"info": "오늘의 정보", "mkt": "오늘의 마케팅", "notice": "오늘의 공지"}
URL_OF = {"img": "imageUrl", "aImg": "aImageUrl", "bImg": "bImageUrl"}

TYPE_FIELDS = {
    "cover": ["headline"],
    "imageText": ["title", "body"],
    "tip": ["number", "title", "body"],
    "quiz": ["number", "question", "sub", "optA", "optB"],
    "table": ["title", "rows", "explanation"],
    "compare": ["title", "aLabel", "aDesc", "bLabel", "bDesc"],
    "kakao": ["label", "messages", "note"],
    "conclusion": ["text", "foot"],
    "gather": ["title", "lines"],
}
PHOTO_TYPES = {"cover": ["img"], "imageText": ["img"], "tip": ["img"], "compare": ["aImg", "bImg"]}


# ───────────────────────── 공통 ─────────────────────────
def cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def jload(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def jsave(p: Path, data):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def today() -> dt.date:
    return dt.datetime.now(KST).date()


def now_str() -> str:
    return dt.datetime.now(KST).isoformat(timespec="minutes")


def ptime() -> str:
    return str(cfg().get("schedule", {}).get("publish_time", "12:00"))


def md(d: str) -> str:
    x = dt.date.fromisoformat(d)
    return f"{x.month}/{x.day}({WEEKDAY[x.weekday()]})"


def parse_json(text: str):
    t = re.sub(r"```(?:json)?", "", text).strip()
    starts = [i for i in (t.find("{"), t.find("[")) if i >= 0]
    if not starts:
        raise ValueError("JSON이 없습니다")
    t = t[min(starts):]
    return json.loads(t[: max(t.rfind("}"), t.rfind("]")) + 1])




def normalize(raw: dict, c: dict) -> dict:
    """Claude가 넘긴 원고를 템플릿 형식으로 정리. 사진은 주소(imageUrl)를 imagePrompt 자리에 키로 둔다."""
    category = raw.get("category") if raw.get("category") in CAT_LABEL else "info"
    slides = []
    for s in raw.get("slides", []):
        t = s.get("type")
        if t not in TYPE_FIELDS:
            continue
        o = {"type": t}
        for k in TYPE_FIELDS[t]:
            v = s.get(k)
            if isinstance(v, list):
                v = "\n".join(
                    f"{'원장' if m.get('from') in ('owner', '원장') else '고객'}: {m.get('text', '')}"
                    if isinstance(m, dict) else str(m) for m in v)
            if v is not None:
                o[k] = str(v)
        for key in PHOTO_TYPES.get(t, []):
            url = s.get(URL_OF[key])
            if url:
                o[IMAGE_KEYS[key]] = str(url)
        if t == "conclusion":
            o.setdefault("foot", DEFAULT_FOOT)
        slides.append(o)
    if not slides or slides[0]["type"] != "cover":
        slides.insert(0, {"type": "cover", "headline": raw.get("topic", "")})
    if not any(s["type"] == "conclusion" for s in slides):
        slides.append({"type": "conclusion", "text": "오늘의 결론", "foot": DEFAULT_FOOT})
    slides = [s for s in slides if s["type"] != "gather"]
    if c["slides"]["gather_slide"] and category != "notice":
        h = c["account"]["handle"]
        slides.append({"type": "gather", "title": "원장님, 이 글은\n**저장**해두세요",
                       "lines": f"🔖 저장해두고 필요할 때 꺼내보기\n📤 옆 샵 원장님께 공유하기\n➕ {h} 팔로우하고 꿀팁 받기"})
    tags = raw.get("hashtags", [])
    return {
        "topic": str(raw.get("topic", "")), "category": category,
        "badge": str(raw.get("badge") or CAT_LABEL[category]), "slides": slides[:10],
        "caption": str(raw.get("caption", "")),
        "hashtags": " ".join(tags) if isinstance(tags, list) else str(tags),
        "factCheck": [str(x) for x in raw.get("factCheck", [])][:10],
    }


def image_file(post_dir: Path, prompt: str) -> Path:
    return post_dir / "images" / (hashlib.md5(prompt.encode()).hexdigest()[:12] + ".jpg")


def post_dir(post_id: str) -> Path:
    return ROOT / "posts" / post_id


def load_script(post_id: str) -> dict:
    return jload(post_dir(post_id) / "script.json", None)


def save_script(post_id: str, script: dict):
    jsave(post_dir(post_id) / "script.json", script)


def sh(*args, input_text=None) -> str:
    if MOCK:
        print("[MOCK]", " ".join(a if len(a) < 60 else a[:60] + "…" for a in args))
        return "https://github.com/o/r/issues/1" if args[:3] == ("gh", "issue", "create") else ""
    r = subprocess.run(args, capture_output=True, text=True, input=input_text)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} 실패: {r.stderr[:400]}")
    return r.stdout.strip()


def git_push(message: str):
    if MOCK:
        return
    sh("git", "config", "user.name", "beautypanda-bot")
    sh("git", "config", "user.email", "bot@users.noreply.github.com")
    sh("git", "add", "-A", "posts", "data")
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        return
    sh("git", "commit", "-m", message)
    import time
    for attempt in range(5):  # 다른 작업과 동시에 올릴 때를 대비해 재시도
        try:
            sh("git", "pull", "--rebase")
            sh("git", "push")
            return
        except RuntimeError:
            if attempt == 4:
                raise
            time.sleep(5 + attempt * 5)


def raw_url(post_id: str, name: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/posts/{post_id}/{name}"


def hist_get(hist: list, post_id: str) -> dict:
    return next(h for h in hist if h["id"] == post_id)


def ensure_labels():
    for name, color in (("카드뉴스", "7B57D6"), ("검수대기", "F4B63B"), ("승인", "5E9E1E"),
                        ("게시완료", "C7B3F5"), ("작업함", "E4572E")):
        sh("gh", "label", "create", name, "--color", color, "--force")


# ───────────────────────── 렌더링 · 검수 ─────────────────────────
def render_post_by_prompt(pid: str, script: dict, rev: int):
    d = post_dir(pid)
    (d / "images").mkdir(parents=True, exist_ok=True)
    links = []
    for i, s in enumerate(script["slides"], start=1):
        for key, pk in IMAGE_KEYS.items():
            p = s.get(pk)
            if p and image_file(d, p).exists():
                link = d / "images" / f"{i:02d}_{key}.jpg"
                link.write_bytes(image_file(d, p).read_bytes())
                links.append(link)
    for old in d.glob("r*_*.jpg"):
        old.unlink()
    render_post(d, script, f"r{rev}")
    for l in links:
        l.unlink()


def review_body(pid: str, script: dict, h: dict, log: list) -> str:
    rev = script.get("rev", 1)
    n = len(script["slides"])
    imgs = "".join(f'<img src="{raw_url(pid, f"r{rev}_{i:02d}.jpg")}" width="240"> ' for i in range(1, n + 1))
    facts = "\n".join(f"- [ ] {f}" for f in script["factCheck"]) or "확인이 필요한 항목이 없어요."
    notes = ("\n\n### 참고\n" + "\n".join(f"- {x}" for x in log)) if log else ""
    when = "승인하면 바로 게시" if h.get("urgent") else f"**{md(h['scheduled'])} {ptime()} 게시 예정**"
    return f"""<!-- post:{pid} rev:{rev} -->
## {script['topic']}
**{script['badge']}** · {n}장 · {rev}번째 버전 · {when}

{imgs}

### 캡션
```text
{script['caption']}

{script['hashtags']}
```

### 게시 전 확인
{facts}
{notes}

---
**이렇게 하시면 돼요**
- 괜찮으면 오른쪽 **Labels**에서 `승인`을 붙이세요. 예정일에 자동으로 올라갑니다.
- 고칠 게 있으면 Claude 채팅에서 말하세요. 예: "10/7 글 표지 문구 더 짧게, 3번째 장 사진은 네일샵으로"
- 올리지 않을 거면 이슈를 닫으면 됩니다.
- '게시 전 확인' 항목이 있으면 이슈 본문을 편집해서 확인한 것에 체크해야 게시돼요.
"""


def finish_post(pid: str, log: list):
    """사진이 준비된 글을 렌더링하고 검수 이슈를 만들거나 갱신."""
    hist = jload(HISTORY, [])
    h = hist_get(hist, pid)
    script = load_script(pid)
    new_issue = not h.get("issue")
    if not new_issue:
        script["rev"] = script.get("rev", 1) + 1
    render_post_by_prompt(pid, script, script.get("rev", 1))
    save_script(pid, script)
    git_push(f"카드뉴스 완성: {pid} r{script.get('rev', 1)}")
    body = review_body(pid, script, h, log)
    if new_issue:
        url = sh("gh", "issue", "create", "--title", f"[{script['badge']}] {script['topic']}", "--body-file", "-",
                 "--label", "카드뉴스", "--label", "검수대기", input_text=body)
        h["issue"] = int(url.rstrip("/").split("/")[-1])
        if MOCK:
            (post_dir(pid) / "issue_preview.md").write_text(body, encoding="utf-8")
    else:
        sh("gh", "issue", "edit", str(h["issue"]), "--body-file", "-", input_text=body)
        try:  # 수정본은 다시 승인받기
            sh("gh", "issue", "edit", str(h["issue"]), "--remove-label", "승인", "--add-label", "검수대기")
        except RuntimeError:
            pass
        sh("gh", "issue", "comment", str(h["issue"]), "--body", "수정본으로 바꿨어요. 위 미리보기를 확인해 주세요.")
    h["status"] = "검수대기"
    jsave(HISTORY, hist)
    git_push(f"기록 업데이트: {pid}")




# ───────────────────────── 명령 ─────────────────────────
def extract_payload(comment: str) -> dict:
    body = re.sub(r"^\s*/원고\s*", "", comment)
    return parse_json(body)


def cmd_ingest():
    """`/원고` 댓글: {"posts":[{scheduled, category, badge, topic, slides, caption, hashtags, factCheck, urgent, replace}]}"""
    c = cfg()
    issue = os.environ.get("ISSUE", "")
    try:
        payload = extract_payload(os.environ.get("COMMENT", ""))
        posts = payload["posts"] if isinstance(payload, dict) else payload
    except Exception as e:
        sh("gh", "issue", "comment", issue, "--body", f"원고를 읽지 못했어요: {type(e).__name__}. 형식을 확인해 주세요.")
        raise SystemExit(1)
    hist = jload(HISTORY, [])
    results = []
    for raw in posts:
        script = normalize(raw, c)
        log: list = []
        pid = raw.get("replace")
        if pid and any(h["id"] == pid for h in hist):
            old = load_script(pid) or {}
            script["rev"] = old.get("rev", 1)  # finish_post가 +1
            h = hist_get(hist, pid)
            h.update(topic=script["topic"], category=script["category"])
            if raw.get("scheduled"):
                h["scheduled"] = raw["scheduled"]
        else:
            scheduled = raw.get("scheduled") or today().isoformat()
            seq = sum(1 for h in hist if h["id"].startswith(scheduled)) + 1
            pid = f"{scheduled}-{seq:02d}"
            script["rev"] = 1
            hist.append({"id": pid, "topic": script["topic"], "category": script["category"], "status": "렌더링",
                         "issue": None, "scheduled": scheduled, "urgent": bool(raw.get("urgent")),
                         "created": now_str()})
        d = post_dir(pid)
        (d / "images").mkdir(parents=True, exist_ok=True)
        for i, s in enumerate(script["slides"], start=1):
            for pk in IMAGE_KEYS.values():
                url = s.get(pk)
                if url and not image_file(d, url).exists():
                    try:
                        download_image(url, image_file(d, url))
                    except Exception as e:
                        log.append(f"{i}번째 장 사진을 내려받지 못해 기본 배경으로 넣었어요 ({type(e).__name__}).")
        save_script(pid, script)
        jsave(HISTORY, hist)
        finish_post(pid, log)
        hist = jload(HISTORY, [])
        results.append(f"- {md(hist_get(hist, pid)['scheduled'])} {script['topic']} → #{hist_get(hist, pid)['issue']}")
    if issue:
        sh("gh", "issue", "comment", issue, "--body", "카드뉴스를 완성해서 검수 요청을 보냈어요.\n" + "\n".join(results))
    print("\n".join(results))


def cmd_setup():
    ensure_labels()
    body = """이 이슈는 **Claude 작업함**이에요. 닫지 말고 그대로 두세요.

매주 Claude에게 **"이번 주 카드뉴스 만들어줘"** 라고 하면, Claude가 원고를 쓰고 힉스필드 무제한 모드로 사진을 만든 뒤
이 이슈에 `/원고` 댓글로 넘깁니다. 그러면 카드뉴스가 완성되고 글마다 검수 요청이 따로 옵니다.
"""
    url = sh("gh", "issue", "create", "--title", "📥 Claude 작업함", "--body", body, "--label", "작업함")
    num = url.rstrip("/").split("/")[-1]
    try:
        sh("gh", "issue", "pin", num)
    except RuntimeError:
        pass
    print("작업함:", url)


def issue_marker(issue: int) -> tuple[str, int, str]:
    body = sh("gh", "issue", "view", str(issue), "--json", "body", "-q", ".body")
    m = re.search(r"<!-- post:(\S+) rev:(\d+) -->", body)
    if not m:
        raise RuntimeError("이 이슈는 카드뉴스 이슈가 아닙니다.")
    return m.group(1), int(m.group(2)), body


def facts_ok(issue: int, body: str) -> bool:
    if "- [ ]" in body:
        sh("gh", "issue", "edit", str(issue), "--remove-label", "승인")
        sh("gh", "issue", "comment", str(issue), "--body",
           "'게시 전 확인'에 체크 안 된 항목이 있어요. 본문을 편집해 확인한 항목에 체크한 뒤 다시 `승인`을 붙여주세요.")
        return False
    return True


def published_today(hist: list) -> bool:
    return any((h.get("published") or "").startswith(today().isoformat()) and not h.get("urgent") for h in hist)


def publish_now(pid: str, issue: int, rev: int):
    from .instagram import InstagramError, publish_carousel
    c = cfg()
    script = load_script(pid)
    urls = [raw_url(pid, f"r{rev}_{i:02d}.jpg") for i in range(1, len(script["slides"]) + 1)]
    caption = f"{script['caption']}\n\n{script['hashtags']}".strip()
    try:
        res = publish_carousel(os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"], urls, caption,
                               c["instagram"]["graph_version"])
    except (InstagramError, KeyError) as e:
        sh("gh", "issue", "comment", str(issue), "--body",
           f"인스타그램 게시에 실패했어요: {e}\n\n토큰이 만료됐거나 권한이 없을 수 있어요. 설정 확인 후 `승인` 라벨을 뗐다가 다시 붙여주세요.")
        raise SystemExit(1)
    sh("gh", "issue", "comment", str(issue), "--body", f"인스타그램에 올렸어요 🎉 {res['permalink']}")
    sh("gh", "issue", "edit", str(issue), "--add-label", "게시완료", "--remove-label", "검수대기")
    sh("gh", "issue", "close", str(issue))
    hist = jload(HISTORY, [])
    hist_get(hist, pid).update(status="게시완료", permalink=res["permalink"], published=now_str())
    jsave(HISTORY, hist)
    git_push(f"게시 완료: {pid}")


def cmd_approve():
    issue = int(os.environ["ISSUE"])
    pid, rev, body = issue_marker(issue)
    if not facts_ok(issue, body):
        return
    hist = jload(HISTORY, [])
    h = hist_get(hist, pid)
    h["status"] = "승인"
    jsave(HISTORY, hist)
    git_push(f"승인: {pid}")
    if h.get("urgent") or (h["scheduled"] <= today().isoformat() and not published_today(hist)):
        publish_now(pid, issue, rev)
    else:
        sh("gh", "issue", "comment", str(issue), "--body", f"승인됐어요. {md(h['scheduled'])} {ptime()}에 올라갑니다.")


def cmd_publish():
    """평일 정오: 예정일이 된 승인 글 중 가장 이른 것 하나 게시."""
    hist = jload(HISTORY, [])
    if published_today(hist):
        print("오늘은 이미 게시했어요.")
        return
    out = sh("gh", "issue", "list", "--label", "승인", "--label", "카드뉴스", "--state", "open",
             "--json", "number", "-q", ".[].number")
    cands = []
    for num in filter(None, out.split("\n")):
        pid, rev, body = issue_marker(int(num))
        h = next((x for x in hist if x["id"] == pid), None)
        if h and not h.get("published") and h.get("scheduled", "9999") <= today().isoformat() and "- [ ]" not in body:
            cands.append((h["scheduled"], pid, int(num), rev))
    if not cands:
        print("오늘 올릴 승인된 글이 없어요.")
        return
    _, pid, num, rev = sorted(cands)[0]
    publish_now(pid, num, rev)


if __name__ == "__main__":
    cmds = {"ingest": cmd_ingest, "approve": cmd_approve, "publish": cmd_publish, "setup": cmd_setup}
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    cmds.get(name, lambda: sys.exit("사용법: python -m src.pipeline " + "|".join(cmds)))()
