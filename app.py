import re
import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from supabase import create_client, Client

# 1. 화면 기본 설정
st.set_page_config(page_title="프리미엄 스터디 플래너", layout="wide")

# 2. Supabase 연결
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# 날짜 범위 설정
START_DATE = date(2026, 11, 23)
END_DATE = date(2026, 12, 23)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
VALID_DATES = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

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

    if "memo_fixed_range" not in st.session_state or not st.session_state["memo_fixed_range"]:
        st.session_state["memo_fixed_range"] = "07:00-24:00"

    st.session_state["db_loaded"] = True

# 기본 선택 날짜
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

# 5. 자동 시간표 계산 유틸리티
def to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m

def to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def parse_fixed_schedule(text: str):
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})\s*(.+)", line)
        if match:
            s_min = to_min(match.group(1))
            e_min = to_min(match.group(2))
            title = match.group(3).strip()
            if e_min > s_min:
                events.append((s_min, e_min, title))
    events.sort(key=lambda x: x[0])
    return events

def parse_tasks(text: str):
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.search(r"(\d+)\s*분?$", line)
        if match:
            dur = int(match.group(1))
            title = line[:match.start()].strip(" ,/-:")
        else:
            dur = 60
            title = line
        if title and dur > 0:
            tasks.append((title, dur))
    return tasks

def build_auto_schedule(range_str: str, fixed_text: str, tasks_text: str, break_min: int = 10):
    m = re.match(r"(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})", range_str.strip())
    wake_min = to_min(m.group(1)) if m else 420
    sleep_min = to_min(m.group(2)) if m else 1440

    fixed_events = parse_fixed_schedule(fixed_text)
    tasks = parse_tasks(tasks_text)

    # 빈 시간 구간 계산
    free_slots = []
    cur = wake_min
    for s, e, _ in fixed_events:
        if s > cur:
            free_slots.append([cur, min(s, sleep_min)])
        cur = max(cur, e)
    if cur < sleep_min:
        free_slots.append([cur, sleep_min])

    scheduled = [(s, e, f"📌 {t}") for s, e, t in fixed_events]
    unscheduled = []

    for title, dur in tasks:
        placed = False
        # 통째로 들어갈 수 있는 빈 시간 찾기
        for slot in free_slots:
            if slot[1] - slot[0] >= dur:
                start_t = slot[0]
                end_t = start_t + dur
                scheduled.append((start_t, end_t, f"📖 {title}"))
                slot[0] = end_t + break_min
                placed = True
                break
        if not placed:
            unscheduled.append(f"{title} ({dur}분)")

    scheduled.sort(key=lambda x: x[0])
    lines = [f"[{to_hhmm(s)} ~ {to_hhmm(e)}] {t}" for s, e, t in scheduled]
    return "\n".join(lines), unscheduled

# 6. Pretendard 폰트 + 카드 CSS
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .stApp {
        background: linear-gradient(160deg, #f7f9fc 0%, #edf2fb 100%);
    }
    .main-title {
        font-size: 2.3rem;
        font-weight: 900;
        background: linear-gradient(45deg, #4f46e5, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size: 1rem;
        color: #64748b;
        font-weight: 600;
        text-align: center;
        margin-bottom: 20px;
    }
    .stat-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .stat-label { font-size: 0.85rem; color: #64748b; font-weight: 600; margin-bottom: 4px; }
    .stat-value { font-size: 1.45rem; font-weight: 800; color: #1e293b; }
    .daily-box {
        background: #ffffff;
        border-radius: 18px;
        padding: 20px 24px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
        border: 1.5px solid #e2e8f0;
        margin-bottom: 14px;
    }
    .daily-box-done {
        background: #f0fdf4;
        border: 1.5px solid #86efac;
    }
    .cal-card {
        border-radius: 12px;
        padding: 10px 10px 8px 10px;
        min-height: 92px;
        margin-bottom: 6px;
        transition: all 0.15s ease;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .cal-date { font-weight: 800; font-size: 0.95rem; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
    .cal-preview { font-size: 0.78rem; color: #475569; line-height: 1.35; word-break: break-all; }
    .stTextArea textarea {
        font-size: 0.98rem;
        line-height: 1.6;
        border-radius: 12px;
        border: 1.5px solid #cbd5e1;
        background-color: #ffffff;
    }
    .stTextArea textarea:focus {
        border-color: #4f46e5;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    }
    [data-testid="stFileUploadDropzone"] { padding: 12px; }
    </style>
""", unsafe_allow_html=True)

# 7. 사이드바
with st.sidebar:
    st.header("📐 일일 수학 달성도")
    st.caption("매일 30문제 이상 꾸준히 푸는 것이 최상위권의 핵심입니다.")
    math_count = st.number_input("오늘 푼 문제 수", min_value=0, max_value=200, step=1, key="math_count", on_change=save_settings)
    
    st.progress(min(math_count / 30.0, 1.0))
    if math_count >= 30:
        st.success("🔥 완벽합니다! 오늘 수학 목표치를 달성했어요.")
    elif math_count > 0:
        st.info("💡 좋은 페이스입니다. 끝까지 집중력을 유지하세요!")
        
    st.divider()

    st.header("⏱️ 맞춤형 집중 타이머")
    timer_html = """
    <div style='text-align:center; padding:12px; border-radius:14px; background:#ffffff; box-shadow: 0 4px 8px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; font-family: Pretendard, sans-serif;'>
        <h1 id='time' style='color:#4f46e5; font-size: 2.4rem; margin: 8px 0;'>00:00</h1>
        <div style='margin-bottom: 10px;'>
            <input type='number' id='customMin' value='50' min='1' style='width: 60px; padding: 5px; border-radius: 6px; border: 1px solid #cbd5e1; text-align: center; font-weight: bold;'> 분
        </div>
        <button onclick='startCustomTimer()' style='padding:8px 12px; margin:2px; cursor:pointer; background:linear-gradient(45deg, #4f46e5, #6366f1); color:white; border:none; border-radius:8px; font-weight:bold;'>🔥 집중 시작</button>
        <button onclick='startTimer(10)' style='padding:8px 12px; margin:2px; cursor:pointer; background:linear-gradient(45deg, #10b981, #34d399); color:white; border:none; border-radius:8px; font-weight:bold;'>💧 10분 휴식</button>
        <script>
            let timer;
            function startCustomTimer() {
                let min = document.getElementById('customMin').value;
                if(min > 0) startTimer(min);
            }
            function startTimer(minutes) {
                clearInterval(timer);
                let time = minutes * 60;
                let display = document.getElementById('time');
                timer = setInterval(function () {
                    let min = parseInt(time / 60, 10);
                    let sec = parseInt(time % 60, 10);
                    min = min < 10 ? '0' + min : min;
                    sec = sec < 10 ? '0' + sec : sec;
                    display.textContent = min + ':' + sec;
                    if (--time < 0) {
                        clearInterval(timer);
                        display.textContent = '종료! 👏';
                    }
                }, 1000);
            }
        </script>
    </div>
    """
    components.html(timer_html, height=200)

# 8. 상단 타이틀 & 대시보드
st.markdown('<p class="main-title">✨ 기말고사 스터디 플래너</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">11/23 ~ 12/23 실전 집중 프로젝트</p>', unsafe_allow_html=True)

today = date.today()
d_day_diff = (END_DATE - today).days
d_day_str = f"D-{d_day_diff}" if d_day_diff > 0 else ("D-DAY 🔥" if d_day_diff == 0 else f"D+{abs(d_day_diff)}")

done_days = sum(1 for d in VALID_DATES if st.session_state.get(f"chk_{d.strftime('%Y_%m_%d')}", False))
done_pct = int((done_days / TOTAL_DAYS) * 100)

m1, m2 = st.columns(2)
with m1:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">🔥 기말고사 종료까지 (12/23)</div>
            <div class="stat-value" style="color:#4f46e5;">{d_day_str}</div>
        </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">✅ 전체 달성률</div>
            <div class="stat-value" style="color:#10b981;">{done_days} / {TOTAL_DAYS}일 ({done_pct}%)</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")
st.progress(done_days / TOTAL_DAYS)
st.write("")

# 9. [위쪽] 일일 집중 시간표
sel_day = st.session_state["selected_day"]
sel_key = sel_day.strftime('%Y_%m_%d')
sel_wd_idx = sel_day.weekday()
sel_wd = WEEKDAY_KR[sel_wd_idx]

# 날짜 이동 바
nav1, nav2, nav3 = st.columns([1, 3, 1])
with nav1:
    if sel_day > START_DATE:
        st.button("◀ 이전 날", use_container_width=True, on_click=select_day, args=(sel_day - timedelta(days=1),))
with nav2:
    date_labels = [f"{d.month}월 {d.day}일 ({WEEKDAY_KR[d.weekday()]})" + (" · 오늘" if d == today else "") for d in VALID_DATES]
    current_idx = VALID_DATES.index(sel_day)
    picked_label = st.selectbox("날짜 선택", date_labels, index=current_idx, label_visibility="collapsed")
    picked_date = VALID_DATES[date_labels.index(picked_label)]
    if picked_date != sel_day:
        st.session_state["selected_day"] = picked_date
        st.rerun()
with nav3:
    if sel_day < END_DATE:
        st.button("다음 날 ▶", use_container_width=True, on_click=select_day, args=(sel_day + timedelta(days=1),))

# 요일별 고정 시간표 설정 & 자동 생성기
t1, t2 = st.columns(2)
with t1:
    with st.expander("⚙️ 요일별 고정 시간표 설정 (월~일)", expanded=False):
        st.text_input("기상~취침 시간 (예: 07:00-24:00)", key="memo_fixed_range", on_change=save_day, args=("fixed_range",))
        edit_wd = st.selectbox("설정할 요일", WEEKDAY_KR, index=sel_wd_idx)
        edit_wd_idx = WEEKDAY_KR.index(edit_wd)
        fixed_key = f"fixed_{edit_wd_idx}"
        if f"memo_{fixed_key}" not in st.session_state:
            st.session_state[f"memo_{fixed_key}"] = ""
        st.caption(f"{edit_wd}요일 고정 일정 (형식: 08:30-16:00 학교)")
        st.text_area(
            f"{edit_wd}요일 고정 일정",
            key=f"memo_{fixed_key}",
            height=130,
            label_visibility="collapsed",
            on_change=save_day,
            args=(fixed_key,)
        )

with t2:
    with st.expander(f"⚡ {sel_wd}요일 고정 일정 바탕 자동 시간표 짜기", expanded=False):
        st.caption("할 일과 소요 시간(분)을 한 줄씩 입력 (형식: 수학 30문제 90분)")
        tasks_input = st.text_area(
            "오늘 할 일 목록",
            key=f"tasks_input_{sel_key}",
            height=120,
            label_visibility="collapsed"
        )
        break_min = st.number_input("과목 사이 휴식 시간(분)", min_value=0, max_value=30, value=10, step=5)
        if st.button("⚡ 빈 시간에 자동 배치하기", use_container_width=True, type="primary"):
            wd_fixed_text = st.session_state.get(f"memo_fixed_{sel_wd_idx}", "")
            range_text = st.session_state.get("memo_fixed_range", "07:00-24:00")
            result_schedule, unscheduled = build_auto_schedule(range_text, wd_fixed_text, tasks_input, int(break_min))
            st.session_state[f"memo_{sel_key}"] = result_schedule
            save_day(sel_key)
            if unscheduled:
                st.session_state["schedule_warn"] = "시간이 부족해 배치하지 못한 할 일: " + ", ".join(unscheduled)
            else:
                st.session_state["schedule_warn"] = ""
            st.rerun()

if st.session_state.get("schedule_warn"):
    st.warning(st.session_state["schedule_warn"])
    st.session_state["schedule_warn"] = ""

# 선택된 날의 세션 키 초기화
memo_key = f"memo_{sel_key}"
chk_key = f"chk_{sel_key}"
if memo_key not in st.session_state:
    st.session_state[memo_key] = ""
if chk_key not in st.session_state:
    st.session_state[chk_key] = False

is_sel_done = st.session_state[chk_key]
box_class = "daily-box daily-box-done" if is_sel_done else "daily-box"
status
