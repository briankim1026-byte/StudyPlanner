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

# 5. 유연한 시간 파서 ("7시", "8시 30분", "08:30", "24시" 모두 인식)
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
    return 420, 1440  # 기본 07:00 ~ 24:00

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
        # 총 시간 추출 (예: 5시간, 300분)
        total_min = None
        m_hr = re.search(r"(\d+)\s*시간", line)
        m_min = re.search(r"(\d+)\s*분", line)
        if m_hr:
            total_min = int(m_hr.group(1)) * 60
            line = re.sub(r"\d+\s*시간", "", line).strip()
        elif m_min:
            total_min = int(m_min.group(1))
            line = re.sub(r"\d+\s*분", "", line).strip()

        # 분량(숫자+단위) 추출 (예: 210문제, 70p, 14강, 7회)
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

    # 요일별 고정 일정 & 빈 시간 준비
    day_fixed = {}
    day_slots = {}
    day_scheduled = {}
    for d in active_days:
        wd_idx = d.weekday()
        f_txt = st.session_state.get(f"memo_fixed_{wd_idx}", "")
        f_ev = parse_fixed_schedule(f_txt)
        day_fixed[d] = f_ev
        day_slots[d] = get_free_slots(wake_min, sleep_min, f_ev)
        day_scheduled[d] = [(s, e, f"📌 {t}") for s, e, t in f_ev]

    unscheduled = []

    # 각 주간 할 일을 이번 주 날짜들에 균등 분배
    for task in tasks:
        title = task["title"]
        qty = task["qty"]
        unit = task["unit"]
        total_min = task["total_min"]

        # 하루당 소요 시간 결정 (미입력 시 기본 하루 50분)
        if total_min:
            per_day_min = max(20, (total_min // n_days // 5) * 5)
        else:
            per_day_min = 50

        # 분량이 있으면 날짜 수로 나누어 배분
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

        # 각 날짜의 빈 시간에 배치
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

    # 결과 저장
    for d in active_days:
        dk = d.strftime('%Y_%m_%d')
        day_scheduled[d].sort(key=lambda x: x[0])
        lines = [f"[{to_hhmm(s)} ~ {to_hhmm(e)}] {t}" for s, e, t in day_scheduled[d]]
        st.session_state[f"memo_{dk}"] = "\n".join(lines)
        save_day(dk)

    return active_days, unscheduled

# 6. Pretendard 폰트 + 카드 CSS
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .stApp { background: linear-gradient(160deg, #f7f9fc 0%, #edf2fb 100%); }
    .main-title {
        font-size: 2.2rem; font-weight: 900;
        background: linear-gradient(45deg, #4f46e5, #0ea5e9);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 4px;
    }
    .sub-title { font-size: 1rem; color: #64748b; font-weight: 600; text-align: center; margin-bottom: 18px; }
    .stat-card {
        background: #ffffff; border-radius: 16px; padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); border: 1px solid #e2e8f0; text-align: center;
    }
    .stat-label { font-size: 0.85rem; color: #64748b; font-weight: 600; margin-bottom: 4px; }
    .stat-value { font-size: 1.4rem; font-weight: 800; color: #1e293b; }
    .week-card {
        border-radius: 14px; padding: 12px; min-height: 185px; margin-bottom: 8px;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }
    .week-date { font-weight: 800; font-size: 0.95rem; margin-bottom: 8px; display: flex; justify-content: space-between; }
    .week-body { font-size: 0.78rem; color: #334155; line-height: 1.48; white-space: pre-wrap; word-break: break-word; }
    .cal-card {
        border-radius: 12px; padding: 8px 10px; min-height: 76px; margin-bottom: 6px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .cal-date { font-weight: 800; font-size: 0.9rem; margin-bottom: 3px; display: flex; justify-content: space-between; }
    .cal-preview { font-size: 0.74rem; color: #475569; line-height: 1.3; word-break: break-all; }
    .stTextArea textarea {
        font-size: 0.95rem; line-height: 1.55; border-radius: 12px;
        border: 1.5px solid #cbd5e1; background-color: #ffffff;
    }
    .stTextArea textarea:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }
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
st.markdown('<p class="sub-title">11/23 ~ 12/23 주간 자동 배분 프로젝트</p>', unsafe_allow_html=True)

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

# 현재 선택된 날짜가 속한 주차 찾기
sel_day = st.session_state["selected_day"]
current_week_idx = 0
for idx, wk in enumerate(WEEKS):
    if sel_day in wk:
        current_week_idx = idx
        break

week_labels = []
for idx, wk in enumerate(WEEKS):
    valid_w = [d for d in wk if d is not None]
    week_labels.append(f"{idx+1}주차 ({valid_w[0].month}/{valid_w[0].day} ~ {valid_w[-1].month}/{valid_w[-1].day})")

picked_week_label = st.selectbox("📅 주차 선택", week_labels, index=current_week_idx)
picked_week_idx = week_labels.index(picked_week_label)
if picked_week_idx != current_week_idx:
    first_valid = [d for d in WEEKS[picked_week_idx] if d is not None][0]
    st.session_state["selected_day"] = first_valid
    st.rerun()

active_week = WEEKS[picked_week_idx]

# 9. 고정 시간표 설정 (평일 일괄 지원) & 주간 자동 배분
t1, t2 = st.columns(2)
with t1:
    with st.expander("⚙️ 고정 시간표 설정 (평일 일괄 / 요일별)", expanded=False):
        st.text_input("기상~취침 시간 (예: 7시-24시 또는 07:00-24:00)", key="memo_fixed_range", on_change=save_day, args=("fixed_range",))
        target_opt = st.selectbox("설정할 요일", ["평일 전체 (월~금)"] + WEEKDAY_KR)

        if target_opt == "평일 전체 (월~금)":
            default_weekday_txt = st.session_state.get("memo_fixed_0", "")
            st.caption("평일 공통 고정 일정 (예: 8시-16시 학교)")
            bulk_txt = st.text_area("평일 공통 고정 일정", value=default_weekday_txt, height=120, label_visibility="collapsed")
            if st.button("💾 평일(월~금)에 한꺼번에 저장", use_container_width=True):
                for wd_i in range(5):
                    fk = f"fixed_{wd_i}"
                    st.session_state[f"memo_{fk}"] = bulk_txt
                    save_day(fk)
                st.success("월~금 고정 시간표가 모두 저장됐어요!")
        else:
            edit_wd_idx = WEEKDAY_KR.index(target_opt)
            fk = f"fixed_{edit_wd_idx}"
            if f"memo_{fk}" not in st.session_state:
                st.session_state[f"memo_{fk}"] = ""
            st.caption(f"{target_opt}요일 고정 일정 (예: 8시-16시 학교)")
            st.text_area(
                f"{target_opt}요일 고정 일정",
                key=f"memo_{fk}",
                height=120,
                label_visibility="collapsed",
                on_change=save_day,
                args=(fk,)
            )

with t2:
    with st.expander(f"⚡ {picked_week_idx+1}주차 할 일 입력 → 주간 시간표 자동 짜기", expanded=False):
        wk_task_key = f"week_tasks_{picked_week_idx}"
        if f"memo_{wk_task_key}" not in st.session_state:
            st.session_state[f"memo_{wk_task_key}"] = ""
        st.caption("이번 주 할 일과 분량을 한 줄씩 입력 (예: 수학 210문제 / 국어 교과서 70p)")
        st.text_area(
            "이번 주 할 일",
            key=f"memo_{wk_task_key}",
            height=120,
            label_visibility="collapsed",
            on_change=save_day,
            args=(wk_task_key,)
        )
        break_min = st.number_input("과목 사이 휴식 시간(분)", min_value=0, max_value=30, value=10, step=5)
        if st.button("⚡ 이번 주(월~일) 시간표 자동 배분하기", use_container_width=True, type="primary"):
            range_txt = st.session_state.get("memo_fixed_range", "07:00-24:00")
            wk_txt = st.session_state.get(f"memo_{wk_task_key}", "")
            _, unscheduled = generate_weekly_schedule(active_week, range_txt, wk_txt, int(break_min))
            if unscheduled:
                st.session_state["schedule_warn"] = "빈 시간이 부족해 일부 배치를 못 했어요: " + ", ".join(unscheduled[:5])
            else:
                st.session_state["schedule_warn"] = ""
            st.rerun()

if st.session_state.get("schedule_warn"):
    st.warning(st.session_state["schedule_warn"])
    st.session_state["schedule_warn"] = ""

# 10. [위쪽] 주간 시간표 (월~일)
st.markdown(f"### 📋 {week_labels[picked_week_idx]} 주간 시간표")
w_cols = st.columns(7)
for i, day in enumerate(active_week):
    with w_cols[i]:
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
                bg, border = "#ffffff", "1px solid #e2e8f0"

            day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
            icons = ("✅" if is_done else "") + (" 📸" if has_photo else "")

            st.markdown(f"""
                <div class="week-card" style="background:{bg}; border:{border};">
                    <div class="week-date" style="color:{day_color};">
                        <span>{day.month}/{day.day} ({WEEKDAY_KR[i]})</span>
                        <span>{icons}</span>
                    </div>
                    <div class="week-body">{memo_txt}</div>
                </div>
            """, unsafe_allow_html=True)
            st.button("상세/인증", key=f"wk_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
        else:
            st.write("")

# 11. [중간] 선택한 날 상세 수정 · 완료 체크 · 사진 인증
sel_key = sel_day.strftime('%Y_%m_%d')
sel_wd = WEEKDAY_KR[sel_day.weekday()]
memo_key = f"memo_{sel_key}"
chk_key = f"chk_{sel_key}"
if memo_key not in st.session_state:
    st.session_state[memo_key] = ""
if chk_key not in st.session_state:
    st.session_state[chk_key] = False

st.write("")
d_left, d_right = st.columns([3, 2], gap="large")
with d_left:
    st.markdown(f"**📌 {sel_day.month}월 {sel_day.day}일 ({sel_wd}) 하루 분량 수정**")
    st.text_area(
        label="하루 분량",
        key=memo_key,
        height=190,
        label_visibility="collapsed",
        on_change=save_day,
        args=(sel_key,)
    )
    st.checkbox("✅ 오늘 하루 목표 완료!", key=chk_key, on_change=save_day, args=(sel_key,))

with d_right:
    st.markdown("**📸 오늘의 공부 인증 사진**")
    saved_url = st.session_state.get(f"photo_url_{sel_key}", "")
    if saved_url:
        st.image(saved_url, use_container_width=True)

    with st.expander("📤 사진 올리기 / 변경하기", expanded=False):
        uploaded_file = st.file_uploader(
            "인증 사진 선택",
            type=["jpg", "jpeg", "png"],
            key=f"photo_{sel_key}",
            label_visibility="collapsed"
        )
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get(f"last_uploaded_{sel_key}") != file_id:
                ext = uploaded_file.name.split(".")[-1].lower()
                file_path = f"{sel_key}_{int(time.time())}.{ext}"
                supabase.storage.from_("photos").upload(
                    file_path,
                    uploaded_file.getvalue(),
                    {"content-type": uploaded_file.type}
                )
                public_url = supabase.storage.from_("photos").get_public_url(file_path)
                st.session_state[f"photo_url_{sel_key}"] = public_url
                st.session_state[f"last_uploaded_{sel_key}"] = file_id
                save_day(sel_key)
                st.rerun()

st.divider()

# 12. [아래쪽] 한눈에 보는 전체 달력
st.markdown("### 🗓️ 한눈에 보는 전체 달력")
header_cols = st.columns(7)
for i, day_name in enumerate(WEEKDAY_KR):
    color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#475569"
    header_cols[i].markdown(f"<div style='text-align:center; font-weight:800; color:{color}; padding-bottom:6px;'>{day_name}</div>", unsafe_allow_html=True)

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
                    bg, border = "#ffffff", "1px solid #e2e8f0"

                day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
                icons = ("✅" if is_done else "") + (" 📸" if has_photo else "")
                preview = (memo_txt.replace("\n", " ")[:22] + "…") if len(memo_txt) > 22 else memo_txt.replace("\n", " ")

                st.markdown(f"""
                    <div class="cal-card" style="background:{bg}; border:{border};">
                        <div class="cal-date" style="color:{day_color};">
                            <span>{day.month}/{day.day}{' 🔥' if day == today else ''}</span>
                            <span style="font-size:0.8rem;">{icons}</span>
                        </div>
                        <div class="cal-preview">{preview}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.button("열기", key=f"cal_btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
            else:
                st.write("")
