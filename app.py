import html
import json
import re
import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta, timezone
from supabase import create_client, Client

st.set_page_config(page_title="라이프 & 스터디 플래너", page_icon="✨", layout="wide")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

KST = timezone(timedelta(hours=9))

def get_kst_today() -> date:
    return datetime.now(KST).date()

START_DATE = date(2026, 11, 23)
END_DATE = date(2026, 12, 23)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
VALID_DATES = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
WD_MAP = {d: i for i, d in enumerate(WEEKDAY_KR)}
CONDITIONS = ["😊 좋음", "😐 보통", "😫 피곤"]

WAKE_HOURS = list(range(5, 13))        # 05:00 ~ 12:00
SLEEP_HOURS = list(range(20, 28))      # 20:00 ~ 03:00 (새벽)
TIME_OPTS_30M = [f"{m // 60:02d}:{m % 60:02d}" for m in range(360, 1441, 30)]

TASK_COLORS = [
    ("#eef2ff", "#6366f1", "#312e81", "🟣"),
    ("#ecfdf5", "#10b981", "#065f46", "🟢"),
    ("#fff7ed", "#f97316", "#9a3412", "🟠"),
    ("#f0f9ff", "#0ea5e9", "#075985", "🔵"),
    ("#fdf2f8", "#ec4899", "#831843", "🩷"),
    ("#fefce8", "#eab308", "#854d0e", "🟡"),
    ("#f3e8ff", "#a855f7", "#581c87", "🪻"),
    ("#f0fdfa", "#14b8a6", "#115e59", "🩵"),
]

all_dates_padded = list(VALID_DATES)
while len(all_dates_padded) % 7 != 0:
    all_dates_padded.append(None)
WEEKS = [all_dates_padded[i:i+7] for i in range(0, len(all_dates_padded), 7)]

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important; color: #0f172a; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    overflow-x: hidden !important;
    max-width: 100vw !important;
}
[data-testid="stDecoration"] { display: none; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 1320px; box-sizing: border-box !important; }
.stApp {
    background-color: #f6f8fc;
    background-image: radial-gradient(at 8% 10%, rgba(129,140,248,.14) 0px, transparent 42%),
                      radial-gradient(at 92% 8%, rgba(56,189,248,.13) 0px, transparent 40%),
                      radial-gradient(at 50% 95%, rgba(167,243,208,.12) 0px, transparent 45%);
    background-attachment: fixed;
}
[data-testid="stSidebar"] { background: rgba(255,255,255,.92); backdrop-filter: blur(14px); border-right: 1px solid rgba(226,232,240,.85); }
.side-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 18px; padding: 14px; box-shadow: 0 6px 18px rgba(15,23,42,.04); margin-bottom: 10px; }
.exam-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 9px; border-radius: 10px; background: #f8fafc; margin-bottom: 6px; font-size: .8rem; }
.exam-dday { font-size: .7rem; font-weight: 800; padding: 2px 7px; border-radius: 999px; background: #eef2ff; color: #4f46e5; white-space: nowrap; }
.mini-bar-bg { width: 100%; height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; margin-top: 10px; }
.mini-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #10b981, #34d399); transition: width .4s ease; }
.hero-wrap { text-align: center; margin-bottom: 20px; }
.hero-pill { display: inline-block; padding: 5px 14px; border-radius: 999px; background: rgba(99,102,241,.1); color: #4f46e5; font-size: .78rem; font-weight: 700; letter-spacing: .04em; margin-bottom: 8px; }
.hero-title { font-size: 2.25rem; font-weight: 900; letter-spacing: -.03em; background: linear-gradient(120deg, #1e1b4b 0%, #4f46e5 55%, #0284c7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
.stat-card { background: rgba(255,255,255,.9); backdrop-filter: blur(12px); border-radius: 20px; padding: 18px 22px; box-shadow: 0 10px 28px rgba(15,23,42,.045); border: 1px solid rgba(255,255,255,.9); min-height: 102px; }
.stat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.stat-label { font-size: .84rem; color: #64748b; font-weight: 700; }
.stat-badge { font-size: .75rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
.stat-value { font-size: 1.65rem; font-weight: 900; letter-spacing: -.02em; }
.sec-header { display: flex; align-items: center; gap: 8px; font-size: 1.12rem; font-weight: 800; color: #1e293b; margin: 18px 0 10px 0; }
.sec-dot { width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #0ea5e9); display: inline-block; flex-shrink: 0; }
[data-testid="stExpander"] { background: rgba(255,255,255,.9) !important; border: 1px solid #e2e8f0 !important; border-radius: 16px !important; box-shadow: 0 4px 14px rgba(15,23,42,.035) !important; }
.week-card { border-radius: 18px; padding: 13px 11px; min-height: 185px; margin-bottom: 8px; box-shadow: 0 6px 18px rgba(15,23,42,.04); transition: transform .18s ease; }
.week-card:hover { transform: translateY(-2px); }
.week-date { font-weight: 800; font-size: .92rem; margin-bottom: 10px; padding-bottom: 7px; border-bottom: 1px solid rgba(148,163,184,.18); display: flex; justify-content: space-between; align-items: center; }
.today-chip { font-size: .65rem; font-weight: 800; background: #f59e0b; color: #fff; padding: 2px 6px; border-radius: 999px; margin-left: 4px; }
.sch-item { font-size: .75rem; line-height: 1.38; padding: 5px 8px; border-radius: 8px; margin-bottom: 5px; word-break: break-word; font-weight: 600; }
.fixed-chip-row { font-size: .78rem; padding: 5px 9px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; margin-bottom: 4px; color: #334155; word-break: break-word; }
.detail-banner { background: rgba(255,255,255,.92); border: 1px solid #e2e8f0; border-radius: 18px; padding: 14px 20px; margin: 14px 0 12px 0; box-shadow: 0 6px 18px rgba(15,23,42,.04); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
.detail-banner-done { background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 1.5px solid #86efac; }
.hour-lbl { font-size: .8rem; font-weight: 800; color: #64748b; padding-top: 9px; text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.slot-box { border-radius: 11px; padding: 8px 13px; font-size: .85rem; font-weight: 700; min-height: 38px; display: flex; align-items: center; margin-bottom: 4px; word-break: break-word; }
.slot-empty { background: #fff; border: 1.5px dashed #cbd5e1; color: #94a3b8; font-weight: 500; }
.slot-fixed { background: #f1f5f9; border-left: 4px solid #94a3b8; color: #475569; }
.st-card-hdr { display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; }
.st-card-title { font-size: 1.02rem; font-weight: 900; letter-spacing: .02em; color: #0f172a; }
.st-card-total { font-size: .9rem; font-weight: 700; color: #475569; }

/* 기존 한달 달력 CSS Grid (각 날짜 칸 직접 터치 지원) */
.mcal-wrap { background: rgba(255,255,255,.92); border: 1px solid #e2e8f0; border-radius: 18px; padding: 12px 10px; box-shadow: 0 6px 20px rgba(15,23,42,.04); margin-bottom: 10px; }
.mcal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 5px; }
.mcal-hdr { text-align: center; font-weight: 800; font-size: .82rem; padding: 4px 0 6px 0; }
.mcal-cell {
    border-radius: 12px; padding: 7px 6px; min-height: 74px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-sizing: border-box; overflow: hidden;
    cursor: pointer !important;
    user-select: none;
    -webkit-tap-highlight-color: rgba(79,70,229,.15);
    transition: transform .12s ease, box-shadow .12s ease;
}
.mcal-cell:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,70,229,.12); }
.mcal-cell:active { transform: scale(.96); }
.mcal-empty { background: transparent; border: none; min-height: 40px; }
.mcal-top { display: flex; justify-content: space-between; align-items: center; gap: 2px; font-weight: 800; font-size: .82rem; pointer-events: none; }
.mcal-today-tag { font-size: .58rem; font-weight: 900; background: #f59e0b; color: #fff; padding: 1px 4px; border-radius: 999px; }
.mcal-cnt { font-size: .7rem; font-weight: 700; color: #4f46e5; background: rgba(99,102,241,.1); padding: 1px 5px; border-radius: 6px; display: inline-block; width: fit-content; margin-top: 3px; }
.mcal-prev { font-size: .68rem; color: #64748b; line-height: 1.25; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.stTextArea textarea, .stTextInput input { font-size: 16px !important; line-height: 1.55 !important; border-radius: 14px !important; border: 1.5px solid #e2e8f0 !important; background-color: #fff !important; }
.stTextArea textarea:focus, .stTextInput input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.16) !important; }
.stButton > button { border-radius: 10px !important; font-weight: 700 !important; font-size: .8rem !important; border: 1px solid #e2e8f0 !important; background: #fff !important; color: #334155 !important; padding: .4rem .55rem !important; }
.stButton > button:hover:not(:disabled) { border-color: #6366f1 !important; color: #4f46e5 !important; background: #f5f7ff !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important; color: #fff !important; border: none !important; box-shadow: 0 4px 12px rgba(79,70,229,.28) !important; }
.stButton > button:disabled { background: #eef2ff !important; color: #4f46e5 !important; border: 1px solid #c7d2fe !important; opacity: 1 !important; }
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 8px 22px rgba(15,23,42,.08); border: 1px solid #e2e8f0; }
[data-testid="stFileUploadDropzone"] { border-radius: 14px !important; padding: 12px !important; }
.tt-row-marker, .mob-pair-marker, .cal-hidden-zone { display: none; height: 0; margin: 0; padding: 0; }

/* 달력 셀 터치 트리거용 숨김 버튼 영역 */
.stElementContainer:has(.cal-hidden-zone) + *,
.element-container:has(.cal-hidden-zone) + * {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* 모바일(아이폰) 화면 최적화 */
@media (max-width: 768px) {
    .block-container {
        padding-top: 1.1rem !important;
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
        padding-bottom: 2.2rem !important;
    }
    .hero-wrap { margin-bottom: 12px; }
    .hero-pill { font-size: .7rem; padding: 4px 10px; }
    .hero-title { font-size: 1.55rem; }
    .stat-card { padding: 12px 15px; min-height: auto; border-radius: 16px; }
    .stat-value { font-size: 1.35rem; }
    .sec-header { font-size: 1rem; margin: 14px 0 8px 0; }
    .week-card { min-height: auto; padding: 10px 11px; border-radius: 14px; }
    .detail-banner { padding: 11px 14px; border-radius: 14px; }
    .detail-banner span:first-child { font-size: .92rem !important; }
    .hour-lbl { font-size: .72rem; padding-top: 0; text-align: left; }
    .slot-box { padding: 7px 10px; font-size: .8rem; min-height: 36px; margin-bottom: 0; border-radius: 10px; }

    /* 2~4열 보조 버튼 가로 유지 */
    .stElementContainer:has(.mob-pair-marker) + .stElementContainer [data-testid="stHorizontalBlock"],
    .element-container:has(.mob-pair-marker) + .element-container [data-testid="stHorizontalBlock"],
    .stElementContainer:has(.mob-pair-marker) + [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 6px !important;
        align-items: center !important;
    }
    .stElementContainer:has(.mob-pair-marker) + .stElementContainer [data-testid="stHorizontalBlock"] > div,
    .element-container:has(.mob-pair-marker) + .element-container [data-testid="stHorizontalBlock"] > div,
    .stElementContainer:has(.mob-pair-marker) + [data-testid="stHorizontalBlock"] > div {
        min-width: 0 !important;
        flex: 1 1 0% !important;
    }
    .stElementContainer:has(.mob-pair-marker) + .stElementContainer .stButton > button,
    .element-container:has(.mob-pair-marker) + .element-container .stButton > button,
    .stElementContainer:has(.mob-pair-marker) + [data-testid="stHorizontalBlock"] .stButton > button {
        min-height: 40px !important;
        font-size: .82rem !important;
    }

    /* 타임테이블 행: 시간 + 넓은 일정 카드 1줄 유지 */
    .stElementContainer:has(.tt-row-marker) + .stElementContainer [data-testid="stHorizontalBlock"],
    .element-container:has(.tt-row-marker) + .element-container [data-testid="stHorizontalBlock"],
    .stElementContainer:has(.tt-row-marker) + [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 6px !important;
        align-items: center !important;
        margin-bottom: 5px !important;
    }
    .stElementContainer:has(.tt-row-marker) + .stElementContainer [data-testid="stHorizontalBlock"] > div:nth-child(1),
    .element-container:has(.tt-row-marker) + .element-container [data-testid="stHorizontalBlock"] > div:nth-child(1),
    .stElementContainer:has(.tt-row-marker) + [data-testid="stHorizontalBlock"] > div:nth-child(1) {
        width: 74px !important;
        min-width: 74px !important;
        max-width: 74px !important;
        flex: 0 0 74px !important;
    }
    .stElementContainer:has(.tt-row-marker) + .stElementContainer [data-testid="stHorizontalBlock"] > div:nth-child(2),
    .element-container:has(.tt-row-marker) + .element-container [data-testid="stHorizontalBlock"] > div:nth-child(2),
    .stElementContainer:has(.tt-row-marker) + [data-testid="stHorizontalBlock"] > div:nth-child(2) {
        width: auto !important;
        min-width: 0 !important;
        flex: 1 1 auto !important;
    }

    /* 아이폰 한달 달력 컴팩트 최적화 */
    .mcal-wrap { padding: 8px 6px; border-radius: 14px; }
    .mcal-grid { gap: 3px; }
    .mcal-hdr { font-size: .74rem; padding-bottom: 4px; }
    .mcal-cell { padding: 5px 3px; min-height: 54px; border-radius: 9px; }
    .mcal-top { font-size: .68rem; flex-direction: column; align-items: flex-start; gap: 1px; }
    .mcal-today-tag { font-size: .52rem; padding: 0 3px; }
    .mcal-cnt { font-size: .6rem; padding: 0 4px; margin-top: 2px; }
    .mcal-prev { display: none; }
}
</style>
""", unsafe_allow_html=True)

# 1. 개인별 로그인 게이트
if "current_user" not in st.session_state:
    st.markdown("""
        <div class="hero-wrap" style="margin-top:32px;">
            <div class="hero-pill">MENTOR · MENTEE HABIT PROJECT</div>
            <h1 class="hero-title">라이프 & 스터디 플래너</h1>
        </div>
    """, unsafe_allow_html=True)
    _, mid, _ = st.columns([1.2, 1.6, 1.2])
    with mid:
        with st.container(border=True):
            st.markdown("#### 🔐 내 플래너 열기")
            st.caption("각자 이름과 4자리 비밀번호를 입력하면 나만의 공간에 따로 저장돼요.")
            u_name = st.text_input("이름 (또는 닉네임)", placeholder="예: 홍길동")
            u_pin = st.text_input("비밀번호 (숫자 4자리)", type="password", max_chars=4, placeholder="예: 1234")
            if st.button("🚀 시작하기 / 로그인", use_container_width=True, type="primary"):
                clean_name = re.sub(r"\s+", "", u_name)
                if not clean_name:
                    st.error("이름을 입력해 주세요.")
                elif len(u_pin) != 4 or not u_pin.isdigit():
                    st.error("비밀번호는 숫자 4자리로 입력해 주세요.")
                else:
                    pin_key = f"u_{clean_name}__pin"
                    res = supabase.table("daily_logs").select("*").eq("day_key", pin_key).execute()
                    if res.data:
                        if res.data[0].get("memo") == u_pin:
                            st.session_state["current_user"] = clean_name
                            st.session_state.pop("db_loaded", None)
                            st.rerun()
                        else:
                            st.error("비밀번호가 일치하지 않아요. 다시 확인해 주세요!")
                    else:
                        supabase.table("daily_logs").upsert({"day_key": pin_key, "memo": u_pin, "is_done": False, "photo_url": ""}).execute()
                        st.session_state["current_user"] = clean_name
                        st.session_state.pop("db_loaded", None)
                        st.rerun()
    st.stop()

USER = st.session_state["current_user"]
USER_PREFIX = f"u_{USER}__"

def save_day(day_key):
    supabase.table("daily_logs").upsert({
        "day_key": f"{USER_PREFIX}{day_key}",
        "memo": st.session_state.get(f"memo_{day_key}", ""),
        "is_done": bool(st.session_state.get(f"chk_{day_key}", False)),
        "photo_url": st.session_state.get(f"photo_url_{day_key}", "")
    }).execute()

def get_habit_list():
    raw = st.session_state.get("memo_habit_list", "12시 전 취침, 아침 식사, 물 마시기, 운동 30분, 밤에 폰 안 보기")
    return [h.strip() for h in raw.split(",") if h.strip()]

def save_habits(sel_key):
    checked = [h for h in get_habit_list() if st.session_state.get(f"hab_{sel_key}_{h}", False)]
    hk = f"habits_{sel_key}"
    st.session_state[f"memo_{hk}"] = json.dumps(checked, ensure_ascii=False)
    save_day(hk)

def save_sleep_cond(sel_key):
    data = {
        "wake": st.session_state.get(f"wake_{sel_key}", "07:00"),
        "sleep": st.session_state.get(f"sleep_{sel_key}", "23:30"),
        "cond": st.session_state.get(f"cond_{sel_key}", CONDITIONS[0]),
    }
    sk = f"sleep_{sel_key}"
    st.session_state[f"memo_{sk}"] = json.dumps(data, ensure_ascii=False)
    save_day(sk)

def select_day(target_date, do_scroll: bool = False):
    st.session_state["selected_day"] = target_date
    if do_scroll:
        st.session_state["scroll_to_detail"] = True

TIME_PAT = r"(\d{1,2})\s*(?::\s*(\d{2})|시(?:\s*(\d{1,2})\s*분?)?)"

def parse_time_groups(h_str, m1_str, m2_str) -> int:
    return int(h_str) * 60 + (int(m1_str) if m1_str else (int(m2_str) if m2_str else 0))

def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def fmt_hour_label(h: int) -> str:
    if h < 24:
        return f"{h:02d}:00"
    if h == 24:
        return "24:00 (자정)"
    return f"새벽 {h - 24:02d}:00"

def fmt_slot_range(h: int) -> str:
    return f"{h % 24:02d}:00~{(h + 1) % 24:02d}:00"

def parse_range(range_str: str, default=(420, 1440)):
    m = re.search(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}", (range_str or "").strip())
    if m:
        s = parse_time_groups(m.group(1), m.group(2), m.group(3))
        e = parse_time_groups(m.group(4), m.group(5), m.group(6))
        if e <= s:
            e += 1440
        if 0 <= s < e <= 2160:
            return s, e
    return default

def parse_fixed_schedule(text: str):
    events = []
    for line in (text or "").splitlines():
        m = re.match(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}\s*(.+)", line.strip())
        if m:
            s = parse_time_groups(m.group(1), m.group(2), m.group(3))
            e = parse_time_groups(m.group(4), m.group(5), m.group(6))
            t = m.group(7).strip()
            if e <= s and e <= 240:
                e += 1440
            if e > s and t:
                events.append((s, e, t))
    return sorted(events, key=lambda x: x[0])

def get_free_hours(wd_idx: int, range_str: str):
    wake_min, sleep_min = parse_range(range_str)
    start_h, end_h = max(0, wake_min // 60), min(30, (sleep_min + 59) // 60)
    fixed_events = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_idx}", ""))
    free_h = []
    for h in range(start_h, end_h):
        h_s, h_e = h * 60, (h + 1) * 60
        if not any(s < h_e and e > h_s for s, e, _ in fixed_events):
            free_h.append(h)
    return free_h

def extract_task_hours(label: str):
    m_hb = re.search(r"\s*\((\d+)\s*시간\s*반\)\s*$", label)
    if m_hb:
        return label[:m_hb.start()].strip(), int(m_hb.group(1)) + 1
    m_hm = re.search(r"\s*\((\d+)\s*시간\s*(\d+)\s*분\)\s*$", label)
    if m_hm:
        hrs = max(1, (int(m_hm.group(1)) * 60 + int(m_hm.group(2)) + 59) // 60)
        return label[:m_hm.start()].strip(), hrs
    m_h = re.search(r"\s*\((\d+)\s*시간\)\s*$", label)
    if m_h:
        return label[:m_h.start()].strip(), max(1, int(m_h.group(1)))
    m_m = re.search(r"\s*\((\d+)\s*분\)\s*$", label)
    if m_m:
        return label[:m_m.start()].strip(), max(1, (int(m_m.group(1)) + 59) // 60)
    return label.strip(), 1

def save_wake_sleep_dropdowns():
    wh = int(st.session_state.get("ui_wake_h", 7))
    sh = int(st.session_state.get("ui_sleep_h", 24))
    end_h_24 = sh if sh <= 24 else (sh - 24)
    st.session_state["memo_fixed_range"] = f"{wh:02d}:00-{end_h_24:02d}:00"
    save_day("fixed_range")

def add_fixed_event_visual(name: str, selected_wds, start_str: str, end_str: str):
    s_h, s_m = map(int, start_str.split(":"))
    e_h, e_m = map(int, end_str.split(":"))
    s_tot, e_tot = s_h * 60 + s_m, e_h * 60 + e_m
    if e_tot <= s_tot:
        return "종료 시간은 시작 시간보다 늦어야 해요."
    for wd_i in selected_wds:
        evs = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_i}", ""))
        if (s_tot, e_tot, name) not in evs:
            evs.append((s_tot, e_tot, name))
        evs.sort(key=lambda x: x[0])
        st.session_state[f"memo_fixed_{wd_i}"] = "\n".join(f"{to_hhmm(s)}-{to_hhmm(e)} {t}" for s, e, t in evs)
        save_day(f"fixed_{wd_i}")
    return ""

def remove_fixed_event_visual(wd_i: int, target_ev):
    evs = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_i}", ""))
    evs = [ev for ev in evs if ev != target_ev]
    st.session_state[f"memo_fixed_{wd_i}"] = "\n".join(f"{to_hhmm(s)}-{to_hhmm(e)} {t}" for s, e, t in evs)
    save_day(f"fixed_{wd_i}")

def update_fixed_event_visual(old_wd: int, old_ev, new_wd: int, new_name: str, new_start_str: str, new_end_str: str):
    s_h, s_m = map(int, new_start_str.split(":"))
    e_h, e_m = map(int, new_end_str.split(":"))
    s_tot, e_tot = s_h * 60 + s_m, e_h * 60 + e_m
    if e_tot <= s_tot:
        return "종료 시간은 시작 시간보다 늦어야 해요."
    remove_fixed_event_visual(old_wd, old_ev)
    evs = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{new_wd}", ""))
    if (s_tot, e_tot, new_name) not in evs:
        evs.append((s_tot, e_tot, new_name))
    evs.sort(key=lambda x: x[0])
    st.session_state[f"memo_fixed_{new_wd}"] = "\n".join(f"{to_hhmm(s)}-{to_hhmm(e)} {t}" for s, e, t in evs)
    save_day(f"fixed_{new_wd}")
    return ""

def clear_all_fixed_schedules():
    st.session_state["memo_fixed_range"] = "07:00-24:00"
    save_day("fixed_range")
    for wd_i in range(7):
        st.session_state[f"memo_fixed_{wd_i}"] = ""
        save_day(f"fixed_{wd_i}")

def split_into_chunks(total: int, parts: int):
    base, rem = total // parts, total % parts
    return [base + (1 if i < rem else 0) for i in range(parts)]

def parse_exam_schedule(text: str, today_dt: date):
    items = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"(\d{1,2})\s*(?:/|-|\.|월)\s*(\d{1,2})\s*일?\s*(.+)", line)
        if m:
            mo, dy, subj = int(m.group(1)), int(m.group(2)), m.group(3).strip(" :-")
            try:
                dt = date(2026, mo, dy)
                diff = (dt - today_dt).days
                dday = f"D-{diff}" if diff > 0 else ("D-DAY" if diff == 0 else f"D+{abs(diff)}")
                items.append((dt, f"{mo}/{dy} ({WEEKDAY_KR[dt.weekday()]})", subj, dday))
            except ValueError:
                items.append((date(2099, 1, 1), "", line, ""))
        else:
            items.append((date(2099, 1, 1), "", line, ""))
    return sorted(items, key=lambda x: x[0])

def parse_tasks(text: str):
    tasks = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        hours = 1
        dur_txt = ""
        for pat, h_fn, txt_fn in [
            (r"(?:각각\s*)?(\d+)\s*시간\s*반(?:씩)?", lambda m: int(m.group(1)) + 1, lambda m: f"{m.group(1)}시간 반"),
            (r"(?:각각\s*)?(\d+)\s*시간\s*(\d+)\s*분(?:씩)?", lambda m: max(1, (int(m.group(1))*60 + int(m.group(2)) + 59)//60), lambda m: f"{m.group(1)}시간 {m.group(2)}분"),
            (r"(?:각각\s*)?(\d+)\s*시간(?:씩)?", lambda m: max(1, int(m.group(1))), lambda m: f"{m.group(1)}시간"),
            (r"(?:각각\s*)?(\d+)\s*분(?:씩)?", lambda m: max(1, (int(m.group(1)) + 59)//60), lambda m: f"{m.group(1)}분"),
        ]:
            mm = re.search(pat, line)
            if mm:
                hours = h_fn(mm)
                dur_txt = txt_fn(mm)
                line = (line[:mm.start()] + " " + line[mm.end():]).strip()
                break

        allowed_days = None
        m_rng = re.search(r"([월화수목금토일])(?:요일)?\s*[-~]\s*([월화수목금토일])(?:요일)?(?:\s*중에|\s*중|\s*사이)?", line)
        if m_rng:
            s_i, e_i = WD_MAP[m_rng.group(1)], WD_MAP[m_rng.group(2)]
            allowed_days = list(range(s_i, e_i + 1)) if s_i <= e_i else (list(range(s_i, 7)) + list(range(0, e_i + 1)))
            line = (line[:m_rng.start()] + " " + line[m_rng.end():]).strip()
        elif re.search(r"평일(?:\s*중에|\s*중)?", line):
            allowed_days = [0, 1, 2, 3, 4]
            line = re.sub(r"평일(?:\s*중에|\s*중)?", " ", line).strip()
        elif re.search(r"주말(?:\s*중에|\s*중)?", line):
            allowed_days = [5, 6]
            line = re.sub(r"주말(?:\s*중에|\s*중)?", " ", line).strip()

        specific_days = None
        m_list = re.search(r"(?:[월화수목금토일]요일(?:\s*[,/·]\s*[월화수목금토일]요일)*)|(?:[월화수목금토일](?:\s*[,/·]\s*[월화수목금토일])+)", line)
        if m_list:
            found = re.findall(r"[월화수목금토일]", m_list.group(0))
            specific_days = list(dict.fromkeys(WD_MAP[ch] for ch in found))
            line = (line[:m_list.start()] + " " + line[m_list.end():]).strip()
        else:
            m_comp = re.search(r"(?<![가-힣])([월화수목금토일]{2,6})(?:요일)?(?![가-힣])", line)
            if m_comp:
                specific_days = list(dict.fromkeys(WD_MAP[ch] for ch in m_comp.group(1)))
                line = (line[:m_comp.start()] + " " + line[m_comp.end():]).strip()
            else:
                m_one = re.search(r"(?<![가-힣])([월화수목금토일])요일(?![가-힣])", line)
                if m_one:
                    specific_days = [WD_MAP[m_one.group(1)]]
                    line = (line[:m_one.start()] + " " + line[m_one.end():]).strip()

        rounds = 1
        m_rnd = re.search(r"(?:[*xX×]\s*)?(\d+)\s*회독", line)
        if m_rnd:
            rounds = max(1, int(m_rnd.group(1)))
            line = (line[:m_rnd.start()] + " " + line[m_rnd.end():]).strip()

        m_multi = re.search(r"(?:총\s*)?(\d+)\s*(지문|단원|과|강|챕터).*?각각\s*(\d+)\s*(?:번|회)씩?", line)
        if m_multi:
            n_items, unit, reps = int(m_multi.group(1)), m_multi.group(2), int(m_multi.group(3))
            title = (line[:m_multi.start()] + line[m_multi.end():]).strip(" ,/-:") or raw.strip()
            sessions = [f"{title} ({i}{unit} {r}/{reps}회)" for r in range(1, reps + 1) for i in range(1, n_items + 1)]
            tasks.append({"mode": "sessions", "sessions": sessions, "hours": hours, "is_weekly_repeat": False})
            continue

        freq, is_weekly_repeat = None, False
        if specific_days:
            freq, is_weekly_repeat = len(specific_days), True
        elif re.search(r"매일|하루에\s*한\s*번", line):
            freq, is_weekly_repeat = 7, True
            line = re.sub(r"매일|하루에\s*한\s*번", " ", line).strip()
        elif re.search(r"이틀에\s*한\s*번|격일", line):
            freq, is_weekly_repeat = 4, True
            line = re.sub(r"이틀에\s*한\s*번|격일", " ", line).strip()
        else:
            m_freq = re.search(r"(?:일주일에\s*|주에\s*|주\s*)?(\d+)\s*(일|번|회)(?:씩)?", line)
            if m_freq:
                freq = int(m_freq.group(1))
                is_weekly_repeat = bool(
                    allowed_days is not None
                    or re.search(r"일주일에|주에|주\s*\d", m_freq.group(0))
                    or re.search(r"일주일에|주에", line)
                    or dur_txt
                )
                line = (line[:m_freq.start()] + " " + line[m_freq.end():]).strip()

        qty, unit = None, ""
        m_qty = re.search(r"(?:총\s*)?(\d+)\s*(단원|과|강|지문|챕터|회차|문제|페이지|쪽|개|장|p|P)", line)
        if m_qty:
            qty, unit = int(m_qty.group(1)), m_qty.group(2)
            line = (line[:m_qty.start()] + " " + line[m_qty.end():]).strip()

        line = re.sub(r"\b(?:일주일에|주에|중에|각각)\b", " ", line)
        title = re.sub(r"\s+", " ", line).strip(" ,/-:*xX×") or raw.strip()
        if dur_txt and hours > 1:
            base_label = f"{title} ({dur_txt})"
        elif dur_txt and not qty and rounds == 1:
            base_label = f"{title} ({dur_txt})"
        else:
            base_label = title

        tasks.append({
            "mode": "smart", "title": title, "base_label": base_label,
            "qty": qty, "unit": unit, "rounds": rounds, "freq": freq,
            "hours": hours, "specific_days": specific_days, "allowed_days": allowed_days,
            "is_weekly_repeat": is_weekly_repeat,
        })
    return tasks

def format_round_chunk(title: str, unit: str, items):
    groups = []
    for r, u in items:
        if groups and groups[-1][0] == r:
            groups[-1][2] = u
        else:
            groups.append([r, u, u])
    parts = [f"{r}회독 {f'{s_u}{unit}' if s_u == e_u else f'{s_u}~{e_u}{unit}'}" for r, s_u, e_u in groups]
    return f"{title} " + " · ".join(parts)

def load_day_grid(dk: str) -> dict:
    raw = st.session_state.get(f"memo_grid_{dk}", "")
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def auto_fill_day_grid(d: date, task_entries, range_str: str, existing_grid=None):
    dk = d.strftime('%Y_%m_%d')
    free_hours = get_free_hours(d.weekday(), range_str)
    grid = dict(existing_grid) if existing_grid else {}
    used = {int(h_str) for h_str in grid.keys() if h_str.isdigit()}

    ordered_entries = sorted(task_entries, key=lambda x: -max(1, x[1]))
    for label, hrs in ordered_entries:
        hrs = max(1, hrs)
        placed = False
        if hrs > 1 and len(free_hours) >= hrs:
            for i in range(len(free_hours) - hrs + 1):
                block = free_hours[i:i+hrs]
                if all(h not in used for h in block) and all(block[j+1] - block[j] == 1 for j in range(hrs - 1)):
                    for h in block:
                        grid[str(h)] = label
                        used.add(h)
                    placed = True
                    break
        if not placed:
            cnt = 0
            for h in free_hours:
                if h not in used:
                    grid[str(h)] = label
                    used.add(h)
                    cnt += 1
                    if cnt == hrs:
                        break
    st.session_state[f"memo_grid_{dk}"] = json.dumps(grid, ensure_ascii=False)
    save_day(f"grid_{dk}")

def sync_day_tasks_to_grid(d: date, range_str: str):
    dk = d.strftime('%Y_%m_%d')
    tasks = get_day_task_list(dk)
    entries = [(t, extract_task_hours(t)[1]) for t in tasks]
    auto_fill_day_grid(d, entries, range_str, existing_grid={})

def distribute_days_and_grid(active_days, range_str: str, tasks):
    n_days = len(active_days)
    if not n_days or not tasks:
        return
    day_free = {d: len(get_free_hours(d.weekday(), range_str)) for d in active_days}
    day_load = {d: 0 for d in active_days}
    day_entries = {d: [] for d in active_days}
    SEQ_UNITS = {"단원", "과", "강", "지문", "챕터", "회차"}

    def task_priority(t):
        return 0 if t.get("specific_days") else (1 if t.get("allowed_days") else 2)

    for task in sorted(tasks, key=task_priority):
        hrs = task.get("hours", 1)
        if task["mode"] == "sessions":
            for label in task["sessions"]:
                best_d = max(active_days, key=lambda d: (day_free[d] - day_load[d], -len(day_entries[d])))
                day_entries[best_d].append((label, hrs))
                day_load[best_d] += hrs
            continue

        if task.get("rounds", 1) > 1 and task.get("qty"):
            all_items = [(r, u) for r in range(1, task["rounds"] + 1) for u in range(1, task["qty"] + 1)]
            pool = [d for d in active_days if not task.get("allowed_days") or d.weekday() in task["allowed_days"]] or active_days
            chunks = split_into_chunks(len(all_items), len(pool))
            cur = 0
            for d, c in zip(pool, chunks):
                sub = all_items[cur:cur+c]
                cur += c
                if sub:
                    day_entries[d].append((format_round_chunk(task["title"], task["unit"], sub), hrs))
                    day_load[d] += hrs
            continue

        title, base_label = task["title"], task.get("base_label", task["title"])
        qty, unit, freq = task["qty"], task["unit"], task["freq"]
        spec_days, allow_days = task.get("specific_days"), task.get("allowed_days")

        if spec_days:
            chosen = [d for d in active_days if d.weekday() in spec_days]
            k = len(chosen)
        else:
            pool = [d for d in active_days if (not allow_days or d.weekday() in allow_days)] or active_days
            k = min(freq, len(pool)) if freq else (min(qty, len(pool)) if (qty and unit in SEQ_UNITS) else (len(pool) if qty else min(2, len(pool))))
            chosen = sorted(sorted(pool, key=lambda d: (-(day_free[d] - day_load[d]), len(day_entries[d]), d))[:k])

        if not chosen:
            continue

        sessions = []
        if qty and unit in SEQ_UNITS:
            start_num = task.get("start_num", 1)
            if qty >= k:
                cur = start_num
                for c in split_into_chunks(qty, k):
                    end = cur + c - 1
                    sessions.append(f"{title} {cur}{unit}" if cur == end else f"{title} {cur}~{end}{unit}")
                    cur = end + 1
            else:
                sessions = [f"{title} {start_num + (i % qty)}{unit}" for i in range(k)]
        elif qty:
            sessions = [f"{title} {c}{unit}" for c in split_into_chunks(qty, k) if c > 0]
        else:
            sessions = [base_label for _ in range(k)]

        for d, label in zip(chosen, sessions):
            day_entries[d].append((label, hrs))
            day_load[d] += hrs

    for d in active_days:
        dk = d.strftime('%Y_%m_%d')
        st.session_state[f"memo_{dk}"] = "\n".join(lbl for lbl, _ in day_entries[d])
        st.session_state[f"memo_done_tasks_{dk}"] = "[]"
        st.session_state[f"memo_carried_{dk}"] = ""
        st.session_state[f"chk_{dk}"] = False
        save_day(dk)
        save_day(f"done_tasks_{dk}")
        save_day(f"carried_{dk}")
        auto_fill_day_grid(d, day_entries[d], range_str)

def distribute_exam_total_plan(start_d: date, end_d: date, range_str: str, total_text: str):
    tasks = parse_tasks(total_text)
    if not tasks:
        return
    active_weeks = [(w_idx, [d for d in wk if d is not None and start_d <= d <= end_d]) for w_idx, wk in enumerate(WEEKS)]
    active_weeks = [(w_idx, days) for w_idx, days in active_weeks if days]
    n_wks = len(active_weeks)
    if not n_wks:
        return

    all_active_days = [d for _, days in active_weeks for d in days]
    week_task_objs = {w_idx: [] for w_idx, _ in active_weeks}
    week_summary_lines = {w_idx: [] for w_idx, _ in active_weeks}
    SEQ_UNITS = {"단원", "과", "강", "지문", "챕터", "회차"}

    for task in tasks:
        if task["mode"] == "sessions":
            chunks = split_into_chunks(len(task["sessions"]), n_wks)
            cur = 0
            for (w_idx, _), c in zip(active_weeks, chunks):
                sub = task["sessions"][cur:cur+c]
                cur += c
                if sub:
                    week_task_objs[w_idx].append({"mode": "sessions", "sessions": sub, "hours": task.get("hours", 1)})
                    week_summary_lines[w_idx].append(f"{sub[0]} 외 {len(sub)-1}건" if len(sub) > 1 else sub[0])
            continue

        if task.get("rounds", 1) > 1 and task.get("qty"):
            all_items = [(r, u) for r in range(1, task["rounds"] + 1) for u in range(1, task["qty"] + 1)]
            chunks = split_into_chunks(len(all_items), len(all_active_days))
            day_item_map, cur = {}, 0
            for d, c in zip(all_active_days, chunks):
                day_item_map[d] = all_items[cur:cur+c]
                cur += c
            for w_idx, days_in_wk in active_weeks:
                wk_items = [it for d in days_in_wk for it in day_item_map[d]]
                if wk_items:
                    week_summary_lines[w_idx].append(format_round_chunk(task["title"], task["unit"], wk_items))
                for d in days_in_wk:
                    if day_item_map[d]:
                        lbl = format_round_chunk(task["title"], task["unit"], day_item_map[d])
                        week_task_objs[w_idx].append({
                            "mode": "smart", "title": task["title"], "base_label": lbl,
                            "qty": None, "unit": "", "rounds": 1, "freq": 1,
                            "hours": task.get("hours", 1), "specific_days": [d.weekday()],
                            "allowed_days": None, "is_weekly_repeat": True
                        })
            continue

        title, base_label = task["title"], task.get("base_label", task["title"])
        qty, unit, freq, is_wk_rep = task["qty"], task["unit"], task["freq"], task["is_weekly_repeat"]

        if is_wk_rep and not qty:
            for w_idx, _ in active_weeks:
                week_task_objs[w_idx].append(dict(task))
                if task.get("specific_days"):
                    d_names = ",".join(WEEKDAY_KR[i] for i in task["specific_days"])
                    week_summary_lines[w_idx].append(f"{base_label} ({d_names})")
                else:
                    week_summary_lines[w_idx].append(f"{base_label} 주 {freq}회")
        elif qty:
            chunks = split_into_chunks(qty, n_wks)
            cur = 1
            for (w_idx, _), c in zip(active_weeks, chunks):
                if c > 0:
                    t_copy = dict(task)
                    t_copy["qty"], t_copy["start_num"] = c, cur
                    week_task_objs[w_idx].append(t_copy)
                    if unit in SEQ_UNITS:
                        rng = f"{cur}{unit}" if c == 1 else f"{cur}~{cur+c-1}{unit}"
                        week_summary_lines[w_idx].append(f"{title} {rng}")
                    else:
                        week_summary_lines[w_idx].append(f"{title} {c}{unit}")
                    cur += c
        else:
            cnt = freq if freq else n_wks
            chunks = split_into_chunks(cnt, n_wks)
            for (w_idx, _), c in zip(active_weeks, chunks):
                if c > 0:
                    t_copy = dict(task)
                    t_copy["freq"] = c
                    week_task_objs[w_idx].append(t_copy)
                    week_summary_lines[w_idx].append(f"{base_label} {c}회")

    for w_idx, days_in_wk in active_weeks:
        wk_key = f"week_tasks_{w_idx}"
        st.session_state[f"memo_{wk_key}"] = "\n".join(week_summary_lines[w_idx])
        save_day(wk_key)
        distribute_days_and_grid(days_in_wk, range_str, week_task_objs[w_idx])

def get_day_task_list(dk: str):
    return [line.strip() for line in st.session_state.get(f"memo_{dk}", "").splitlines() if line.strip()]

def get_done_tasks_set(dk: str) -> set:
    raw = st.session_state.get(f"memo_done_tasks_{dk}", "")
    try:
        return set(json.loads(raw)) if raw else set()
    except Exception:
        return set()

def toggle_task_done(dk: str, task_label: str):
    day_tasks = get_day_task_list(dk)
    done_set = get_done_tasks_set(dk)
    if task_label in done_set:
        done_set.remove(task_label)
    else:
        done_set.add(task_label)
    st.session_state[f"memo_done_tasks_{dk}"] = json.dumps(list(done_set), ensure_ascii=False)
    save_day(f"done_tasks_{dk}")
    st.session_state[f"chk_{dk}"] = bool(day_tasks and all(t in done_set for t in day_tasks))
    save_day(dk)

def carry_over_uncompleted_to_next_day(src_day: date, range_str: str) -> int:
    next_day = src_day + timedelta(days=1)
    if next_day > END_DATE:
        return 0
    src_dk = src_day.strftime('%Y_%m_%d')
    nxt_dk = next_day.strftime('%Y_%m_%d')

    src_tasks = get_day_task_list(src_dk)
    done_set = get_done_tasks_set(src_dk)
    uncompleted = [t for t in src_tasks if t not in done_set]
    if not uncompleted:
        return 0

    kept_tasks = [t for t in src_tasks if t in done_set]
    st.session_state[f"memo_{src_dk}"] = "\n".join(kept_tasks)
    st.session_state[f"memo_carried_{src_dk}"] = "1"
    if kept_tasks:
        st.session_state[f"chk_{src_dk}"] = True
    save_day(src_dk)
    save_day(f"carried_{src_dk}")

    src_grid = load_day_grid(src_dk)
    cleaned_src_grid = {hk: val for hk, val in src_grid.items() if val not in uncompleted}
    st.session_state[f"memo_grid_{src_dk}"] = json.dumps(cleaned_src_grid, ensure_ascii=False)
    save_day(f"grid_{src_dk}")

    nxt_tasks = get_day_task_list(nxt_dk)
    new_entries = []
    for t in uncompleted:
        clean_t = re.sub(r"^\[이월\]\s*", "", t).strip()
        carried_lbl = f"[이월] {clean_t}"
        if carried_lbl not in nxt_tasks:
            nxt_tasks.append(carried_lbl)
            new_entries.append((carried_lbl, extract_task_hours(clean_t)[1]))

    st.session_state[f"memo_{nxt_dk}"] = "\n".join(nxt_tasks)
    st.session_state[f"chk_{nxt_dk}"] = False
    save_day(nxt_dk)

    if new_entries:
        existing_nxt_grid = load_day_grid(nxt_dk)
        auto_fill_day_grid(next_day, new_entries, range_str, existing_grid=existing_nxt_grid)

    return len(new_entries)

def auto_rollover_past_days():
    today_dt = get_kst_today()
    range_str = st.session_state.get("memo_fixed_range", "07:00-24:00")
    total_moved = 0
    for d in VALID_DATES:
        if d >= today_dt:
            break
        dk = d.strftime('%Y_%m_%d')
        if st.session_state.get(f"chk_{dk}", False):
            continue
        if st.session_state.get(f"memo_carried_{dk}") == "1":
            continue
        moved = carry_over_uncompleted_to_next_day(d, range_str)
        total_moved += moved
    return total_moved

def render_week_task_chips(dk: str) -> str:
    tasks = get_day_task_list(dk)
    done_set = get_done_tasks_set(dk)
    chips = []
    for i, t in enumerate(tasks):
        bg, bd, fg, _ = TASK_COLORS[i % len(TASK_COLORS)]
        is_t_done = t in done_set
        deco = "text-decoration:line-through; opacity:.65;" if is_t_done else ""
        mark = "✓ " if is_t_done else ""
        chips.append(f'<div class="sch-item" style="background:{bg}; border-left:3px solid {bd}; color:{fg}; {deco}">{mark}{html.escape(t)}</div>')
    return "".join(chips)

def move_task_block(dk: str, target_task: str, free_hours, new_start_h=None, step_dir: int = 0):
    if not free_hours:
        return
    grid = load_day_grid(dk)
    cur_indices = [i for i, h in enumerate(free_hours) if grid.get(str(h)) == target_task]
    if not cur_indices:
        return
    k = len(cur_indices)

    if step_dir != 0:
        if step_dir < 0 and cur_indices[0] == 0:
            return
        if step_dir > 0 and cur_indices[-1] >= len(free_hours) - 1:
            return
        start_idx = cur_indices[0] + step_dir
    elif new_start_h is not None and new_start_h in free_hours:
        start_idx = free_hours.index(new_start_h)
    else:
        return

    start_idx = max(0, min(start_idx, len(free_hours) - k))
    target_hours = free_hours[start_idx : start_idx + k]
    old_hours = [free_hours[i] for i in cur_indices]
    if target_hours == old_hours:
        return

    displaced = [grid[str(h)] for h in target_hours if str(h) in grid and grid[str(h)] != target_task]
    vacated = [h for h in old_hours if h not in target_hours]

    for h in old_hours + target_hours:
        grid.pop(str(h), None)
    for h in target_hours:
        grid[str(h)] = target_task
    for h, val in zip(vacated, displaced):
        grid[str(h)] = val

    st.session_state[f"memo_grid_{dk}"] = json.dumps(grid, ensure_ascii=False)
    save_day(f"grid_{dk}")

# 2. 로그인한 사용자 데이터 로드 + 지난 날짜 미완료 할 일 자동 이월
if st.session_state.get("db_loaded") != USER:
    for k in list(st.session_state.keys()):
        if k.startswith(("memo_", "chk_", "photo_url_")):
            del st.session_state[k]
    res_logs = supabase.table("daily_logs").select("*").like("day_key", f"{USER_PREFIX}%").execute()
    for row in res_logs.data:
        dk = row["day_key"][len(USER_PREFIX):]
        st.session_state[f"memo_{dk}"] = row.get("memo", "")
        st.session_state[f"chk_{dk}"] = bool(row.get("is_done", False))
        st.session_state[f"photo_url_{dk}"] = row.get("photo_url", "")
    if not st.session_state.get("memo_fixed_range"):
        st.session_state["memo_fixed_range"] = "07:00-24:00"
    if not st.session_state.get("memo_habit_list"):
        st.session_state["memo_habit_list"] = "12시 전 취침, 아침 식사, 물 마시기, 운동 30분, 밤에 폰 안 보기"
    st.session_state.setdefault("memo_exam_schedule", "")
    st.session_state.setdefault("memo_total_exam_tasks", "")
    moved_cnt = auto_rollover_past_days()
    if moved_cnt > 0:
        st.session_state["rollover_notice"] = f"지난 날짜에 못 끝낸 할 일 {moved_cnt}건이 다음 날 시간표로 자동 이월되었어요!"
    st.session_state["db_loaded"] = USER

today = get_kst_today()

if "selected_day" not in st.session_state:
    st.session_state["selected_day"] = today if START_DATE <= today <= END_DATE else START_DATE

# 사이드바
with st.sidebar:
    uc1, uc2 = st.columns([2.2, 1])
    with uc1:
        st.markdown(f'<div style="font-weight:800; font-size:.95rem; padding-top:4px;">👤 {html.escape(USER)}님</div>', unsafe_allow_html=True)
    with uc2:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    st.divider()

    st.markdown('<div style="font-size:.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">📅 중요 일정 · 시험 시간표</div>', unsafe_allow_html=True)
    exam_items = parse_exam_schedule(st.session_state.get("memo_exam_schedule", ""), today)
    if exam_items:
        rows_html = "".join(
            f'<div class="exam-row"><div><div style="font-weight:800; color:#1e293b;">{html.escape(subj)}</div><div style="font-size:.7rem; color:#64748b;">{dt_lbl}</div></div>'
            + (f'<span class="exam-dday">{dday}</span>' if dday else "") + '</div>'
            for _, dt_lbl, subj, dday in exam_items
        )
        st.markdown(f'<div class="side-card" style="padding:10px 10px 4px 10px;">{rows_html}</div>', unsafe_allow_html=True)
    with st.expander("✏️ 일정 입력 / 수정", expanded=(not bool(exam_items))):
        st.caption("한 줄씩 입력 (예: 12/18 국어, 영어)")
        st.text_area("일정", key="memo_exam_schedule", height=95, label_visibility="collapsed", on_change=save_day, args=("exam_schedule",))

    st.write("")
    st.markdown('<div style="font-size:.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">⏱️ 집중 타이머</div>', unsafe_allow_html=True)
    timer_html = """
    <div style='text-align:center; padding:16px 12px; border-radius:18px; background:#fff; box-shadow:0 8px 22px rgba(15,23,42,.06); border:1px solid #e2e8f0; font-family:Pretendard,sans-serif;'>
        <div id='st' style='font-size:.72rem; font-weight:800; color:#64748b; letter-spacing:.06em;'>READY</div>
        <div id='tm' style='color:#1e293b; font-size:2.4rem; font-weight:900; font-variant-numeric:tabular-nums; margin:4px 0 10px 0;'>00:00</div>
        <div style='margin-bottom:12px;'>
            <input type='number' id='cm' value='50' min='1' style='width:58px; padding:5px; border-radius:9px; border:1.5px solid #e2e8f0; text-align:center; font-weight:800; font-size:16px;'> <span style='font-size:.82rem; font-weight:700; color:#64748b;'>분</span>
        </div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;'>
            <button onclick='go(document.getElementById("cm").value,"FOCUS")' style='padding:8px; cursor:pointer; background:linear-gradient(135deg,#4f46e5,#2563eb); color:#fff; border:none; border-radius:10px; font-weight:700; font-size:.8rem;'>🔥 집중</button>
            <button onclick='go(10,"BREAK")' style='padding:8px; cursor:pointer; background:linear-gradient(135deg,#10b981,#059669); color:#fff; border:none; border-radius:10px; font-weight:700; font-size:.8rem;'>💧 10분 휴식</button>
        </div>
        <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:5px;'>
            <button onclick='resume()' style='padding:6px 2px; cursor:pointer; background:#eef2ff; color:#4f46e5; border:none; border-radius:9px; font-weight:700; font-size:.75rem;'>▶ 재개</button>
            <button onclick='pause()' style='padding:6px 2px; cursor:pointer; background:#f1f5f9; color:#334155; border:none; border-radius:9px; font-weight:700; font-size:.75rem;'>⏸ 정지</button>
            <button onclick='reset()' style='padding:6px 2px; cursor:pointer; background:#f1f5f9; color:#64748b; border:none; border-radius:9px; font-weight:700; font-size:.75rem;'>↺ 초기화</button>
        </div>
        <script>
            let t=null, rem=0, curMode='FOCUS';
            function draw(){ let m=Math.floor(rem/60), s=rem%60; document.getElementById('tm').textContent=(m<10?'0'+m:m)+':'+(s<10?'0'+s:s); }
            function startTick(){
                if(t) return;
                t=setInterval(()=>{
                    if(--rem<0){ clearInterval(t); t=null; rem=0; document.getElementById('tm').textContent='완료! 👏'; document.getElementById('st').textContent='DONE'; }
                    else draw();
                },1000);
            }
            function go(min, mode){ clearInterval(t); t=null; curMode=mode; rem=Math.max(1,parseInt(min)||50)*60; document.getElementById('st').textContent=curMode; draw(); startTick(); }
            function pause(){ if(t){ clearInterval(t); t=null; document.getElementById('st').textContent='PAUSED'; } }
            function resume(){ if(!t && rem>0){ document.getElementById('st').textContent=curMode; startTick(); } }
            function reset(){ clearInterval(t); t=null; rem=0; document.getElementById('tm').textContent='00:00'; document.getElementById('st').textContent='READY'; }
        </script>
    </div>
    """
    components.html(timer_html, height=235)

st.markdown(f"""
    <div class="hero-wrap">
        <div class="hero-pill">2026.11.23 — 12.23 · {html.escape(USER)}'S ROUTINE</div>
        <h1 class="hero-title">라이프 & 스터디 플래너</h1>
    </div>
""", unsafe_allow_html=True)

if st.session_state.get("rollover_notice"):
    st.info(st.session_state.pop("rollover_notice"))

d_day_diff = (END_DATE - today).days
d_day_str = f"D-{d_day_diff}" if d_day_diff > 0 else ("D-DAY 🔥" if d_day_diff == 0 else f"D+{abs(d_day_diff)}")
done_days = sum(1 for d in VALID_DATES if st.session_state.get(f"chk_{d.strftime('%Y_%m_%d')}", False))
done_pct = int((done_days / TOTAL_DAYS) * 100)

m1, m2 = st.columns(2, gap="medium")
with m1:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-top"><span class="stat-label">🔥 프로젝트 종료까지</span><span class="stat-badge" style="background:#eef2ff; color:#4f46e5;">12월 23일</span></div>
            <div class="stat-value" style="color:#4f46e5;">{d_day_str}</div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-top"><span class="stat-label">✅ 전체 달성률</span><span class="stat-badge" style="background:#ecfdf5; color:#059669;">{done_pct}% 완료</span></div>
            <div class="stat-value" style="color:#0f172a;">{done_days} <span style="font-size:1rem; color:#94a3b8; font-weight:700;">/ {TOTAL_DAYS}일</span></div>
            <div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{done_pct}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)

st.write("")
sel_day = st.session_state["selected_day"]
current_week_idx = next((idx for idx, wk in enumerate(WEEKS) if sel_day in wk), 0)
week_labels = [f"{i+1}주차 ({[d for d in w if d][0].month}/{[d for d in w if d][0].day} ~ {[d for d in w if d][-1].month}/{[d for d in w if d][-1].day})" for i, w in enumerate(WEEKS)]

picked_week_label = st.selectbox("📅 주차 선택", week_labels, index=current_week_idx)
picked_week_idx = week_labels.index(picked_week_label)
if picked_week_idx != current_week_idx:
    st.session_state["selected_day"] = [d for d in WEEKS[picked_week_idx] if d][0]
    st.rerun()
active_week = WEEKS[picked_week_idx]

t1, t2 = st.columns(2, gap="medium")
with t1:
    with st.expander("⚙️ 고정 시간표 설정 (클릭형 간편 등록)", expanded=False):
        cur_w, cur_s = parse_range(st.session_state.get("memo_fixed_range", "07:00-24:00"))
        cur_wh = min(max(cur_w // 60, WAKE_HOURS[0]), WAKE_HOURS[-1])
        cur_sh = min(max(cur_s // 60, SLEEP_HOURS[0]), SLEEP_HOURS[-1])
        st.session_state["ui_wake_h"] = cur_wh
        st.session_state["ui_sleep_h"] = cur_sh

        rc1, rc2 = st.columns(2)
        with rc1:
            st.selectbox("🌅 기상 시간", WAKE_HOURS, format_func=fmt_hour_label, key="ui_wake_h", on_change=save_wake_sleep_dropdowns)
        with rc2:
            st.selectbox("🌙 취침 시간", SLEEP_HOURS, format_func=fmt_hour_label, key="ui_sleep_h", on_change=save_wake_sleep_dropdowns)

        st.markdown("---")
        st.markdown("**➕ 학교 · 학원 일정 간편 추가**")
        ev_name = st.text_input("일정 이름", placeholder="예: 학교, 수학학원, 영어학원", key="ui_fix_name")
        st.caption("해당 요일을 모두 체크하세요")
        wd_cols = st.columns(7)
        checked_wds = []
        for idx_w, wd_lbl in enumerate(WEEKDAY_KR):
            with wd_cols[idx_w]:
                if st.checkbox(wd_lbl, value=(idx_w < 5), key=f"ui_fix_wd_{idx_w}"):
                    checked_wds.append(idx_w)

        tc1, tc2 = st.columns(2)
        with tc1:
            ev_start = st.selectbox("시작 시간", TIME_OPTS_30M, index=TIME_OPTS_30M.index("08:00"), key="ui_fix_s")
        with tc2:
            ev_end = st.selectbox("종료 시간", TIME_OPTS_30M, index=TIME_OPTS_30M.index("16:00"), key="ui_fix_e")

        if st.button("➕ 선택한 요일에 일정 추가", use_container_width=True, type="primary"):
            if not ev_name.strip():
                st.warning("일정 이름(예: 학교, 수학학원)을 입력해 주세요.")
            elif not checked_wds:
                st.warning("요일을 하나 이상 체크해 주세요.")
            else:
                err = add_fixed_event_visual(ev_name.strip(), checked_wds, ev_start, ev_end)
                if err:
                    st.warning(err)
                else:
                    st.rerun()

        all_saved_evs = []
        for wd_i in range(7):
            evs = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_i}", ""))
            for ev in evs:
                all_saved_evs.append((wd_i, ev))

        if all_saved_evs:
            st.markdown("---")
            st.markdown("**📋 현재 등록된 고정 일정**")
            for wd_i in range(7):
                evs = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_i}", ""))
                if evs:
                    joined = " · ".join(f"{to_hhmm(s)}~{to_hhmm(e)} {html.escape(t)}" for s, e, t in evs)
                    st.markdown(f'<div class="fixed-chip-row"><b>{WEEKDAY_KR[wd_i]}</b> | {joined}</div>', unsafe_allow_html=True)

            target_choice = st.selectbox(
                "수정 · 삭제할 일정 선택",
                all_saved_evs,
                format_func=lambda x: f"[{WEEKDAY_KR[x[0]]}] {to_hhmm(x[1][0])}~{to_hhmm(x[1][1])} {x[1][2]}",
                key="ui_del_fix_sel"
            )
            dc_e, dc_d, dc_c = st.columns(3)
            with dc_e:
                if st.button("✏️ 수정", use_container_width=True):
                    st.session_state["editing_fixed_item"] = target_choice
                    st.rerun()
            with dc_d:
                if st.button("🗑️ 삭제", use_container_width=True):
                    remove_fixed_event_visual(target_choice[0], target_choice[1])
                    st.session_state.pop("editing_fixed_item", None)
                    st.rerun()
            with dc_c:
                if st.button("🧹 전체 비우기", use_container_width=True):
                    clear_all_fixed_schedules()
                    st.session_state.pop("editing_fixed_item", None)
                    st.rerun()

            edit_item = st.session_state.get("editing_fixed_item")
            if edit_item and edit_item in all_saved_evs:
                old_wd, old_ev = edit_item
                old_s_str, old_e_str, old_name = to_hhmm(old_ev[0]), to_hhmm(old_ev[1]), old_ev[2]
                edit_opts = sorted(set(TIME_OPTS_30M + [old_s_str, old_e_str]))
                uid = f"{old_wd}_{old_ev[0]}_{old_ev[1]}_{old_name}"

                with st.container(border=True):
                    st.markdown(f"**✏️ 일정 수정** (`[{WEEKDAY_KR[old_wd]}] {old_s_str}~{old_e_str} {html.escape(old_name)}`)")
                    ec1, ec2 = st.columns([1, 2])
                    with ec1:
                        new_wd_lbl = st.selectbox("요일", WEEKDAY_KR, index=old_wd, key=f"ed_wd_{uid}")
                    with ec2:
                        new_name = st.text_input("일정 이름", value=old_name, key=f"ed_nm_{uid}")
                    et1, et2 = st.columns(2)
                    with et1:
                        new_s_str = st.selectbox("시작 시간", edit_opts, index=edit_opts.index(old_s_str), key=f"ed_st_{uid}")
                    with et2:
                        new_e_str = st.selectbox("종료 시간", edit_opts, index=edit_opts.index(old_e_str), key=f"ed_et_{uid}")

                    eb1, eb2 = st.columns(2)
                    with eb1:
                        if st.button("💾 수정 저장", use_container_width=True, type="primary", key=f"ed_sv_{uid}"):
                            if not new_name.strip():
                                st.warning("일정 이름을 입력해 주세요.")
                            else:
                                err = update_fixed_event_visual(old_wd, old_ev, WEEKDAY_KR.index(new_wd_lbl), new_name.strip(), new_s_str, new_e_str)
                                if err:
                                    st.warning(err)
                                else:
                                    st.session_state.pop("editing_fixed_item", None)
                                    st.rerun()
                    with eb2:
                        if st.button("취소", use_container_width=True, key=f"ed_cn_{uid}"):
                            st.session_state.pop("editing_fixed_item", None)
                            st.rerun()

with t2:
    with st.expander("⚡ 시험 전까지 전체 할 일 → 주간·일간·시간표 자동 배분", expanded=False):
        tab_all, tab_wk = st.tabs(["🎯 시험 전까지 전체 배분", f"📅 {picked_week_idx+1}주차만 배분"])
        with tab_all:
            dc1, dc2 = st.columns(2)
            with dc1:
                default_s = today if START_DATE <= today <= END_DATE else START_DATE
                plan_start = st.date_input("시작일", value=default_s, min_value=START_DATE, max_value=END_DATE)
            with dc2:
                plan_end = st.date_input("목표 종료일(시험 전날)", value=END_DATE, min_value=START_DATE, max_value=END_DATE)
            st.caption("자유롭게 한 줄씩 입력 (예: 수학 일주일에 일요일,화요일,목요일 각각 2시간 / 국사 총 22단원 * 3회독)")
            st.text_area("전체 할 일", key="memo_total_exam_tasks", height=130, label_visibility="collapsed", on_change=save_day, args=("total_exam_tasks",))
            if st.button("🚀 전체 기간 → 주간 → 일간 → 시간표 자동 배분!", use_container_width=True, type="primary"):
                if plan_start <= plan_end:
                    distribute_exam_total_plan(plan_start, plan_end, st.session_state.get("memo_fixed_range", "07:00-24:00"), st.session_state.get("memo_total_exam_tasks", ""))
                    st.rerun()
                else:
                    st.error("종료일은 시작일 이후로 골라주세요.")
        with tab_wk:
            wk_task_key = f"week_tasks_{picked_week_idx}"
            st.session_state.setdefault(f"memo_{wk_task_key}", "")
            st.caption("이번 주 할 일만 따로 수정해서 다시 배분할 수 있어요.")
            st.text_area("이번 주 할 일", key=f"memo_{wk_task_key}", height=130, label_visibility="collapsed", on_change=save_day, args=(wk_task_key,))
            if st.button(f"⚡ {picked_week_idx+1}주차만 다시 배분하기", use_container_width=True):
                active_d = [d for d in active_week if d is not None]
                distribute_days_and_grid(active_d, st.session_state.get("memo_fixed_range", "07:00-24:00"), parse_tasks(st.session_state.get(f"memo_{wk_task_key}", "")))
                st.rerun()

st.markdown(f'<div class="sec-header"><span class="sec-dot"></span>{week_labels[picked_week_idx]} 요일별 할 일</div>', unsafe_allow_html=True)
w_cols = st.columns(7)
for i, day in enumerate(active_week):
    with w_cols[i]:
        if day is not None:
            dk = day.strftime('%Y_%m_%d')
            is_done = st.session_state.get(f"chk_{dk}", False)
            has_photo = bool(st.session_state.get(f"photo_url_{dk}", ""))
            if day == sel_day:
                bg, border = "#f5f7ff", "2px solid #4f46e5"
            elif is_done:
                bg, border = "#f0fdf4", "1.5px solid #86efac"
            elif day == today:
                bg, border = "#fffbeb", "2px solid #f59e0b"
            else:
                bg, border = "rgba(255,255,255,.92)", "1px solid #e2e8f0"
            day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
            today_chip = '<span class="today-chip">TODAY</span>' if day == today else ""
            icons = ("✅" if is_done else "") + (" 📸" if has_photo else "")
            st.markdown(f"""
                <div class="week-card" style="background:{bg}; border:{border};">
                    <div class="week-date" style="color:{day_color};"><span>{day.month}/{day.day} ({WEEKDAY_KR[i]}){today_chip}</span><span>{icons}</span></div>
                    <div>{render_week_task_chips(dk)}</div>
                </div>
            """, unsafe_allow_html=True)
            st.button("선택됨" if day == sel_day else "상세 보기", key=f"wk_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day, True))
        else:
            st.write("")

# 달력에서 날짜 클릭 시 이동할 목적지 앵커
st.markdown('<div id="daily-timetable-anchor" style="scroll-margin-top: 14px;"></div>', unsafe_allow_html=True)

sel_key = sel_day.strftime('%Y_%m_%d')
sel_wd = WEEKDAY_KR[sel_day.weekday()]
memo_key, chk_key = f"memo_{sel_key}", f"chk_{sel_key}"
st.session_state.setdefault(memo_key, "")
st.session_state.setdefault(chk_key, False)
is_sel_done = st.session_state[chk_key]

st.markdown(f"""
    <div class="detail-banner {'detail-banner-done' if is_sel_done else ''}">
        <span style="font-size:1.05rem; font-weight:800; color:#1e293b;">📌 {sel_day.month}월 {sel_day.day}일 ({sel_wd}) 자동 시간표 & 생활습관</span>
        <span style="font-size:.85rem; font-weight:800; color:#15803d;">{'🎉 오늘 목표 완료!' if is_sel_done else ''}</span>
    </div>
""", unsafe_allow_html=True)

d_left, d_right = st.columns([3, 2], gap="large")

with d_left:
    day_tasks = get_day_task_list(sel_key)
    done_set = get_done_tasks_set(sel_key)
    color_map = {t: TASK_COLORS[idx % len(TASK_COLORS)] for idx, t in enumerate(day_tasks)}
    range_str = st.session_state.get("memo_fixed_range", "07:00-24:00")

    with st.container(border=True):
        st.markdown(f"""
            <div class="st-card-hdr" style="margin-bottom:8px;">
                <span class="st-card-title">📋 오늘의 할 일 체크</span>
                <span class="st-card-total"><b style="color:#4f46e5;">{sum(1 for t in day_tasks if t in done_set)}</b> / {len(day_tasks)}</span>
            </div>
        """, unsafe_allow_html=True)
        if day_tasks:
            for idx_t, t in enumerate(day_tasks):
                dot = color_map[t][3]
                st.checkbox(
                    f"{dot} {t}",
                    value=(t in done_set),
                    key=f"tdone_{sel_key}_{idx_t}_{t}",
                    on_change=toggle_task_done,
                    args=(sel_key, t)
                )
            uncompleted_now = [t for t in day_tasks if t not in done_set]
            if uncompleted_now and sel_day < END_DATE:
                if st.button(f"⏭️ 못 한 할 일({len(uncompleted_now)}건) 다음날로 이월 & 자동 배치", use_container_width=True):
                    moved = carry_over_uncompleted_to_next_day(sel_day, range_str)
                    if moved > 0:
                        st.session_state["rollover_notice"] = f"{moved}건이 {sel_day + timedelta(days=1)} 시간표로 이월 및 자동 배치되었어요!"
                    st.rerun()
        else:
            st.caption("배정된 할 일이 없어요.")

    wake_min, sleep_min = parse_range(range_str)
    start_h, end_h = max(0, wake_min // 60), min(30, (sleep_min + 59) // 60)
    fixed_events = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{sel_day.weekday()}", ""))
    free_hours = get_free_hours(sel_day.weekday(), range_str)
    day_grid = load_day_grid(sel_key)

    placed_blocks = []
    seen_labels = set()
    for h in free_hours:
        val = day_grid.get(str(h))
        if val and val not in seen_labels:
            seen_labels.add(val)
            hrs_of_val = [hh for hh in free_hours if day_grid.get(str(hh)) == val]
            placed_blocks.append((val, hrs_of_val))

    if placed_blocks and len(free_hours) > 1:
        with st.container(border=True):
            st.markdown('<div class="st-card-hdr" style="margin-bottom:8px;"><span class="st-card-title">🔀 시간표 순서 · 시간 바꾸기</span></div>', unsafe_allow_html=True)

            def fmt_placed_opt(item):
                lbl, hrs_list = item
                dot = color_map.get(lbl, ("", "", "", "📌"))[3]
                clean_nm, _ = extract_task_hours(lbl)
                t_span = f"{hrs_list[0]%24:02d}:00~{(hrs_list[-1]+1)%24:02d}:00"
                return f"{dot} {clean_nm} ({t_span})"

            sel_block = st.selectbox(
                "순서나 시간을 바꿀 일정",
                placed_blocks,
                format_func=fmt_placed_opt,
                key=f"mv_blk_{sel_key}"
            )
            chosen_lbl, chosen_hrs = sel_block
            can_up = free_hours.index(chosen_hrs[0]) > 0
            can_dn = free_hours.index(chosen_hrs[-1]) < len(free_hours) - 1

            st.markdown('<div class="mob-pair-marker"></div>', unsafe_allow_html=True)
            mv_c1, mv_c2 = st.columns(2, gap="small")
            with mv_c1:
                if st.button("⬆️ 더 이른 시간으로", use_container_width=True, disabled=(not can_up), key=f"mv_up_{sel_key}"):
                    move_task_block(sel_key, chosen_lbl, free_hours, step_dir=-1)
                    st.rerun()
            with mv_c2:
                if st.button("⬇️ 더 늦은 시간으로", use_container_width=True, disabled=(not can_dn), key=f"mv_dn_{sel_key}"):
                    move_task_block(sel_key, chosen_lbl, free_hours, step_dir=1)
                    st.rerun()

            k_len = len(chosen_hrs)
            valid_starts = free_hours[: max(1, len(free_hours) - k_len + 1)]
            cur_start = chosen_hrs[0] if chosen_hrs[0] in valid_starts else valid_starts[0]

            def fmt_target_time(sh: int):
                eh = (sh + k_len) % 24
                return f"{sh%24:02d}:00 시작 ({sh%24:02d}:00~{eh:02d}:00)"

            st.markdown('<div class="mob-pair-marker"></div>', unsafe_allow_html=True)
            jp_c1, jp_c2 = st.columns([2, 1], gap="small")
            with jp_c1:
                target_sh = st.selectbox(
                    "바로 옮길 시간",
                    valid_starts,
                    index=valid_starts.index(cur_start),
                    format_func=fmt_target_time,
                    label_visibility="collapsed",
                    key=f"jp_sel_{sel_key}_{chosen_lbl}"
                )
            with jp_c2:
                if st.button("✨ 이동", use_container_width=True, type="primary", disabled=(target_sh == chosen_hrs[0]), key=f"jp_btn_{sel_key}"):
                    move_task_block(sel_key, chosen_lbl, free_hours, new_start_h=target_sh)
                    st.rerun()

    slot_totals = {}
    for h in range(start_h, end_h):
        val = day_grid.get(str(h))
        if val:
            slot_totals[val] = slot_totals.get(val, 0) + 1
    slot_seen = {}

    for h in range(start_h, end_h):
        h_s, h_e = h * 60, (h + 1) * 60
        overlapping = [(s, e, title) for s, e, title in fixed_events if s < h_e and e > h_s]
        assigned = day_grid.get(str(h))

        st.markdown('<div class="tt-row-marker"></div>', unsafe_allow_html=True)
        c_time, c_box = st.columns([1.35, 4.65], gap="small")
        with c_time:
            st.markdown(f'<div class="hour-lbl">{fmt_slot_range(h)}</div>', unsafe_allow_html=True)
        with c_box:
            if overlapping:
                labels = []
                for s, e, title in overlapping:
                    if s > h_s or e < h_e:
                        labels.append(f"{title} ({to_hhmm(s)}~{to_hhmm(e)})")
                    else:
                        labels.append(title)
                st.markdown(f'<div class="slot-box slot-fixed">{html.escape(" · ".join(labels))}</div>', unsafe_allow_html=True)
            elif assigned:
                slot_seen[assigned] = slot_seen.get(assigned, 0) + 1
                tot_c = slot_totals.get(assigned, 1)
                cur_c = slot_seen[assigned]
                clean_nm, intended_h = extract_task_hours(assigned)
                if tot_c > 1:
                    disp_lbl = f"{clean_nm} ({cur_c}/{tot_c}시간)"
                elif intended_h > 1:
                    disp_lbl = f"{clean_nm} (1시간)"
                else:
                    disp_lbl = clean_nm
                bg, bd, fg, dot = color_map.get(assigned, ("#f8fafc", "#64748b", "#1e293b", "📌"))
                st.markdown(f'<div class="slot-box" style="background:{bg}; border-left:4px solid {bd}; color:{fg};">{dot} {html.escape(disp_lbl)}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="slot-box slot-empty"></div>', unsafe_allow_html=True)

    st.write("")
    with st.expander("✏️ 오늘 할 일 목록 직접 수정 & 자동 재정렬", expanded=False):
        st.text_area("오늘 할 일 목록", key=memo_key, height=110, label_visibility="collapsed", on_change=save_day, args=(sel_key,))
        if st.button("🔄 수정된 할 일 시간표에 전부 자동 배치", use_container_width=True):
            sync_day_tasks_to_grid(sel_day, range_str)
            st.rerun()
    st.checkbox("✅ 오늘 하루 목표 완료!", key=chk_key, on_change=save_day, args=(sel_key,))

with d_right:
    raw_sl = st.session_state.get(f"memo_sleep_{sel_key}", "")
    try:
        saved_sl = json.loads(raw_sl) if raw_sl else {}
    except Exception:
        saved_sl = {}
    st.session_state.setdefault(f"wake_{sel_key}", saved_sl.get("wake", "07:00"))
    st.session_state.setdefault(f"sleep_{sel_key}", saved_sl.get("sleep", "23:30"))
    st.session_state.setdefault(f"cond_{sel_key}", saved_sl.get("cond", CONDITIONS[0]))

    with st.container(border=True):
        st.markdown('<div class="st-card-hdr" style="margin-bottom:8px;"><span class="st-card-title">😴 수면 & 컨디션</span></div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns(2, gap="small")
        with sc1:
            st.text_input("기상 시간", key=f"wake_{sel_key}", on_change=save_sleep_cond, args=(sel_key,))
        with sc2:
            st.text_input("취침 시간", key=f"sleep_{sel_key}", on_change=save_sleep_cond, args=(sel_key,))
        st.radio("오늘 컨디션", CONDITIONS, horizontal=True, key=f"cond_{sel_key}", on_change=save_sleep_cond, args=(sel_key,))

    habit_list = get_habit_list()
    raw_hab = st.session_state.get(f"memo_habits_{sel_key}", "")
    try:
        saved_hab = set(json.loads(raw_hab)) if raw_hab else set()
    except Exception:
        saved_hab = set()
    done_hab_cnt = 0
    for h in habit_list:
        hk = f"hab_{sel_key}_{h}"
        st.session_state.setdefault(hk, h in saved_hab)
        if st.session_state[hk]:
            done_hab_cnt += 1

    with st.container(border=True):
        st.markdown(f"""
            <div class="st-card-hdr" style="margin-bottom:8px;">
                <span class="st-card-title">🌱 생활습관 체크</span>
                <span class="st-card-total"><b style="color:#10b981;">{done_hab_cnt}</b> / {len(habit_list)}</span>
            </div>
        """, unsafe_allow_html=True)
        for h in habit_list:
            st.checkbox(h, key=f"hab_{sel_key}_{h}", on_change=save_habits, args=(sel_key,))

    with st.expander("✏️ 생활습관 항목 수정", expanded=False):
        st.caption("쉼표(,)로 구분해서 입력")
        st.text_input("습관 목록", key="memo_habit_list", label_visibility="collapsed", on_change=save_day, args=("habit_list",))

    saved_url = st.session_state.get(f"photo_url_{sel_key}", "")
    if saved_url:
        st.image(saved_url, use_container_width=True)
    with st.expander("📤 오늘의 인증 사진 올리기 / 변경하기", expanded=False):
        uploaded_file = st.file_uploader("인증 사진 선택", type=["jpg", "jpeg", "png"], key=f"photo_{sel_key}", label_visibility="collapsed")
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get(f"last_uploaded_{sel_key}") != file_id:
                ext = uploaded_file.name.split(".")[-1].lower()
                file_path = f"{USER}_{sel_key}_{int(time.time())}.{ext}"
                supabase.storage.from_("photos").upload(file_path, uploaded_file.getvalue(), {"content-type": uploaded_file.type})
                st.session_state[f"photo_url_{sel_key}"] = supabase.storage.from_("photos").get_public_url(file_path)
                st.session_state[f"last_uploaded_{sel_key}"] = file_id
                save_day(sel_key)
                st.rerun()

# 한눈에 보는 한달 달력 (기존 카드 모양 유지 + 날짜 칸 직접 터치 시 해당 날짜 시간표로 바로 이동)
st.markdown('<div class="sec-header" style="margin-top:26px;"><span class="sec-dot"></span>한눈에 보는 한달 달력 <span style="font-size:.76rem; font-weight:600; color:#64748b;">(날짜를 터치하면 바로 이동해요)</span></div>', unsafe_allow_html=True)

cal_cells = []
for i, day_name in enumerate(WEEKDAY_KR):
    color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#64748b"
    cal_cells.append(f'<div class="mcal-hdr" style="color:{color};">{day_name}</div>')

for week in WEEKS:
    for i, day in enumerate(week):
        if day is not None:
            dk = day.strftime('%Y_%m_%d')
            day_t_list = get_day_task_list(dk)
            is_done = st.session_state.get(f"chk_{dk}", False)
            has_photo = bool(st.session_state.get(f"photo_url_{dk}", ""))
            if day == sel_day:
                bg, border = "#eef2ff", "2px solid #4f46e5"
            elif is_done:
                bg, border = "#ecfdf5", "1.5px solid #6ee7b7"
            elif day == today:
                bg, border = "#fffbeb", "2px solid #f59e0b"
            else:
                bg, border = "#ffffff", "1px solid #e2e8f0"
            day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
            today_tag = '<span class="mcal-today-tag">TODAY</span>' if day == today else ""
            icons = ("✅" if is_done else "") + ("📸" if has_photo else "")
            cnt_badge = f'<span class="mcal-cnt">{len(day_t_list)}개</span>' if day_t_list else ""
            prev_txt = html.escape(day_t_list[0]) if day_t_list else ""
            cal_cells.append(
                f'<div id="mcal-cell-{dk}" class="mcal-cell" style="background:{bg}; border:{border};">'
                f'<div class="mcal-top" style="color:{day_color};"><span>{day.month}/{day.day} {today_tag}</span><span>{icons}</span></div>'
                f'<div style="pointer-events:none;">{cnt_badge}<div class="mcal-prev">{prev_txt}</div></div>'
                f'</div>'
            )
        else:
            cal_cells.append('<div class="mcal-empty"></div>')

st.markdown(f'<div class="mcal-wrap"><div class="mcal-grid">{"".join(cal_cells)}</div></div>', unsafe_allow_html=True)

# 달력 셀 터치 이벤트를 연결하기 위한 숨김 버튼 묶음
st.markdown('<div class="cal-hidden-zone"></div>', unsafe_allow_html=True)
with st.container():
    for d in VALID_DATES:
        dk = d.strftime('%Y_%m_%d')
        st.button(f"CALJUMP_{dk}", key=f"caljump_{dk}", on_click=select_day, args=(d, True))

st.markdown('<div class="mob-pair-marker"></div>', unsafe_allow_html=True)
nav1, nav2, nav3, nav4 = st.columns([1, 2.3, 1, 1.1], gap="small")
with nav1:
    st.button("◀ 이전 날", use_container_width=True, disabled=(sel_day <= START_DATE), on_click=select_day, args=(sel_day - timedelta(days=1), True), key="nav_prev_btn")
with nav2:
    def fmt_date_opt(d: date):
        t_cnt = len(get_day_task_list(d.strftime('%Y_%m_%d')))
        t_mark = " [TODAY]" if d == today else ""
        return f"{d.month}/{d.day} ({WEEKDAY_KR[d.weekday()]}){t_mark} · 할일 {t_cnt}개"
    jump_day = st.selectbox("날짜 바로 이동", VALID_DATES, index=VALID_DATES.index(sel_day), format_func=fmt_date_opt, label_visibility="collapsed")
    if jump_day != sel_day:
        select_day(jump_day, True)
        st.rerun()
with nav3:
    st.button("다음 날 ▶", use_container_width=True, disabled=(sel_day >= END_DATE), on_click=select_day, args=(sel_day + timedelta(days=1), True), key="nav_next_btn")
with nav4:
    today_target = today if START_DATE <= today <= END_DATE else START_DATE
    st.button("📍 오늘로", use_container_width=True, on_click=select_day, args=(today_target, True), key="nav_today_btn")

# 달력 날짜 셀 터치 바인딩 + 선택 시 하루 시간표로 부드럽게 스크롤
scroll_flag = "true" if st.session_state.pop("scroll_to_detail", False) else "false"
components.html(f"""
    <!-- {time.time()} -->
    <script>
        (function() {{
            try {{
                const doc = window.parent.document;
                if (!doc.body.dataset.mcalBound) {{
                    doc.body.dataset.mcalBound = "1";
                    doc.body.addEventListener("click", function(e) {{
                        const cell = e.target.closest(".mcal-cell");
                        if (!cell || !cell.id || !cell.id.startsWith("mcal-cell-")) return;
                        const dk = cell.id.replace("mcal-cell-", "");
                        const anchor = doc.getElementById("daily-timetable-anchor");
                        if (anchor) {{
                            anchor.scrollIntoView({{ behavior: "smooth", block: "start" }});
                        }}
                        const buttons = doc.querySelectorAll("button");
                        for (const btn of buttons) {{
                            if ((btn.innerText || "").trim() === "CALJUMP_" + dk) {{
                                btn.click();
                                break;
                            }}
                        }}
                    }});
                }}
                if ({scroll_flag}) {{
                    setTimeout(function() {{
                        const anchor = doc.getElementById("daily-timetable-anchor");
                        if (anchor) {{
                            anchor.scrollIntoView({{ behavior: "smooth", block: "start" }});
                        }}
                    }}, 150);
                }}
            }} catch (err) {{}}
        }})();
    </script>
""", height=0)
# 끝
