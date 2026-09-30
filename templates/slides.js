/* ---------------- config ---------------- */
const CATS = {
  info: { label: "오늘의 정보", color: "#A8D862", deep: "#5E9E1E" },
  mkt:  { label: "오늘의 마케팅", color: "#F4B63B", deep: "#D48A12" },
  notice: { label: "오늘의 공지", color: "#C7B3F5", deep: "#7B57D6" }
};
const TYPE_NAMES = {
  cover:"표지", imageText:"이미지 + 설명", tip:"번호 팁", quiz:"퀴즈", table:"표",
  compare:"A / B 비교", kakao:"카톡 대화", conclusion:"오늘의 결론", gather:"저장·공유·팔로우"
};
const HANDLE = "@_beauty.panda";
const DEFAULT_FOOT = "앞으로도 원장님들께 도움되는\n현실 꿀팁이 계속 올라옵니다";
const DEFAULT_GATHER = {
  type:"gather", title:"원장님, 이 글은\n**저장**해두세요",
  lines:"🔖 저장해두고 필요할 때 꺼내보기\n📤 옆 샵 원장님께 공유하기\n➕ " + HANDLE + " 팔로우하고 꿀팁 받기"
};

const PANDA = `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><circle cx="48" cy="46" r="30" fill="#1B1B1F"/><circle cx="152" cy="46" r="30" fill="#1B1B1F"/><ellipse cx="100" cy="108" rx="82" ry="76" fill="#fff" stroke="#1B1B1F" stroke-width="5"/><ellipse cx="66" cy="102" rx="22" ry="28" transform="rotate(-25 66 102)" fill="#1B1B1F"/><ellipse cx="134" cy="102" rx="22" ry="28" transform="rotate(25 134 102)" fill="#1B1B1F"/><circle cx="70" cy="100" r="8" fill="#fff"/><circle cx="130" cy="100" r="8" fill="#fff"/><ellipse cx="100" cy="130" rx="11" ry="8" fill="#1B1B1F"/><path d="M88 146q12 10 24 0" stroke="#1B1B1F" stroke-width="5" fill="none" stroke-linecap="round"/><circle cx="52" cy="138" r="11" fill="#F7A9C0"/><circle cx="148" cy="138" r="11" fill="#F7A9C0"/></svg>`;
const QPANDA = `<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg"><g transform="translate(0 30)">${PANDA.replace(/^<svg[^>]*>|<\/svg>$/g,"")}</g><text x="192" y="70" font-size="72" font-weight="900" fill="#1B1B1F" font-family="Noto Sans KR, sans-serif">?</text></svg>`;

/* ---------------- demo post (no AI usage needed to see templates) ---------------- */
const DEMO = {
  topic:"예약금 환불 문의 응대", category:"info", badge:"오늘의 정보",
  slides:[
    {type:"cover", headline:"예약금 환불 문의,\n원장님 **이렇게** 답해보세요"},
    {type:"imageText", title:"규정대로 답했는데\n왜 분쟁이 될까요?", body:"환불 규정을 안내하는 건 맞아요.\n그런데 첫 문장부터 **'불가'로 시작하면**\n고객님은 거절당했다고 느끼세요.\n같은 규정도 말하는 순서가 중요해요.", visualHint:"고객 문의 카톡 캡처 또는 예약 화면"},
    {type:"kakao", label:"❌ 혹시 이렇게 답하고 계신가요?", messages:"고객: 내일 예약 취소하면 예약금 환불되나요?\n원장: 전일 취소는 환불 불가입니다. 예약하실 때 동의하셨어요.", note:"규정만 먼저 던지면\n'안 돌려주려고 한다'고 느끼기 쉬워요."},
    {type:"kakao", label:"✅ 이제 이렇게 답해보세요", messages:"고객: 내일 예약 취소하면 예약금 환불되나요?\n원장: 갑자기 일정이 생기셨군요 😢 안내드린 대로 전일 취소는 예약금이 차감되는데요, 대신 이번 주 안으로 날짜 변경은 가능해요!", note:"**공감 → 규정 → 대안** 순서로 답하면\n같은 규정도 훨씬 부드럽게 전달돼요."},
    {type:"tip", number:"1", title:"예약 확정 문자에\n규정을 한 번 더 넣어두세요", body:"취소 규정을 **한 줄로 요약해서**\n예약 확정 안내에 함께 보내세요.\n미리 본 규정은 '몰랐다'는 말을 줄여줘요.", visualHint:"예약 확정 문자 예시 화면"},
    {type:"conclusion", text:"규정보다 순서가 먼저!\n공감 → 규정 → 대안", foot:DEFAULT_FOOT},
    {...DEFAULT_GATHER}
  ],
  caption:"예약금 환불 문의, 매번 난감하셨죠? 💬\n규정은 그대로 두고 답하는 순서만 바꿔보세요.\n\n문의 올 때 바로 꺼내볼 수 있게 저장해두세요 🔖",
  hashtags:"#뷰티샵원장 #뷰티샵운영 #예약금 #고객응대 #속눈썹샵 #네일샵 #피부관리실 #1인샵 #샵운영팁 #뷰티판다",
  factCheck:[]
};

/* ---------------- state ---------------- */
var state = JSON.parse(JSON.stringify(DEMO));
let cur = 0;
let sample = null, downloads = null, db = null;

/* ---------------- helpers ---------------- */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function rich(text, color, weight){
  let h = esc(text).replace(/\*\*(.+?)\*\*/g, (_, t) => color ? `<span style="color:${color};font-weight:${weight||"inherit"}">${t}</span>` : `<span class="hlv">${t}</span>`);
  return h.replace(/\n/g, "<br>");
}
const plain = s => String(s ?? "").replace(/\*\*/g, "");
function cat(){ return CATS[state.category] || CATS.info; }
function coverSize(t){
  const longest = Math.max(1, ...plain(t).split("\n").map(l=>[...l].length));
  return longest <= 13 ? 78 : Math.max(56, Math.floor(78*13/longest));
}
function badgeText(){ return (state.badge && state.badge.trim()) || cat().label; }
function bgStyle(url){ return url ? `background-image:url('${url}')` : ""; }
function strip(){ return `<div class="strip-bar" style="background:${cat().color}"></div>`; }
function wm(color){ return `<div class="wm" style="color:${color}">뷰티판다</div>`; }
function placeholder(hint){
  return `<div class="ph">${PANDA}<div class="ph-only">${esc(hint || "이미지를 넣어주세요")}</div><div class="ph-only" style="font-size:26px">오른쪽 편집에서 사진 업로드</div></div>`;
}

/* ---------------- slide renderers ---------------- */
function renderSlide(s){
  const c = cat();
  switch(s.type){
    case "cover": return `<div class="sl">
      ${s.img ? `<div class="bgimg" style="${bgStyle(s.img)}"></div>` : `<div class="cov-fallback"><div class="pd">${PANDA}</div></div>`}
      <div class="shade"></div>
      <div class="cov"><span class="pill" style="border-color:${c.color};color:${c.color}">${esc(badgeText())}</span>
      <h1 style="font-size:${coverSize(s.headline)}px">${rich(s.headline, c.color)}</h1></div>
      ${wm("#fff")}${strip()}</div>`;
    case "imageText":
    case "tip": return `<div class="sl">
      <div class="top ${s.img ? "" : "empty"}" style="${bgStyle(s.img)}">${s.img ? "" : placeholder(s.visualHint)}</div>
      <div class="bottom"><h2>${s.type==="tip" ? `<span class="num" style="background:${c.deep}">${esc(s.number||"1")}</span>` : ""}<span>${rich(s.title, c.deep)}</span></h2>
      <div class="body">${rich(s.body)}</div></div>
      ${wm("#141119")}${strip()}</div>`;
    case "quiz": return `<div class="sl quiz">
      <div class="qpill"><span style="background:${c.deep}">QUIZ ${esc(String(s.number||"1").padStart(2,"0"))}</span></div>
      <div class="qq">${rich(s.question, c.deep)}</div>
      <div class="qsub">${rich(s.sub || "원장님은 어떻게 생각하세요?")}</div>
      <div class="qbtns"><div style="border-color:${c.color}">${esc(s.optA||"✅ 괜찮다")}</div><div style="border-color:${c.color}">${esc(s.optB||"❌ 안된다")}</div></div>
      <div class="qpanda">${QPANDA}</div>
      ${wm("#141119")}${strip()}</div>`;
    case "table": {
      const rows = String(s.rows||"").split("\n").map(r=>r.trim()).filter(Boolean).slice(0,6);
      return `<div class="sl table">
      <div class="t-title">${rich(s.title, c.deep)}</div>
      <div class="t-warn">⚠️</div>
      <div class="tbl"><div class="th">문제가 된 표현</div><div class="th">✅ 왜 문제가 됐을까?</div>
      <div class="lc">${rows.map(r=>`<div>${esc(r)}</div>`).join("")}</div>
      <div class="rc"><div>${rich(s.explanation)}</div></div></div>
      ${wm("#141119")}${strip()}</div>`;
    }
    case "compare": return `<div class="sl compare">
      <div class="c-title">${rich(s.title, c.deep)}</div>
      <div class="ccols">
        <div class="ccol"><div class="cbadge" style="background:${c.deep}">A</div><div class="clabel">${esc(s.aLabel)}</div><div class="cimg" style="${bgStyle(s.aImg)}"></div><div class="cdesc">${rich(s.aDesc)}</div></div>
        <div class="ccol"><div class="cbadge" style="background:${c.deep}">B</div><div class="clabel">${esc(s.bLabel)}</div><div class="cimg" style="${bgStyle(s.bImg)}"></div><div class="cdesc">${rich(s.bDesc)}</div></div>
      </div>
      ${wm("#141119")}${strip()}</div>`;
    case "kakao": {
      const msgs = String(s.messages||"").split("\n").map(l=>l.trim()).filter(Boolean).map(l=>{
        const m = l.match(/^(고객|원장)\s*[:：]\s*(.*)$/);
        return m ? {o:m[1]==="원장", t:m[2]} : {o:false, t:l};
      }).slice(0,5);
      return `<div class="sl kakao">
      <div class="k-label"><span>${esc(s.label)}</span></div>
      <div class="msgs">${msgs.map(m=>`<div class="msg ${m.o?"o":"c"}">${esc(m.t)}</div>`).join("")}</div>
      <div class="k-note">${rich(s.note)}</div>
      ${wm("#141119")}${strip()}</div>`;
    }
    case "conclusion": return `<div class="sl dark">
      <div class="d-label">✅ 오늘의 결론</div>
      <div class="d-main">${rich(s.text, c.color)}</div>
      <div class="d-foot">${rich(s.foot || DEFAULT_FOOT)}</div>
      ${wm("#fff")}${strip()}</div>`;
    case "gather": {
      const lines = String(s.lines||"").split("\n").map(l=>l.trim()).filter(Boolean).slice(0,4);
      return `<div class="sl dark">
      <div class="g-title">${rich(s.title, c.color)}</div>
      <div class="g-list">${lines.map(l=>`<div>${esc(l)}</div>`).join("")}</div>
      ${wm("#fff")}${strip()}</div>`;
    }
  }
  return `<div class="sl"></div>`;
}

