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

# 3. DB에서 기존 데이터 불러오기 (새로고침/재접속 시 자동 복원)
if "db_loaded" not in st.session_state:
    # 사이드바 설정 불러오기
    res_set = supabase.table("user_settings").select("*").eq("id", 1).execute()
    if res_set.data:
        row = res_set.data[0]
        st.session_state["goal"] = row.get("goal", "")
        st.session_state["target_grade"] = row.get("target_grade", "선택하세요")
        st.session_state["math_count"] = int(row.get("math_count", 0))
    else:
        st.session_state["goal"] = ""
        st.session_state["target_grade"] = "선택하세요"
        st.session_state["math_count"] = 0

    # 날짜별 기록 불러오기
    res_logs = supabase.table("daily_logs").select("*").execute()
    for row in res_logs.data:
        dk = row["day_key"]
        st.session_state[f"memo_{dk}"] = row.get("memo", "")
        st.session_state[f"chk_{dk}"] = bool(row.get("is_done", False))
        st.session_state[f"photo_url_{dk}"] = row.get("photo_url", "")

    st.session_state["db_loaded"] = True

# 4. 자동 저장 함수
def save_settings():
    supabase.table("user_settings").upsert({
        "id": 1,
        "goal": st.session_state.get("goal", ""),
        "target_grade": st.session_state.get("target_grade", "선택하세요"),
        "math_count": int(st.session_state.get("math_count", 0))
    }).execute()

def save_day(day_key):
    supabase.table("daily_logs").upsert({
        "day_key": day_key,
        "memo": st.session_state.get(f"memo_{day_key}", ""),
        "is_done": bool(st.session_state.get(f"chk_{day_key}", False)),
        "photo_url": st.session_state.get(f"photo_url_{day_key}", "")
    }).execute()

# CSS (한 줄로 안전하게 처리 및 첨부 박스 크기 최적화)
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e0eaf5 100%); }
    .main-title { font-size: 2.8rem; font-weight: 900; background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #495057; font-weight: 600; text-align: center; margin-bottom: 30px; }
    .stTextArea textarea { font-size: 0.95rem; line-height: 1.5; border-radius: 12px; border: 1.5px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.04); background-color: #ffffff; transition: all 0.2s ease; }
    .stTextArea textarea:focus { border-color: #2575fc; box-shadow: 0 0 8px rgba(37, 117, 252, 0.3); }
    .stCheckbox { margin-top: -10px; margin-bottom: 10px; padding-left: 5px; }
    [data-testid="stFileUploadDropzone"] { padding: 15px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🎯 나의 다짐")
    st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과", key="goal", on_change=save_settings)
    grade_options = ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"]
    if st.session_state.get("target_grade") not in grade_options:
        st.session_state["target_grade"] = "선택하세요"
    st.selectbox("목표 등급", grade_options, key="target_grade", on_change=save_settings)
    
    st.divider()
    
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
    <div style='text-align:center; padding:10px; border-radius:12px; background:#ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;'>
        <h1 id='time' style='color:#2575fc; font-size: 2.5rem; margin: 10px 0;'>00:00</h1>
        <div style='margin-bottom: 10px;'>
            <input type='number' id='customMin' value='50' min='1' style='width: 60px; padding: 5px; border-radius: 5px; border: 1px solid #ccc; text-align: center; font-weight: bold;'> 분
        </div>
        <button onclick='startCustomTimer()' style='padding:8px 12px; margin:2px; cursor:pointer; background:linear-gradient(45deg, #2563eb, #3b82f6); color:white; border:none; border-radius:8px; font-weight:bold;'>🔥 집중 시작</button>
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

st.markdown('<p class="main-title">📅 기말고사 집중 달력</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">11/23 ~ 12/23 실전 대비 시간표</p>', unsafe_allow_html=True)

start_date = date(2026, 11, 23)
end_date = date(2026, 12, 23)
total_days = (end_date - start_date).days + 1
valid_dates = [start_date + timedelta(days=i) for i in range(total_days)]

all_dates = list(valid_dates)
while len(all_dates) % 7 != 0:
    all_dates.append(None)

weeks = [all_dates[i:i+7] for i in range(0, len(all_dates), 7)]
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    color = "red" if i == 6 else "#2575fc" if i == 5 else "#495057"
    header_cols[i].markdown(f"<div style='text-align: center; font-weight: 800; color: {color}; padding-bottom: 10px;'>{day_name}</div>", unsafe_allow_html=True)

st.write("---")

for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None:
                day_key = day.strftime('%Y_%m_%d')
                day_color = "red" if i == 6 else "#2575fc" if i == 5 else "#343a40"
                st.markdown(f"<div style='color: {day_color}; font-weight: 800; font-size: 1.1rem; margin-bottom: 5px; padding-left: 5px;'>{day.month}/{day.day}</div>", unsafe_allow_html=True)
                
                # 1. 시간표 적는 칸
                text_key = f"memo_{day_key}"
                if text_key not in st.session_state:
                    st.session_state[text_key] = ""
                st.text_area(
                    label=f"{day.month}월 {day.day}일 시간표",
                    label_visibility="collapsed",
                    key=text_key,
                    height=130,
                    placeholder="국어 1강\n수학 15p",
                    on_change=save_day,
                    args=(day_key,)
                )
                
                # 2. 하루 완료 체크박스
                chk_key = f"chk_{day_key}"
                if chk_key not in st.session_state:
                    st.session_state[chk_key] = False
                if st.checkbox("✅ 하루 완료", key=chk_key, on_change=save_day, args=(day_key,)):
                    st.success("달성!")
                
                # 3. 그날의 개별 사진 업로드 칸
                photo_key = f"photo_{day_key}"
                st.caption("📸 사진 인증")
                uploaded_file = st.file_uploader(
                    f"{day.month}월 {day.day}일 인증",
                    type=["jpg", "jpeg", "png"],
                    key=photo_key,
                    label_visibility="collapsed"
                )
                
                # 새 사진을 올리면 Supabase 스토리지에 업로드 후 URL 저장
                if uploaded_file is not None:
                    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
                    if st.session_state.get(f"last_uploaded_{day_key}") != file_id:
                        ext = uploaded_file.name.split(".")[-1].lower()
                        file_path = f"{day_key}_{int(time.time())}.{ext}"
                        supabase.storage.from_("photos").upload(
                            file_path,
                            uploaded_file.getvalue(),
                            {"content-type": uploaded_file.type}
                        )
                        public_url = supabase.storage.from_("photos").get_public_url(file_path)
                        st.session_state[f"photo_url_{day_key}"] = public_url
                        st.session_state[f"last_uploaded_{day_key}"] = file_id
                        save_day(day_key)
                
                # 저장된 사진이 있으면 캘린더 칸 안에 표시
                saved_url = st.session_state.get(f"photo_url_{day_key}", "")
                if saved_url:
                    st.image(saved_url, use_container_width=True)
            else:
                st.write("")
    st.write("---")
