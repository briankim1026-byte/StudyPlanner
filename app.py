import html
import re
import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from supabase import create_client, Client

# 1. 화면 기본 설정
st.set_page_config(page_title="프리미엄 스터디 플래너", page_icon="✨", layout="wide")

# 2. Supabase 연결
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# 날짜 범위 설정 (11/23 월요일 ~ 12/23 수요일)
START_DATE = date(2026, 11, 23)
END_DATE = date(2026, 12, 23)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
VALID_DATES = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

# 주차별 묶음 생성
all_dates_padded = list(VALID_DATES)
while len(all_dates_padded) % 7 != 0:
    all_dates_padded.append(None)
WEEKS = [all_dates_padded[i:i+7] for i in range(0, len(all_dates_padded), 7)]

# 3. DB에서 기존 데이터 불러오기
if "db_loaded" not in st.session_state:
    res_set = supabase.table("user_settings").select("*").eq("id", 1).execute()
    if res_set.data:
        row = res_set.data[0]
        st.session_state["math_count"] = int(row.get("math_count", 0))
    else:
        st.session_state["math_count"] = 0

    res_logs = supabase.table("daily_logs").select("*").execute()
    for row in res_logs.data:
        dk = row["day_key"]
        st.session_state[f"memo_{dk}"] = row.get("memo", "")
        st.session_state[f"chk_{dk}"] = bool(row.get("is_done", False))
        st.session_state[f"photo_url_{dk}"] = row.get("photo_url", "")

    if not st.session_state.get("memo_fixed_range"):
        st.session_state["memo_fixed_range"] = "07:00-24:00"

    st.session_state["db_loaded"] = True

if "selected_day" not in st.session_state:
    today = date.today()
    st.session_state["selected_day"] = today if START_DATE <= today <= END_DATE else START_DATE

# 4. 자동 저장 함수
def save_settings():
    supabase.table("user_settings").upsert({
        "id": 1,
        "math_count": int(st.session_state.get("math_count", 0))
    }).execute()

def save_day(day_key):
    supabase.table("daily_logs").upsert({
        "day_key": day_key,
        "memo": st.session_state.get(f"memo_{day_key}", ""),
        "is_done": bool(st.session_state.get(f"chk_{day_key}", False)),
        "photo_url": st.session_state.get(f"photo_url_{day_key}", "")
    }).execute()

def select_day(target_date):
    st.session_state["selected_day"] = target_date

# 5. 유연한 시간 파서
TIME_PAT = r"(\d{1,2})\s*(?::\s*(\d{2})|시(?:\s*(\d{1,2})\s*분?)?)"

def parse_time_groups(h_str, m1_str, m2_str) -> int:
    h = int(h_str)
    m = int(m1_str) if m1_str else (int(m2_str) if m2_str else 0)
    return h * 60 + m

def to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def parse_range(range_str: str):
    m = re.search(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}", range_str.strip())
    if m:
        s = parse_time_groups(m.group(1), m.group(2), m.group(3))
        e = parse_time_groups(m.group(4), m.group(5), m.group(6))
        if e > s:
            return s, e
    return 420, 1440

def parse_fixed_schedule(text: str):
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}\s*(.+)", line)
        if m:
            s_min = parse_time_groups(m.group(1), m.group(2), m.group(3))
            e_min = parse_time_groups(m.group(4), m.group(5), m.group(6))
            title = m.group(7).strip()
            if e_min > s_min and title:
                events.append((s_min, e_min, title))
    events.sort(key=lambda x: x[0])
    return events

def get_free_slots(wake_min: int, sleep_min: int, fixed_events):
    slots = []
    cur = wake_min
    for s, e, _ in fixed_events:
        if s > cur:
            slots.append([cur, min(s, sleep_min)])
        cur = max(cur, e)
    if cur < sleep_min:
        slots.append([cur, sleep_min])
    return slots

def parse_weekly_tasks(text: str):
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        total_min = None
        m_hr = re.search(r"(\d+)\s*시간", line)
        m_min = re.search(r"(\d+)\s*분", line)
        if m_hr:
            total_min = int(m_hr.group(1)) * 60
            line = re.sub(r"\d+\s*시간", "", line).strip()
        elif m_min:
            total_min = int(m_min.group(1))
            line = re.sub(r"\d+\s*분", "", line).strip()

        m_qty = re.search(r"(\d+)\s*(문제|페이지|쪽|강|회|단원|개|p|P)", line)
        if m_qty:
            qty = int(m_qty.group(1))
            unit = m_qty.group(2)
            base_title = (line[:m_qty.start()] + line[m_qty.end():]).strip(" ,/-:")
        else:
            qty, unit = None, ""
            base_title = line.strip(" ,/-:")

        if base_title:
            tasks.append({
                "title": base_title,
                "qty": qty,
                "unit": unit,
                "total_min": total_min
            })
    return tasks

def generate_weekly_schedule(week_dates, range_str: str, weekly_tasks_text: str, break_min: int = 10):
    wake_min, sleep_min = parse_range(range_str)
    active_days = [d for d in week_dates if d is not None]
    n_days = len(active_days)
    if n_days == 0:
        return [], []

    tasks = parse_weekly_tasks(weekly_tasks_text)
    if not tasks:
        return [], []

    day_slots = {}
    day_scheduled = {}
    for d in active_days:
        wd_idx = d.weekday()
        f_txt = st.session_state.get(f"memo_fixed_{wd_idx}", "")
        f_ev = parse_fixed_schedule(f_txt)
        day_slots[d] = get_free_slots(wake_min, sleep_min, f_ev)
        day_scheduled[d] = [(s, e, f"📌 {t}") for s, e, t in f_ev]

    unscheduled = []

    for task in tasks:
        title = task["title"]
        qty = task["qty"]
        unit = task["unit"]
        total_min = task["total_min"]

        if total_min:
            per_day_min = max(20, (total_min // n_days // 5) * 5)
        else:
            per_day_min = 50

        if qty:
            base_q = qty // n_days
            rem_q = qty % n_days
            daily_labels = []
            for idx in range(n_days):
                q_today = base_q + (1 if idx < rem_q else 0)
                if q_today > 0:
                    daily_labels.append((active_days[idx], f"{title} {q_today}{unit}"))
        else:
            daily_labels = [(d, title) for d in active_days]

        for d, label in daily_labels:
            placed = False
            for slot in day_slots[d]:
                if slot[1] - slot[0] >= per_day_min:
                    s_t = slot[0]
                    e_t = s_t + per_day_min
                    day_scheduled[d].append((s_t, e_t, f"📖 {label}"))
                    slot[0] = e_t + break_min
                    placed = True
                    break
            if not placed:
                unscheduled.append(f"{d.month}/{d.day} {label} ({per_day_min}분)")

    for d in active_days:
        dk = d.strftime('%Y_%m_%d')
        day_scheduled[d].sort(key=lambda x: x[0])
        lines = [f"[{to_hhmm(s)} ~ {to_hhmm(e)}] {t}" for s, e, t in day_scheduled[d]]
        st.session_state[f"memo_{dk}"] = "\n".join(lines)
        save_day(dk)

    return active_days, unscheduled

# 주간 카드 안의 일정을 컬러 블록 HTML로 예쁘게 변환
def render_schedule_blocks(memo_txt: str) -> str:
    if not memo_txt.strip():
        return ""
    blocks = []
    for raw_line in memo_txt.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        safe = html.escape(line)
        if "📌" in line:
            blocks.append(f'<div class="sch-item sch-fixed">{safe}</div>')
        elif "📖" in line:
            blocks.append(f'<div class="sch-item sch-study">{safe}</div>')
        else:
            blocks.append(f'<div class="sch-item sch-plain">{safe}</div>')
    return "".join(blocks)

# 6. 프리미엄 디자인 CSS
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #0f172a;
    }

    /* 기본 스트림릿 상단 줄 및 푸터 숨김 */
    [data-testid="stDecoration"] { display: none; }
    footer { visibility: hidden; }
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1320px;
    }

    /* 은은한 파스텔 메쉬 배경 */
    .stApp {
        background-color: #f6f8fc;
        background-image:
            radial-gradient(at 8% 10%, rgba(129, 140, 248, 0.14) 0px, transparent 42%),
            radial-gradient(at 92% 8%, rgba(56, 189, 248, 0.13) 0px, transparent 40%),
            radial-gradient(at 50% 95%, rgba(167, 243, 208, 0.12) 0px, transparent 45%);
        background-attachment: fixed;
    }

    /* 사이드바 고급화 */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.82);
        backdrop-filter: blur(14px);
        border-right: 1px solid rgba(226, 232, 240, 0.85);
    }
    .side-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        margin-bottom: 12px;
    }
    .side-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .mini-bar-bg {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 10px;
    }
    .mini-bar-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #6366f1, #0ea5e9);
        transition: width 0.4s ease;
    }

    /* 히어로 타이틀 */
    .hero-wrap {
        text-align: center;
        margin-bottom: 22px;
    }
    .hero-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 999px;
        background: rgba(99, 102, 241, 0.10);
        color: #4f46e5;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 10px;
    }
    .hero-title {
        font-size: 2.35rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        background: linear-gradient(120deg, #1e1b4b 0%, #4f46e5 55%, #0284c7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }

    /* 상단 메트릭 카드 */
    .stat-card {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 18px 22px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.9);
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 104px;
    }
    .stat-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .stat-label { font-size: 0.84rem; color: #64748b; font-weight: 700; }
    .stat-badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
    }
    .stat-value { font-size: 1.7rem; font-weight: 900; letter-spacing: -0.02em; }

    /* 섹션 헤더 */
    .sec-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.15rem;
        font-weight: 800;
        color: #1e293b;
        margin: 18px 0 10px 0;
        letter-spacing: -0.01em;
    }
    .sec-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5, #0ea5e9);
        display: inline-block;
    }

    /* Expander 카드화 */
    [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.035) !important;
        overflow: hidden;
    }

    /* 주간 시간표 카드 */
    .week-card {
        border-radius: 18px;
        padding: 13px 11px;
        min-height: 215px;
        margin-bottom: 8px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .week-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
    }
    .week-date {
        font-weight: 800;
        font-size: 0.92rem;
        margin-bottom: 10px;
        padding-bottom: 7px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .today-chip {
        font-size: 0.65rem;
        font-weight: 800;
        background: #f59e0b;
        color: #ffffff;
        padding: 2px 6px;
        border-radius: 999px;
        margin-left: 4px;
    }
    .sch-item {
        font-size: 0.74rem;
        line-height: 1.38;
        padding: 5px 7px;
        border-radius: 8px;
        margin-bottom: 5px;
        word-break: break-word;
        font-weight: 500;
    }
    .sch-fixed {
        background: #f1f5f9;
        color: #475569;
        border-left: 3px solid #94a3b8;
    }
    .sch-study {
        background: #eef2ff;
        color: #312e81;
        border-left: 3px solid #6366f1;
    }
    .sch-plain {
        background: #f8fafc;
        color: #334155;
        border-left: 3px solid #cbd5e1;
    }

    /* 일일 상세 패널 헤더 */
    .detail-banner {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 14px 20px;
        margin: 14px 0 12px 0;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .detail-banner-done {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 1.5px solid #86efac;
    }

    /* 월별 컴팩트 달력 카드 */
    .cal-card {
        border-radius: 14px;
        padding: 9px 10px;
        min-height: 76px;
        margin-bottom: 6px;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.03);
        transition: transform 0.15s ease;
    }
    .cal-card:hover { transform: translateY(-1px); }
    .cal-date {
        font-weight: 800;
        font-size: 0.86rem;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .cal-preview {
        font-size: 0.72rem;
        color: #64748b;
        line-height: 1.32;
        word-break: break-all;
    }

    /* 입력창 & 버튼 세련되게 */
    .stTextArea textarea, .stTextInput input {
        font-size: 0.94rem !important;
        line-height: 1.6 !important;
        border-radius: 14px !important;
        border: 1.5px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.16) !important;
    }
    .stButton > button {
        border-radius: 11px !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        border: 1px solid #e2e8f0 !important;
        background: #ffffff !important;
        color: #334155 !important;
        padding: 0.35rem 0.75rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover:not(:disabled) {
        border-color: #6366f1 !important;
        color: #4f46e5 !important;
        background: #f5f7ff !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.28) !important;
    }
    .stButton > button[kind="primary"]:hover {
        filter: brightness(1.06);
        transform: translateY(-1px);
    }
    .stButton > button:disabled {
        background: #eef2ff !important;
        color: #4f46e5 !important;
        border: 1px solid #c7d2fe !important;
        opacity: 1 !important;
    }

    /* 인증 사진 라운드 프레임 */
    [data-testid="stImage"] img {
        border-radius: 16px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        border: 1px solid #e2e8f0;
    }
    [data-testid="stFileUploadDropzone"] {
        border-radius: 14px !important;
        padding: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 7. 사이드바
with st.sidebar:
    math_count = st.session_state.get("math_count", 0)
    math_pct = min(int((math_count / 30.0) * 100), 100)

    st.markdown(f"""
        <div class="side-card">
            <div class="side-title">
                <span>📐 일일 수학 달성도</span>
                <span style="color:#4f46e5; font-size:0.85rem;">{math_pct}%</span>
            </div>
            <div style="font-size:0.78rem; color:#64748b;">목표 30문제 · 현재 <b>{math_count}</b>문제</div>
            <div class="mini-bar-bg">
                <div class="mini-bar-fill" style="width:{math_pct}%;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    math_count = st.number_input("오늘 푼 문제 수", min_value=0, max_value=200, step=1, key="math_count", on_change=save_settings)
    if math_count >= 30:
        st.success("🔥 오늘 수학 목표 달성!")

    st.write("")
    st.markdown('<div style="font-size:0.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">⏱️ 집중 타이머</div>', unsafe_allow_html=True)

    timer_html = """
    <div style='text-align:center; padding:18px 14px; border-radius:18px; background:#ffffff; box-shadow:0 8px 22px rgba(15,23,42,0.06); border:1px solid #e2e8f0; font-family:Pretendard, -apple-system, sans-serif;'>
        <div id='status' style='font-size:0.75rem; font-weight:700; color:#64748b; letter-spacing:0.05em; margin-bottom:4px;'>READY</div>
        <div id='time' style='color:#1e293b; font-size:2.6rem; font-weight:900; font-variant-numeric:tabular-nums; letter-spacing:-0.02em; margin:4px 0 12px 0;'>00:00</div>
        <div style='display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:14px;'>
            <input type='number' id='customMin' value='50' min='1' style='width:62px; padding:6px; border-radius:10px; border:1.5px solid #e2e8f0; text-align:center; font-weight:800; color:#1e293b; font-size:0.95rem;'>
            <span style='font-size:0.85rem; font-weight:700; color:#64748b;'>분 설정</span>
        </div>
        <div style='display:grid
