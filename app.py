import html
import json
import re
import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from supabase import create_client, Client

st.set_page_config(page_title="라이프 & 스터디 플래너", page_icon="✨", layout="wide")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

START_DATE = date(2026, 11, 23)
END_DATE = date(2026, 12, 23)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
VALID_DATES = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
CONDITIONS = ["😊 좋음", "😐 보통", "😫 피곤"]

LIFE_BLOCKS = {
    "🍽️ 저녁 식사": ("#fffbeb", "#f59e0b", "#92400e"),
    "🏃 운동/산책": ("#ecfdf5", "#10b981", "#065f46"),
    "🛌 휴식": ("#f0f9ff", "#0ea5e9", "#075985"),
}

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
[data-testid="stDecoration"] { display: none; }
footer { visibility: hidden; }
.block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 1320px; }
.stApp {
    background-color: #f6f8fc;
    background-image: radial-gradient(at 8% 10%, rgba(129,140,248,.14) 0px, transparent 42%),
                      radial-gradient(at 92% 8%, rgba(56,189,248,.13) 0px, transparent 40%),
                      radial-gradient(at 50% 95%, rgba(167,243,208,.12) 0px, transparent 45%);
    background-attachment: fixed;
}
[data-testid="stSidebar"] { background: rgba(255,255,255,.85); backdrop-filter: blur(14px); border-right: 1px solid rgba(226,232,240,.85); }
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
.sec-dot { width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #0ea5e9); display: inline-block; }
[data-testid="stExpander"] { background: rgba(255,255,255,.9) !important; border: 1px solid #e2e8f0 !important; border-radius: 16px !important; box-shadow: 0 4px 14px rgba(15,23,42,.035) !important; }
.week-card { border-radius: 18px; padding: 13px 11px; min-height: 185px; margin-bottom: 8px; box-shadow: 0 6px 18px rgba(15,23,42,.04); transition: transform .18s ease; }
.week-card:hover { transform: translateY(-2px); }
.week-date { font-weight: 800; font-size: .92rem; margin-bottom: 10px; padding-bottom: 7px; border-bottom: 1px solid rgba(148,163,184,.18); display: flex; justify-content: space-between; align-items: center; }
.today-chip { font-size: .65rem; font-weight: 800; background: #f59e0b; color: #fff; padding: 2px 6px; border-radius: 999px; margin-left: 4px; }
.sch-item { font-size: .75rem; line-height: 1.38; padding: 5px 8px; border-radius: 8px; margin-bottom: 5px; word-break: break-word; font-weight: 600; }
.detail-banner { background: rgba(255,255,255,.92); border: 1px solid #e2e8f0; border-radius: 18px; padding: 14px 20px; margin: 14px 0 12px 0; box-shadow: 0 6px 18px rgba(15,23,42,.04); display: flex; justify-content: space-between; align-items: center; }
.detail-banner-done { background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 1.5px solid #86efac; }
.hour-lbl { font-size: .82rem; font-weight: 800; color: #64748b; padding-top: 8px; text-align: right; font-variant-numeric: tabular-nums; }
.slot-box { border-radius: 11px; padding: 8px 12px; font-size: .84rem; font-weight: 700; min-height: 38px; display: flex; align-items: center; margin-bottom: 4px; }
.slot-empty { background: #fff; border: 1.5px dashed #cbd5e1; color: #94a3b8; font-weight: 500; }
.slot-fixed { background: #f1f5f9; border-left: 4px solid #94a3b8; color: #475569; }
.st-card-hdr { display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; }
.st-card-title { font-size: 1.02rem; font-weight: 900; letter-spacing: .02em; color: #0f172a; }
.st-card-total { font-size: .9rem; font-weight: 700; color: #475569; }
.st-subj-lbl { font-size: .84rem; font-weight: 700; color: #334155; margin-bottom: 4px; }
.cal-card { border-radius: 14px; padding: 9px 10px; min-height: 76px; margin-bottom: 6px; box-shadow: 0 3px 10px rgba(15,23,42,.03); }
.cal-date { font-weight: 800; font-size: .86rem; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
.cal-preview { font-size: .72rem; color: #64748b; line-height: 1.32; word-break: break-all; }
.stTextArea textarea, .stTextInput input { font-size: .94rem !important; line-height: 1.6 !important; border-radius: 14px !important; border: 1.5px solid #e2e8f0 !important; background-color: #fff !important; }
.stTextArea textarea:focus, .stTextInput input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.16) !important; }
.stButton > button { border-radius: 10px !important; font-weight: 700 !important; font-size: .78rem !important; border: 1px solid #e2e8f0 !important; background: #fff !important; color: #334155 !important; padding: .32rem .45rem !important; }
.stButton > button:hover:not(:disabled) { border-color: #6366f1 !important; color: #4f46e5 !important; background: #f5f7ff !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important; color: #fff !important; border: none !important; box-shadow: 0 4px 12px rgba(79,70,229,.28) !important; }
.stButton > button:disabled { background: #eef2ff !important; color: #4f46e5 !important; border: 1px solid #c7d2fe !important; opacity: 1 !important; }
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 8px 22px rgba(15,23,42,.08); border: 1px solid #e2e8f0; }
[data-testid="stFileUploadDropzone"] { border-radius: 14px !important; padding: 12px !important; }
</style>
""", unsafe_allow_html=True)

# 1. 개인별 로그인 게이트
if "current_user" not in st.session_state:
    st.markdown("""
        <div class="hero-wrap" style="margin-top:40px;">
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

# 2. 로그인한 사용자 데이터 로드
if st.session_state.get("db_loaded") != USER:
    res_logs = supabase.table("daily_logs").select("*").like("day_key", f"{USER_PREFIX}%").execute()
    for row in res_logs.data:
        dk = row["day_key"][len(USER_PREFIX):]
        st.session_state[f"memo_{dk}"] = row.get("memo", "")
        st.session_state[f"chk_{dk}"] = bool(row.get("is_done", False))
        st.session_state[f"photo_url_{dk}"] = row.get("photo_url", "")
    if not st.session_state.get("memo_fixed_range"):
        st.session_state["memo_fixed_range"] = "07:00-24:00"
    if not st.session_state.get("memo_study_subjects"):
        st.session_state["memo_study_subjects"] = "공부, 운동, 독서, 스마트폰"
    if not st.session_state.get("memo_habit_list"):
        st.session_state["memo_habit_list"] = "12시 전 취침, 아침 식사, 물 마시기, 운동 30분, 밤에 폰 안 보기"
    st.session_state.setdefault("memo_exam_schedule", "")
    st.session_state.setdefault("memo_total_exam_tasks", "")
    st.session_state["db_loaded"] = USER

if "selected_day" not in st.session_state:
    today = date.today()
    st.session_state["selected_day"] = today if START_DATE <= today <= END_DATE else START_DATE

def save_day(day_key):
    supabase.table("daily_logs").upsert({
        "day_key": f"{USER_PREFIX}{day_key}",
        "memo": st.session_state.get(f"memo_{day_key}", ""),
        "is_done": bool(st.session_state.get(f"chk_{day_key}", False)),
        "photo_url": st.session_state.get(f"photo_url_{day_key}", "")
    }).execute()

def get_study_subjects():
    raw = st.session_state.get("memo_study_subjects", "공부, 운동, 독서, 스마트폰")
    subjs = [s.strip() for s in raw.split(",") if s.strip()]
    return subjs if subjs else ["공부", "운동", "독서", "스마트폰"]

def get_habit_list():
    raw = st.session_state.get("memo_habit_list", "12시 전 취침, 아침 식사, 물 마시기, 운동 30분, 밤에 폰 안 보기")
    return [h.strip() for h in raw.split(",") if h.strip()]

def save_study_time(sel_key):
    subjs = get_study_subjects()
    data = {s: [int(st.session_state.get(f"st_{sel_key}_{s}_h", 0)), int(st.session_state.get(f"st_{sel_key}_{s}_m", 0))] for s in subjs}
    st_key = f"study_time_{sel_key}"
    st.session_state[f"memo_{st_key}"] = json.dumps(data, ensure_ascii=False)
    save_day(st_key)

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

def select_day(target_date):
    st.session_state["selected_day"] = target_date

TIME_PAT = r"(\d{1,2})\s*(?::\s*(\d{2})|시(?:\s*(\d{1,2})\s*분?)?)"

def parse_time_groups(h_str, m1_str, m2_str) -> int:
    return int(h_str) * 60 + (int(m1_str) if m1_str else (int(m2_str) if m2_str else 0))

def parse_range(range_str: str, default=(420, 1440)):
    m = re.search(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}", (range_str or "").strip())
    if m:
        s, e = parse_time_groups(m.group(1), m.group(2), m.group(3)), parse_time_groups(m.group(4), m.group(5), m.group(6))
        if e > s:
            return s, e
    return default

def parse_fixed_schedule(text: str):
    events = []
    for line in (text or "").splitlines():
        m = re.match(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}\s*(.+)", line.strip())
        if m:
            s, e, t = parse_time_groups(m.group(1), m.group(2), m.group(3)), parse_time_groups(m.group(4), m.group(5), m.group(6)), m.group(7).strip()
            if e > s and t:
                events.append((s, e, t))
    return sorted(events, key=lambda x: x[0])

def get_free_hours(wd_idx: int, range_str: str):
    wake_min, sleep_min = parse_range(range_str)
    start_h, end_h = max(0, wake_min // 60), min(24, (sleep_min + 59) // 60)
    fixed_events = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{wd_idx}", ""))
    free_h = []
    for h in range(start_h, end_h):
        h_s, h_e = h * 60, (h + 1) * 60
        if not any(s < h_e and e > h_s for s, e, _ in fixed_events):
            free_h.append(h)
    return free_h

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
        dur_txt = ""
        for pat, fmt in [
            (r"(\d+)\s*시간\s*반(?:씩)?", lambda m: f"{m.group(1)}시간 반"),
            (r"(\d+)\s*시간\s*(\d+)\s*분(?:씩)?", lambda m: f"{m.group(1)}시간 {m.group(2)}분"),
            (r"(\d+)\s*시간(?:씩)?", lambda m: f"{m.group(1)}시간"),
            (r"(\d+)\s*분(?:씩)?", lambda m: f"{m.group(1)}분"),
        ]:
            mm = re.search(pat, line)
            if mm:
                dur_txt = fmt(mm)
                line = (line[:mm.start()] + line[mm.end():]).strip()
                break

        m_multi = re.search(r"(?:총\s*)?(\d+)\s*(지문|단원|과|강|챕터).*?각각\s*(\d+)\s*(?:번|회)씩?", line)
        if m_multi:
            n_items, unit, reps = int(m_multi.group(1)), m_multi.group(2), int(m_multi.group(3))
            title = (line[:m_multi.start()] + line[m_multi.end():]).strip(" ,/-:") or raw.strip()
            sessions = [f"{title} ({i}{unit} {r}/{reps}회)" for r in range(1, reps + 1) for i in range(1, n_items + 1)]
            tasks.append({"mode": "sessions", "sessions": sessions, "is_weekly_repeat": False})
            continue

        freq, is_weekly_repeat = None, False
        if re.search(r"매일|하루에\s*한\s*번", line):
            freq, is_weekly_repeat = 7, True
            line = re.sub(r"매일|하루에\s*한\s*번", "", line).strip()
        elif re.search(r"이틀에\s*한\s*번|격일", line):
            freq, is_weekly_repeat = 4, True
            line = re.sub(r"이틀에\s*한\s*번|격일", "", line).strip()
        else:
            m_freq = re.search(r"(?:일주일에\s*|주에\s*|주\s*)?(\d+)\s*(일|번|회)(?:씩)?", line)
            if m_freq:
                freq = int(m_freq.group(1))
                is_weekly_repeat = bool(re.search(r"일주일에|주에|주\s*\d", m_freq.group(0)))
                line = (line[:m_freq.start()] + line[m_freq.end():]).strip()

        qty, unit = None, ""
        m_qty = re.search(r"(?:총\s*)?(\d+)\s*(단원|과|강|지문|챕터|회차|문제|페이지|쪽|개|장|p|P)", line)
        if m_qty:
            qty, unit, line = int(m_qty.group(1)), m_qty.group(2), (line[:m_qty.start()] + line[m_qty.end():]).strip()

        title = re.sub(r"\s+", " ", line).strip(" ,/-:") or raw.strip()
        if dur_txt and not qty:
            title = f"{title} ({dur_txt})"
        tasks.append({"mode": "smart", "title": title, "qty": qty, "unit": unit, "freq": freq, "is_weekly_repeat": is_weekly_repeat})
    return tasks

def auto_fill_day_grid(d: date, task_list, range_str: str):
    dk = d.strftime('%Y_%m_%d')
    free_hours = get_free_hours(d.weekday(), range_str)
    grid = {}
    for idx, t in enumerate(task_list):
        if idx < len(free_hours):
            grid[str(free_hours[idx])] = t
    st.session_state[f"memo_grid_{dk}"] = json.dumps(grid, ensure_ascii=False)
    save_day(f"grid_{dk}")

def distribute_days_and_grid(active_days, range_str: str, tasks):
    n_days = len(active_days)
    if not n_days or not tasks:
        return
    day_free = {d: len(get_free_hours(d.weekday(), range_str)) * 60 for d in active_days}
    day_tasks = {d: [] for d in active_days}
    SEQ_UNITS = {"단원", "과", "강", "지문", "챕터", "회차"}

    for task in tasks:
        if task["mode"] == "sessions":
            for label in task["sessions"]:
                best_d = max(active_days, key=lambda d: (day_free[d] - len(day_tasks[d]) * 60, -len(day_tasks[d])))
                day_tasks[best_d].append(label)
            continue

        title, qty, unit, freq = task["title"], task["qty"], task["unit"], task["freq"]
        k = min(freq, n_days) if freq else (min(qty, n_days) if (qty and unit in SEQ_UNITS) else (n_days if qty else min(2, n_days)))
        chosen = sorted(sorted(active_days, key=lambda d: (-(day_free[d] - len(day_tasks[d]) * 60), d))[:k])

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
            cnt = freq if freq else k
            sessions = [f"{title} ({i+1}/{cnt}회)" for i in range(cnt)]

        if len(sessions) <= len(chosen):
            for d, label in zip(chosen, sessions):
                day_tasks[d].append(label)
        else:
            for label in sessions:
                best_d = max(active_days, key=lambda d: (day_free[d] - len(day_tasks[d]) * 60))
                day_tasks[best_d].append(label)

    for d in active_days:
        dk = d.strftime('%Y_%m_%d')
        st.session_state[f"memo_{dk}"] = "\n".join(day_tasks[d])
        save_day(dk)
        auto_fill_day_grid(d, day_tasks[d], range_str)

# 시험 전까지 전체 할 일 → 1) 주차별 배분 → 2) 매일 배분 → 3) 1시간 타임테이블 자동 배치
def distribute_exam_total_plan(start_d: date, end_d: date, range_str: str, total_text: str):
    tasks = parse_tasks(total_text)
    if not tasks:
        return
    active_weeks = []
    for w_idx, wk in enumerate(WEEKS):
        days_in_wk = [d for d in wk if d is not None and start_d <= d <= end_d]
        if days_in_wk:
            active_weeks.append((w_idx, days_in_wk))
    n_wks = len(active_weeks)
    if not n_wks:
        return

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
                    week_task_objs[w_idx].append({"mode": "sessions", "sessions": sub})
                    week_summary_lines[w_idx].append(f"{sub[0]} 외 {len(sub)-1}건" if len(sub) > 1 else sub[0])
            continue

        title, qty, unit, freq, is_wk_rep = task["title"], task["qty"], task["unit"], task["freq"], task["is_weekly_repeat"]
        if is_wk_rep and not qty:
            for w_idx, _ in active_weeks:
                week_task_objs[w_idx].append(dict(task))
                week_summary_lines[w_idx].append(f"{title} 주 {freq}회")
        elif qty:
            chunks = split_into_chunks(qty, n_wks)
            cur = 1
            for (w_idx, _), c in zip(active_weeks, chunks):
                if c > 0:
                    t_copy = dict(task)
                    t_copy["qty"] = c
                    t_copy["start_num"] = cur
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
                    week_summary_lines[w_idx].append(f"{title} {c}회")

    for w_idx, days_in_wk in active_weeks:
        wk_key = f"week_tasks_{w_idx}"
        st.session_state[f"memo_{wk_key}"] = "\n".join(week_summary_lines[w_idx])
        save_day(wk_key)
        distribute_days_and_grid(days_in_wk, range_str, week_task_objs[w_idx])

def get_day_task_list(dk: str):
    return [line.strip() for line in st.session_state.get(f"memo_{dk}", "").splitlines() if line.strip()]

def render_week_task_chips(dk: str) -> str:
    tasks = get_day_task_list(dk)
    return "".join(
        f'<div class="sch-item" style="background:{TASK_COLORS[i % len(TASK_COLORS)][0]}; border-left:3px solid {TASK_COLORS[i % len(TASK_COLORS)][1]}; color:{TASK_COLORS[i % len(TASK_COLORS)][2]};">{html.escape(t)}</div>'
        for i, t in enumerate(tasks)
    )

def load_day_grid(dk: str) -> dict:
    raw = st.session_state.get(f"memo_grid_{dk}", "")
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def toggle_hour_slot(dk: str, hour: int, brush: str):
    grid = load_day_grid(dk)
    hk = str(hour)
    if brush == "__ERASE__" or grid.get(hk) == brush:
        grid.pop(hk, None)
    else:
        grid[hk] = brush
    st.session_state[f"memo_grid_{dk}"] = json.dumps(grid, ensure_ascii=False)
    save_day(f"grid_{dk}")

def move_hour_slot(dk: str, hour: int, direction: int, free_hours):
    if hour not in free_hours:
        return
    idx = free_hours.index(hour)
    target_idx = idx + direction
    if not (0 <= target_idx < len(free_hours)):
        return
    target_h = free_hours[target_idx]
    grid = load_day_grid(dk)
    h1, h2 = str(hour), str(target_h)
    v1, v2 = grid.get(h1), grid.get(h2)
    if v1 is None:
        return
    grid[h2] = v1
    if v2 is not None:
        grid[h1] = v2
    else:
        grid.pop(h1, None)
    st.session_state[f"memo_grid_{dk}"] = json.dumps(grid, ensure_ascii=False)
    save_day(f"grid_{dk}")

today = date.today()

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
    st.markdown('<div style="font-size:.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">🎧 집중 백색소음</div>', unsafe_allow_html=True)
    noise_html = """
    <div style='padding:14px 12px; border-radius:18px; background:#fff; box-shadow:0 8px 22px rgba(15,23,42,.06); border:1px solid #e2e8f0; font-family:Pretendard,sans-serif; text-align:center;'>
        <div id='ns' style='font-size:.72rem; font-weight:800; color:#64748b; margin-bottom:8px;'>OFF</div>
        <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:5px; margin-bottom:10px;'>
            <button onclick='playNoise("pink","🌧️ 빗소리 재생 중")' style='padding:7px 2px; cursor:pointer; background:#eef2ff; color:#4f46e5; border:none; border-radius:9px; font-weight:700; font-size:.73rem;'>🌧️ 빗소리</button>
            <button onclick='playNoise("brown","☕ 카페·바람 재생 중")' style='padding:7px 2px; cursor:pointer; background:#ecfdf5; color:#059669; border:none; border-radius:9px; font-weight:700; font-size:.73rem;'>☕ 바람</button>
            <button onclick='playNoise("white","📻 백색소음 재생 중")' style='padding:7px 2px; cursor:pointer; background:#f1f5f9; color:#334155; border:none; border-radius:9px; font-weight:700; font-size:.73rem;'>📻 백색</button>
        </div>
        <div style='display:flex; align-items:center; gap:8px;'>
            <span style='font-size:.75rem;'>🔊</span>
            <input type='range' id='vol' min='0' max='0.35' step='0.01' value='0.12' oninput='setVol(this.value)' style='flex:1; accent-color:#4f46e5;'>
            <button onclick='stopNoise()' style='padding:5px 10px; cursor:pointer; background:#fee2e2; color:#dc2626; border:none; border-radius:8px; font-weight:700; font-size:.72rem;'>정지</button>
        </div>
        <script>
            let ctx=null, src=null, gain=null;
            function stopNoise(){ if(src){try{src.stop();}catch(e){} src=null;} document.getElementById('ns').textContent='OFF'; }
            function setVol(v){ if(gain) gain.gain.value=parseFloat(v); }
            function playNoise(type, label){
                stopNoise();
                ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
                if(ctx.state==='suspended') ctx.resume();
                let len = ctx.sampleRate * 3, buf = ctx.createBuffer(1, len, ctx.sampleRate), out = buf.getChannelData(0);
                let b0=0,b1=0,b2=0,last=0;
                for(let i=0;i<len;i++){
                    let w = Math.random()*2-1;
                    if(type==='white'){ out[i]=w*0.5; }
                    else if(type==='pink'){ b0=0.997*b0+w*0.029; b1=0.985*b1+w*0.032; b2=0.950*b2+w*0.048; out[i]=(b0+b1+b2+w*0.05)*1.5; }
                    else { out[i]=(last+(0.02*w))/1.02; last=out[i]; out[i]*=3.2; }
                }
                src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
                gain = ctx.createGain(); gain.gain.value = parseFloat(document.getElementById('vol').value);
                src.connect(gain); gain.connect(ctx.destination); src.start();
                document.getElementById('ns').textContent = label;
            }
        </script>
    </div>
    """
    components.html(noise_html, height=125)

    st.write("")
    st.markdown('<div style="font-size:.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">⏱️ 집중 타이머</div>', unsafe_allow_html=True)
    timer_html = """
    <div style='text-align:center; padding:16px 12px; border-radius:18px; background:#fff; box-shadow:0 8px 22px rgba(15,23,42,.06); border:1px solid #e2e8f0; font-family:Pretendard,sans-serif;'>
        <div id='st' style='font-size:.72rem; font-weight:800; color:#64748b; letter-spacing:.06em;'>READY</div>
        <div id='tm' style='color:#1e293b; font-size:2.4rem; font-weight:900; font-variant-numeric:tabular-nums; margin:4px 0 10px 0;'>00:00</div>
        <div style='margin-bottom:12px;'>
            <input type='number' id='cm' value='50' min='1' style='width:58px; padding:5px; border-radius:9px; border:1.5px solid #e2e8f0; text-align:center; font-weight:800;'> <span style='font-size:.82rem; font-weight:700; color:#64748b;'>분</span>
        </div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;'>
            <button onclick='go(document.getElementById("cm").value,"FOCUS")' style='padding:8px; cursor:pointer; background:linear-gradient(135deg,#4f46e5,#2563eb); color:#fff; border:none; border-radius:10px; font-weight:700; font-size:.8rem;'>🔥 집중</button>
            <button onclick='go(10,"BREAK")' style='padding:8px; cursor:pointer; background:linear-gradient(135deg,#10b981,#059669); color:#fff; border:none; border-radius:10px; font-weight:700; font-size:.8rem;'>💧 10분 휴식</button>
        </div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:6px;'>
            <button onclick='pause()' style='padding:6px; cursor:pointer; background:#f1f5f9; color:#334155; border:none; border-radius:9px; font-weight:700; font-size:.76rem;'>⏸ 정지</button>
            <button onclick='reset()' style='padding:6px; cursor:pointer; background:#f1f5f9; color:#64748b; border:none; border-radius:9px; font-weight:700; font-size:.76rem;'>↺ 초기화</button>
        </div>
        <script>
            let t=null, rem=0;
            function draw(){ let m=Math.floor(rem/60), s=rem%60; document.getElementById('tm').textContent=(m<10?'0'+m:m)+':'+(s<10?'0'+s:s); }
            function go(min, mode){ clearInterval(t); rem=Math.max(1,parseInt(min)||50)*60; document.getElementById('st').textContent=mode; draw();
                t=setInterval(()=>{ if(--rem<0){ clearInterval(t); document.getElementById('tm').textContent='완료! 👏'; document.getElementById('st').textContent='DONE'; } else draw(); },1000); }
            function pause(){ clearInterval(t); document.getElementById('st').textContent='PAUSED'; }
            function reset(){ clearInterval(t); rem=0; document.getElementById('tm').textContent='00:00'; document.getElementById('st').textContent='READY'; }
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
    with st.expander("⚙️ 고정 시간표 설정 (학교 · 학원)", expanded=False):
        st.text_input("기상~취침 시간 (예: 7시-24시)", key="memo_fixed_range", on_change=save_day, args=("fixed_range",))
        target_opt = st.selectbox("설정할 요일", ["평일 전체 (월~금)"] + WEEKDAY_KR)
        if target_opt == "평일 전체 (월~금)":
            st.caption("평일 공통 고정 일정 (예: 8시-16시 학교)")
            bulk_txt = st.text_area("평일 공통 고정 일정", value=st.session_state.get("memo_fixed_0", ""), height=100, label_visibility="collapsed")
            if st.button("💾 평일(월~금)에 한꺼번에 저장", use_container_width=True):
                for wd_i in range(5):
                    st.session_state[f"memo_fixed_{wd_i}"] = bulk_txt
                    save_day(f"fixed_{wd_i}")
                st.success("월~금 고정 시간표가 모두 저장됐어요!")
        else:
            fk = f"fixed_{WEEKDAY_KR.index(target_opt)}"
            st.session_state.setdefault(f"memo_{fk}", "")
            st.caption(f"{target_opt}요일 고정 일정 (학교 + 학원 시간)")
            st.text_area(f"{target_opt}요일 고정 일정", key=f"memo_{fk}", height=100, label_visibility="collapsed", on_change=save_day, args=(fk,))

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
            st.caption("시험 전까지 할 일을 한 줄씩 입력 (예: 국사 15단원 / 수학 300문제 / 매일 영단어 30분 / 주 3회 운동)")
            st.text_area("전체 할 일", key="memo_total_exam_tasks", height=110, label_visibility="collapsed", on_change=save_day, args=("total_exam_tasks",))
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
            st.text_area("이번 주 할 일", key=f"memo_{wk_task_key}", height=110, label_visibility="collapsed", on_change=save_day, args=(wk_task_key,))
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
            st.button("선택됨" if day == sel_day else "시간표 짜기", key=f"wk_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
        else:
            st.write("")

sel_key = sel_day.strftime('%Y_%m_%d')
sel_wd = WEEKDAY_KR[sel_day.weekday()]
memo_key, chk_key = f"memo_{sel_key}", f"chk_{sel_key}"
st.session_state.setdefault(memo_key, "")
st.session_state.setdefault(chk_key, False)
is_sel_done = st.session_state[chk_key]

st.markdown(f"""
    <div class="detail-banner {'detail-banner-done' if is_sel_done else ''}">
        <span style="font-size:1.05rem; font-weight:800; color:#1e293b;">📌 {sel_day.month}월 {sel_day.day}일 ({sel_wd}) 1시간 타임테이블 & 생활습관</span>
        <span style="font-size:.85rem; font-weight:800; color:#15803d;">{'🎉 오늘 목표 완료!' if is_sel_done else ''}</span>
    </div>
""", unsafe_allow_html=True)

d_left, d_right = st.columns([3, 2], gap="large")

with d_left:
    day_tasks = get_day_task_list(sel_key)
    color_map = {t: TASK_COLORS[idx % len(TASK_COLORS)] for idx, t in enumerate(day_tasks)}

    brush_options = day_tasks + list(LIFE_BLOCKS.keys()) + ["__ERASE__"]
    def fmt_brush(opt):
        if opt == "__ERASE__":
            return "🧹 지우기"
        if opt in LIFE_BLOCKS:
            return opt
        return f"{color_map[opt][3]} {opt}"

    selected_brush = st.radio(
        "칠할 항목을 고른 뒤 빈 칸을 누르거나, 배치된 항목의 ▲/▼로 시간을 바로 옮기세요",
        brush_options,
        format_func=fmt_brush,
        horizontal=True,
        key=f"brush_{sel_key}"
    )

    range_str = st.session_state.get("memo_fixed_range", "07:00-24:00")
    wake_min, sleep_min = parse_range(range_str)
    start_h, end_h = max(0, wake_min // 60), min(24, (sleep_min + 59) // 60)
    fixed_events = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{sel_day.weekday()}", ""))
    free_hours = get_free_hours(sel_day.weekday(), range_str)
    day_grid = load_day_grid(sel_key)

    for h in range(start_h, end_h):
        h_s, h_e = h * 60, (h + 1) * 60
        fixed_hit = next((title for s, e, title in fixed_events if s < h_e and e > h_s), None)
        assigned = day_grid.get(str(h))

        c_time, c_box, c_up, c_dn, c_act = st.columns([1.05, 3.85, 0.55, 0.55, 0.85], gap="small")
        with c_time:
            st.markdown(f'<div class="hour-lbl">{h:02d}:00</div>', unsafe_allow_html=True)
        with c_box:
            if fixed_hit:
                st.markdown(f'<div class="slot-box slot-fixed">{html.escape(fixed_hit)}</div>', unsafe_allow_html=True)
            elif assigned in LIFE_BLOCKS:
                bg, bd, fg = LIFE_BLOCKS[assigned]
                st.markdown(f'<div class="slot-box" style="background:{bg}; border-left:4px solid {bd}; color:{fg};">{html.escape(assigned)}</div>', unsafe_allow_html=True)
            elif assigned:
                bg, bd, fg, dot = color_map.get(assigned, ("#f8fafc", "#64748b", "#1e293b", "📌"))
                st.markdown(f'<div class="slot-box" style="background:{bg}; border-left:4px solid {bd}; color:{fg};">{dot} {html.escape(assigned)}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="slot-box slot-empty"></div>', unsafe_allow_html=True)
        with c_up:
            if not fixed_hit and assigned:
                st.button("▲", key=f"up_{sel_key}_{h}", use_container_width=True, disabled=(h == free_hours[0] if free_hours else True), on_click=move_hour_slot, args=(sel_key, h, -1, free_hours))
        with c_dn:
            if not fixed_hit and assigned:
                st.button("▼", key=f"dn_{sel_key}_{h}", use_container_width=True, disabled=(h == free_hours[-1] if free_hours else True), on_click=move_hour_slot, args=(sel_key, h, 1, free_hours))
        with c_act:
            if fixed_hit:
                st.button("고정", key=f"slot_{sel_key}_{h}", use_container_width=True, disabled=True)
            else:
                btn_txt = "✕" if (assigned and (selected_brush == "__ERASE__" or assigned == selected_brush)) else "선택"
                st.button(btn_txt, key=f"slot_{sel_key}_{h}", use_container_width=True, on_click=toggle_hour_slot, args=(sel_key, h, selected_brush))

    st.write("")
    with st.expander("✏️ 오늘 할 일 목록 직접 수정하기 (한 줄에 하나씩)", expanded=False):
        st.text_area("오늘 할 일 목록", key=memo_key, height=120, label_visibility="collapsed", on_change=save_day, args=(sel_key,))
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

    study_subjs = get_study_subjects()
    raw_st = st.session_state.get(f"memo_study_time_{sel_key}", "")
    try:
        saved_st = json.loads(raw_st) if raw_st else {}
    except Exception:
        saved_st = {}
    total_mins = 0
    for s in study_subjs:
        h_k, m_k = f"st_{sel_key}_{s}_h", f"st_{sel_key}_{s}_m"
        st.session_state.setdefault(h_k, int(saved_st.get(s, [0, 0])[0]))
        st.session_state.setdefault(m_k, int(saved_st.get(s, [0, 0])[1]))
        total_mins += int(st.session_state[h_k]) * 60 + int(st.session_state[m_k])
    tot_h, tot_m = total_mins // 60, total_mins % 60

    with st.container(border=True):
        st.markdown(f"""
            <div class="st-card-hdr">
                <span class="st-card-title">DAILY TIME</span>
                <span class="st-card-total">TOTAL : <b style="color:#4f46e5;">{tot_h}</b> h <b style="color:#4f46e5;">{tot_m:02d}</b> m</span>
            </div>
        """, unsafe_allow_html=True)
        for i in range(0, len(study_subjs), 2):
            row_subjs = study_subjs[i:i+2]
            r_cols = st.columns(2, gap="medium")
            for idx, subj in enumerate(row_subjs):
                with r_cols[idx]:
                    st.markdown(f'<div class="st-subj-lbl">{html.escape(subj)}</div>', unsafe_allow_html=True)
                    hc, mc = st.columns(2, gap="small")
                    with hc:
                        st.number_input("h", min_value=0, max_value=24, step=1, key=f"st_{sel_key}_{subj}_h", on_change=save_study_time, args=(sel_key,))
                    with mc:
                        st.number_input("m", min_value=0, max_value=59, step=5, key=f"st_{sel_key}_{subj}_m", on_change=save_study_time, args=(sel_key,))

    with st.expander("✏️ DAILY TIME 항목 이름 설정", expanded=False):
        st.caption("쉼표(,)로 구분해서 입력 (예: 공부, 운동, 독서, 스마트폰)")
        st.text_input("항목 목록", key="memo_study_subjects", label_visibility="collapsed", on_change=save_day, args=("study_subjects",))

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

st.markdown('<div class="sec-header" style="margin-top:26px;"><span class="sec-dot"></span>한눈에 보는 전체 달력</div>', unsafe_allow_html=True)
header_cols = st.columns(7)
for i, day_name in enumerate(WEEKDAY_KR):
    color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#64748b"
    header_cols[i].markdown(f"<div style='text-align:center; font-weight:800; font-size:.85rem; color:{color}; padding-bottom:6px;'>{day_name}</div>", unsafe_allow_html=True)

for week in WEEKS:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None:
                dk = day.strftime('%Y_%m_%d')
                memo_txt = st.session_state.get(f"memo_{dk}", "").strip()
                is_done = st.session_state.get(f"chk_{dk}", False)
                has_photo = bool(st.session_state.get(f"photo_url_{dk}", ""))
                if day == sel_day:
                    bg, border = "#eef2ff", "2px solid #4f46e5"
                elif is_done:
                    bg, border = "#ecfdf5", "1.5px solid #6ee7b7"
                elif day == today:
                    bg, border = "#fffbeb", "2px solid #f59e0b"
                else:
                    bg, border = "rgba(255,255,255,.9)", "1px solid #e2e8f0"
                day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
                icons = ("✅" if is_done else "") + (" 📸" if has_photo else "")
                preview = (memo_txt.replace("\n", " ")[:22] + "…") if len(memo_txt) > 22 else memo_txt.replace("\n", " ")
                st.markdown(f"""
                    <div class="cal-card" style="background:{bg}; border:{border};">
                        <div class="cal-date" style="color:{day_color};"><span>{day.month}/{day.day}{' 🔥' if day == today else ''}</span><span style="font-size:.78rem;">{icons}</span></div>
                        <div class="cal-preview">{html.escape(preview)}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.button("열기", key=f"cal_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
            else:
                st.write("")
# 끝
