import html
import re
import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from supabase import create_client, Client

st.set_page_config(page_title="프리미엄 스터디 플래너", page_icon="✨", layout="wide")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

START_DATE = date(2026, 11, 23)
END_DATE = date(2026, 12, 23)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
VALID_DATES = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

all_dates_padded = list(VALID_DATES)
while len(all_dates_padded) % 7 != 0:
    all_dates_padded.append(None)
WEEKS = [all_dates_padded[i:i+7] for i in range(0, len(all_dates_padded), 7)]

if "db_loaded" not in st.session_state:
    res_set = supabase.table("user_settings").select("*").eq("id", 1).execute()
    st.session_state["math_count"] = int(res_set.data[0].get("math_count", 0)) if res_set.data else 0
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

def save_settings():
    supabase.table("user_settings").upsert({"id": 1, "math_count": int(st.session_state.get("math_count", 0))}).execute()

def save_day(day_key):
    supabase.table("daily_logs").upsert({
        "day_key": day_key,
        "memo": st.session_state.get(f"memo_{day_key}", ""),
        "is_done": bool(st.session_state.get(f"chk_{day_key}", False)),
        "photo_url": st.session_state.get(f"photo_url_{day_key}", "")
    }).execute()

def select_day(target_date):
    st.session_state["selected_day"] = target_date

TIME_PAT = r"(\d{1,2})\s*(?::\s*(\d{2})|시(?:\s*(\d{1,2})\s*분?)?)"

def parse_time_groups(h_str, m1_str, m2_str) -> int:
    return int(h_str) * 60 + (int(m1_str) if m1_str else (int(m2_str) if m2_str else 0))

def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def parse_range(range_str: str):
    m = re.search(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}", range_str.strip())
    if m:
        s, e = parse_time_groups(m.group(1), m.group(2), m.group(3)), parse_time_groups(m.group(4), m.group(5), m.group(6))
        if e > s:
            return s, e
    return 420, 1440

def parse_fixed_schedule(text: str):
    events = []
    for line in text.splitlines():
        m = re.match(rf"{TIME_PAT}\s*[-~]\s*{TIME_PAT}\s*(.+)", line.strip())
        if m:
            s, e, t = parse_time_groups(m.group(1), m.group(2), m.group(3)), parse_time_groups(m.group(4), m.group(5), m.group(6)), m.group(7).strip()
            if e > s and t:
                events.append((s, e, t))
    return sorted(events, key=lambda x: x[0])

def get_free_slots(wake_min: int, sleep_min: int, fixed_events):
    slots, cur = [], wake_min
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
        m_hr, m_min = re.search(r"(\d+)\s*시간", line), re.search(r"(\d+)\s*분", line)
        if m_hr:
            total_min, line = int(m_hr.group(1)) * 60, re.sub(r"\d+\s*시간", "", line).strip()
        elif m_min:
            total_min, line = int(m_min.group(1)), re.sub(r"\d+\s*분", "", line).strip()
        m_qty = re.search(r"(\d+)\s*(문제|페이지|쪽|강|회|단원|개|p|P)", line)
        if m_qty:
            qty, unit = int(m_qty.group(1)), m_qty.group(2)
            base_title = (line[:m_qty.start()] + line[m_qty.end():]).strip(" ,/-:")
        else:
            qty, unit, base_title = None, "", line.strip(" ,/-:")
        if base_title:
            tasks.append({"title": base_title, "qty": qty, "unit": unit, "total_min": total_min})
    return tasks

def generate_weekly_schedule(week_dates, range_str: str, weekly_tasks_text: str, break_min: int = 10):
    wake_min, sleep_min = parse_range(range_str)
    active_days = [d for d in week_dates if d is not None]
    n_days = len(active_days)
    tasks = parse_weekly_tasks(weekly_tasks_text)
    if not n_days or not tasks:
        return [], []
    day_slots, day_scheduled, unscheduled = {}, {}, []
    for d in active_days:
        f_ev = parse_fixed_schedule(st.session_state.get(f"memo_fixed_{d.weekday()}", ""))
        day_slots[d] = get_free_slots(wake_min, sleep_min, f_ev)
        day_scheduled[d] = [(s, e, f"📌 {t}") for s, e, t in f_ev]
    for task in tasks:
        per_day_min = max(20, (task["total_min"] // n_days // 5) * 5) if task["total_min"] else 50
        if task["qty"]:
            base_q, rem_q = task["qty"] // n_days, task["qty"] % n_days
            daily_labels = [(active_days[i], f"{task['title']} {base_q + (1 if i < rem_q else 0)}{task['unit']}") for i in range(n_days) if base_q + (1 if i < rem_q else 0) > 0]
        else:
            daily_labels = [(d, task["title"]) for d in active_days]
        for d, label in daily_labels:
            placed = False
            for slot in day_slots[d]:
                if slot[1] - slot[0] >= per_day_min:
                    s_t, e_t = slot[0], slot[0] + per_day_min
                    day_scheduled[d].append((s_t, e_t, f"📖 {label}"))
                    slot[0] = e_t + break_min
                    placed = True
                    break
            if not placed:
                unscheduled.append(f"{d.month}/{d.day} {label} ({per_day_min}분)")
    for d in active_days:
        dk = d.strftime('%Y_%m_%d')
        day_scheduled[d].sort(key=lambda x: x[0])
        st.session_state[f"memo_{dk}"] = "\n".join([f"[{to_hhmm(s)} ~ {to_hhmm(e)}] {t}" for s, e, t in day_scheduled[d]])
        save_day(dk)
    return active_days, unscheduled

def render_schedule_blocks(memo_txt: str) -> str:
    blocks = []
    for raw_line in memo_txt.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        safe = html.escape(line)
        cls = "sch-fixed" if "📌" in line else ("sch-study" if "📖" in line else "sch-plain")
        blocks.append(f'<div class="sch-item {cls}">{safe}</div>')
    return "".join(blocks)

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
[data-testid="stSidebar"] { background: rgba(255,255,255,.84); backdrop-filter: blur(14px); border-right: 1px solid rgba(226,232,240,.85); }
.side-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 18px; padding: 16px; box-shadow: 0 6px 18px rgba(15,23,42,.04); margin-bottom: 12px; }
.side-title { font-size: .95rem; font-weight: 800; color: #1e293b; margin-bottom: 6px; display: flex; justify-content
