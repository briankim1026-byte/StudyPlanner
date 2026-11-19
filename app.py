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

    st.session_state["db_loaded"] = True

# 기본 선택 날짜 (오늘이 기간 안이면 오늘, 아니면 11/23)
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

# 5. Pretendard 폰트 + 깔끔한 화이트/파스텔 카드 CSS
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

# 6. 사이드바 (수학 달성도 + 집중 타이머)
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

# 7. 상단 타이틀 & 동기부여 대시보드 (2칸)
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

# 8. [위쪽] 일일 집중 시간표 (Daily Focus View)
sel_day = st.session_state["selected_day"]
sel_key = sel_day.strftime('%Y_%m_%d')
sel_wd = WEEKDAY_KR[sel_day.weekday()]

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

# 선택된 날의 세션 키 초기화
memo_key = f"memo_{sel_key}"
chk_key = f"chk_{sel_key}"
if memo_key not in st.session_state:
    st.session_state[memo_key] = ""
if chk_key not in st.session_state:
    st.session_state[chk_key] = False

is_sel_done = st.session_state[chk_key]
box_class = "daily-box daily-box-done" if is_sel_done else "daily-box"
status_badge = "🎉 오늘 목표 완료!" if is_sel_done else ""

st.markdown(f"""
    <div class="{box_class}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.35rem; font-weight:800; color:#1e293b;">📌 {sel_day.month}월 {sel_day.day}일 ({sel_wd}) 일일 시간표</span>
            <span style="font-size:0.9rem; font-weight:700; color:#15803d;">{status_badge}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

d_left, d_right = st.columns([3, 2], gap="large")

with d_left:
    st.text_area(
        label="오늘 할 일 & 시간표",
        key=memo_key,
        height=230,
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

# 9. [아래쪽] 한눈에 보는 컴팩트 월별 달력
st.markdown("### 🗓️ 한눈에 보는 전체 달력")

all_dates = list(VALID_DATES)
while len(all_dates) % 7 != 0:
    all_dates.append(None)
weeks = [all_dates[i:i+7] for i in range(0, len(all_dates), 7)]

header_cols = st.columns(7)
for i, day_name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
    color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#475569"
    header_cols[i].markdown(f"<div style='text-align:center; font-weight:800; color:{color}; padding-bottom:6px;'>{day_name}</div>", unsafe_allow_html=True)

for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None:
                dk = day.strftime('%Y_%m_%d')
                memo_txt = st.session_state.get(f"memo_{dk}", "").strip()
                is_done = st.session_state.get(f"chk_{dk}", False)
                has_photo = bool(st.session_state.get(f"photo_url_{dk}", ""))

                if day == sel_day:
                    bg_color = "#eef2ff"
                    border_style = "2px solid #4f46e5"
                elif is_done:
                    bg_color = "#ecfdf5"
                    border_style = "1.5px solid #6ee7b7"
                elif day == today:
                    bg_color = "#fffbeb"
                    border_style = "2px solid #f59e0b"
                else:
                    bg_color = "#ffffff"
                    border_style = "1px solid #e2e8f0"

                day_color = "#ef4444" if i == 6 else "#2563eb" if i == 5 else "#1e293b"
                icons = ("✅" if is_done else "") + (" 📸" if has_photo else "")
                preview = (memo_txt.replace("\n", " ")[:24] + "…") if len(memo_txt) > 24 else memo_txt.replace("\n", " ")

                st.markdown(f"""
                    <div class="cal-card" style="background:{bg_color}; border:{border_style};">
                        <div class="cal-date" style="color:{day_color};">
                            <span>{day.month}/{day.day}{' 🔥' if day == today else ''}</span>
                            <span style="font-size:0.85rem;">{icons}</span>
                        </div>
                        <div class="cal-preview">{preview}</div>
                    </div>
                """, unsafe_allow_html=True)

                btn_label = "선택됨" if day == sel_day else "열기"
                st.button(btn_label, key=f"btn_{dk}", use_container_width=True, disabled=(day == sel_day), on_click=select_day, args=(day,))
            else:
                st.write("")
