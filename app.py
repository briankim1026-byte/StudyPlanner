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
.side-title { font-size: .95rem; font-weight: 800; color: #1e293b; margin-bottom: 6px; display: flex; justify-content: space-between; }
.mini-bar-bg { width: 100%; height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; margin-top: 10px; }
.mini-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #6366f1, #0ea5e9); transition: width .4s ease; }
.hero-wrap { text-align: center; margin-bottom: 20px; }
.hero-pill { display: inline-block; padding: 5px 14px; border-radius: 999px; background: rgba(99,102,241,.1); color: #4f46e5; font-size: .78rem; font-weight: 700; letter-spacing: .04em; margin-bottom: 8px; }
.hero-title { font-size: 2.3rem; font-weight: 900; letter-spacing: -.03em; background: linear-gradient(120deg, #1e1b4b 0%, #4f46e5 55%, #0284c7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
.stat-card { background: rgba(255,255,255,.9); backdrop-filter: blur(12px); border-radius: 20px; padding: 18px 22px; box-shadow: 0 10px 28px rgba(15,23,42,.045); border: 1px solid rgba(255,255,255,.9); min-height: 102px; }
.stat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.stat-label { font-size: .84rem; color: #64748b; font-weight: 700; }
.stat-badge { font-size: .75rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
.stat-value { font-size: 1.65rem; font-weight: 900; letter-spacing: -.02em; }
.sec-header { display: flex; align-items: center; gap: 8px; font-size: 1.12rem; font-weight: 800; color: #1e293b; margin: 18px 0 10px 0; }
.sec-dot { width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #0ea5e9); display: inline-block; }
[data-testid="stExpander"] { background: rgba(255,255,255,.9) !important; border: 1px solid #e2e8f0 !important; border-radius: 16px !important; box-shadow: 0 4px 14px rgba(15,23,42,.035) !important; }
.week-card { border-radius: 18px; padding: 13px 11px; min-height: 215px; margin-bottom: 8px; box-shadow: 0 6px 18px rgba(15,23,42,.04); transition: transform .18s ease, box-shadow .18s ease; }
.week-card:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(15,23,42,.07); }
.week-date { font-weight: 800; font-size: .92rem; margin-bottom: 10px; padding-bottom: 7px; border-bottom: 1px solid rgba(148,163,184,.18); display: flex; justify-content: space-between; align-items: center; }
.today-chip { font-size: .65rem; font-weight: 800; background: #f59e0b; color: #fff; padding: 2px 6px; border-radius: 999px; margin-left: 4px; }
.sch-item { font-size: .74rem; line-height: 1.38; padding: 5px 7px; border-radius: 8px; margin-bottom: 5px; word-break: break-word; font-weight: 500; }
.sch-fixed { background: #f1f5f9; color: #475569; border-left: 3px solid #94a3b8; }
.sch-study { background: #eef2ff; color: #312e81; border-left: 3px solid #6366f1; }
.sch-plain { background: #f8fafc; color: #334155; border-left: 3px solid #cbd5e1; }
.detail-banner { background: rgba(255,255,255,.92); border: 1px solid #e2e8f0; border-radius: 18px; padding: 14px 20px; margin: 14px 0 12px 0; box-shadow: 0 6px 18px rgba(15,23,42,.04); display: flex; justify-content: space-between; align-items: center; }
.detail-banner-done { background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 1.5px solid #86efac; }
.cal-card { border-radius: 14px; padding: 9px 10px; min-height: 76px; margin-bottom: 6px; box-shadow: 0 3px 10px rgba(15,23,42,.03); transition: transform .15s ease; }
.cal-card:hover { transform: translateY(-1px); }
.cal-date { font-weight: 800; font-size: .86rem; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
.cal-preview { font-size: .72rem; color: #64748b; line-height: 1.32; word-break: break-all; }
.stTextArea textarea, .stTextInput input { font-size: .94rem !important; line-height: 1.6 !important; border-radius: 14px !important; border: 1.5px solid #e2e8f0 !important; background-color: #fff !important; }
.stTextArea textarea:focus, .stTextInput input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.16) !important; }
.stButton > button { border-radius: 11px !important; font-weight: 700 !important; font-size: .82rem !important; border: 1px solid #e2e8f0 !important; background: #fff !important; color: #334155 !important; padding: .35rem .75rem !important; transition: all .15s ease !important; }
.stButton > button:hover:not(:disabled) { border-color: #6366f1 !important; color: #4f46e5 !important; background: #f5f7ff !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important; color: #fff !important; border: none !important; box-shadow: 0 4px 12px rgba(79,70,229,.28) !important; }
.stButton > button:disabled { background: #eef2ff !important; color: #4f46e5 !important; border: 1px solid #c7d2fe !important; opacity: 1 !important; }
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 8px 22px rgba(15,23,42,.08); border: 1px solid #e2e8f0; }
[data-testid="stFileUploadDropzone"] { border-radius: 14px !important; padding: 12px !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    math_count = st.session_state.get("math_count", 0)
    math_pct = min(int((math_count / 30.0) * 100), 100)
    st.markdown(f"""
        <div class="side-card">
            <div class="side-title"><span>📐 일일 수학 달성도</span><span style="color:#4f46e5;">{math_pct}%</span></div>
            <div style="font-size:.78rem; color:#64748b;">목표 30문제 · 현재 <b>{math_count}</b>문제</div>
            <div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{math_pct}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    math_count = st.number_input("오늘 푼 문제 수", min_value=0, max_value=200, step=1, key="math_count", on_change=save_settings)
    if math_count >= 30:
        st.success("🔥 오늘 수학 목표 달성!")
    st.write("")
    st.markdown('<div style="font-size:.95rem; font-weight:800; color:#1e293b; margin-bottom:8px;">⏱️ 집중 타이머</div>', unsafe_allow_html=True)
    timer_html = """
    <div style='text-align:center; padding:16px 12px; border-radius:18px; background:#fff; box-shadow:0 8px 22px rgba(15,23,42,.06); border:1px solid #e2e8f0; font-family:Pretendard,sans-serif;'>
        <div id='st' style='font-size:.72rem; font-weight:800; color:#64748b; letter-spacing:.06em;'>READY</div>
        <div id='tm' style='color:#1e293b; font-size:2.5rem; font-weight:900; font-variant-numeric:tabular-nums; margin:4px 0 10px 0;'>00:00</div>
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
    components.html(timer_html, height=245)

st.markdown("""
    <div class="hero-wrap">
        <div class="hero-pill">2026.11.23 — 12.23 FINAL EXAM</div>
        <h1 class="hero-title">기말고사 스터디 플래너</h1>
    </div>
""", unsafe_allow_html=True)

today = date.today()
d_day_diff = (END_DATE - today).days
d_day_str = f"D-{d_day_diff}" if d_day_diff > 0 else ("D-DAY 🔥" if d_day_diff == 0 else f"D+{abs(d_day_diff)}")
done_days = sum(1 for d in VALID_DATES if st.session_state.get(f"chk_{d.strftime('%Y_%m_%d')}", False))
done_pct = int((done_days / TOTAL_DAYS) * 100)

m1, m2 = st.columns(2, gap="medium")
with m1:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-top"><span class="stat-label">🔥 기말고사 종료까지</span><span class="stat-badge" style="background:#eef2ff; color:#4f46e5;">12월 23일</span></div>
            <div class="stat-value" style="color:#4f46e5;">{d_day_str}</div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-top"><span class="stat-label">✅ 전체 달성률</span><span class="stat-badge" style="background:#ecfdf5; color:#059669;">{done_pct}% 완료</span></div>
            <div class="stat-value" style="color:#0f172a;">{done_days} <span style="font-size:1rem; color:#94a3b8; font-weight:700;">/ {TOTAL_DAYS}일</span></div>
            <div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{done_pct}%; background:linear-gradient(90deg,#10b981,#34d399);"></div></div>
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
    with st.expander("⚙️ 고정 시간표 설정 (평일 일괄 / 요일별)", expanded=False):
        st.text_input("기상~취침 시간 (예: 7시-24시)", key="memo_fixed_range", on_change=save_day, args=("fixed_range",))
        target_opt = st.selectbox("설정할 요일", ["평일 전체 (월~금)"] + WEEKDAY_KR)
        if target_opt == "평일 전체 (월~금)":
            st.caption("평일 공통 고정 일정 (예: 8시-16시 학교)")
            bulk_txt = st.text_area("평일 공통 고정 일정", value=st.session_state.get("memo_fixed_0", ""), height=115, label_visibility="collapsed")
            if st.button("💾 평일(월~금)에 한꺼번에 저장", use_container_width=True):
                for wd_i in range(5):
                    st.session_state[f"memo_fixed_{wd_i}"] = bulk_txt
                    save_day(f"fixed_{wd_i}")
                st.success("월~금 고정 시간표가 모두 저장됐어요!")
        else:
            fk = f"fixed_{WEEKDAY_KR.index(target_opt)}"
            st.session_state.setdefault(f"memo_{fk}", "")
            st.caption(f"{target_opt}요일 고정 일정 (예: 8시-16시 학교)")
            st.text_area(f"{target_opt}요일 고정 일정", key=f"memo_{fk}", height=115, label_visibility="collapsed", on_change=save_day, args=(fk,))

with t2:
    with st.expander(f"⚡ {picked_week_idx+1}주차 할 일 입력 → 주간 시간표 자동 짜기", expanded=False):
        wk_task_key = f"week_tasks_{picked_week_idx}"
        st.session_state.setdefault(f"memo_{wk_task_key}", "")
        st.caption("이번 주 할 일과 분량을 한 줄씩 입력 (예: 수학 210문제 / 국어 교과서 70p)")
        st.text_area("이번 주 할 일", key=f"memo_{wk_task_key}", height=115, label_visibility="collapsed", on_change=save_day, args=(wk_task_key,))
        break_min = st.number_input("과목 사이 휴식 시간(분)", min_value=0, max_value=30, value=10, step=5)
        if st.button("⚡ 이번 주(월~일) 시간표 자동 배분하기", use_container_width=True, type="primary"):
            _, unscheduled = generate_weekly_schedule(active_week, st.session_state.get("memo_fixed_range", "07:00-24:00"), st.session_state.get(f"memo_{wk_task_key}", ""), int(break_min))
            st.session_state["schedule_warn"] = ("빈 시간이 부족해 일부 배치를 못 했어요: " + ", ".join(unscheduled[:5])) if unscheduled else ""
            st.rerun()

if st.session_state.get("schedule_warn"):
    st.warning(st.session_state["schedule_warn"])
    st.session_state["schedule_warn"] = ""

st.markdown(f'<div class="sec-header"><span class="sec-dot"></span>{week_labels[picked_week_idx]} 주간 시간표</div>', unsafe_allow_html=True)
w_cols = st.columns(7)
for i, day in enumerate(active_week):
    with w_cols[i]:
        if day is not None:
            dk = day.strftime('%Y_%m_%d')
            memo_txt = st.session_state.get(f"memo_{dk}", "").strip()
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
                    <div>{render_schedule_blocks(memo_txt)}</div>
                </div>
            """, unsafe_allow_html=True)
            st.button("선택됨" if day == sel_day else "상세/인증", key=f"wk_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
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
        <span style="font-size:1.05rem; font-weight:800; color:#1e293b;">📌 {sel_day.month}월 {sel_day.day}일 ({sel_wd}) 하루 분량 & 인증</span>
        <span style="font-size:.85rem; font-weight:800; color:#15803d;">{'🎉 오늘 목표 완료!' if is_sel_done else ''}</span>
    </div>
""", unsafe_allow_html=True)

d_left, d_right = st.columns([3, 2], gap="large")
with d_left:
    st.text_area("하루 분량", key=memo_key, height=195, label_visibility="collapsed", on_change=save_day, args=(sel_key,))
    st.checkbox("✅ 오늘 하루 목표 완료!", key=chk_key, on_change=save_day, args=(sel_key,))

with d_right:
    saved_url = st.session_state.get(f"photo_url_{sel_key}", "")
    if saved_url:
        st.image(saved_url, use_container_width=True)
    with st.expander("📤 공부 인증 사진 올리기 / 변경하기", expanded=False):
        uploaded_file = st.file_uploader("인증 사진 선택", type=["jpg", "jpeg", "png"], key=f"photo_{sel_key}", label_visibility="collapsed")
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get(f"last_uploaded_{sel_key}") != file_id:
                ext = uploaded_file.name.split(".")[-1].lower()
                file_path = f"{sel_key}_{int(time.time())}.{ext}"
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
