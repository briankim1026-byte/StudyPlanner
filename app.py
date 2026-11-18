import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta

# 1. 화면 기본 설정
st.set_page_config(page_title="기말고사 집중 스터디 플래너", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #6B7280; margin-bottom: 20px; }
    .stTextArea textarea { font-size: 0.9rem; line-height: 1.4; }
    .stButton button { font-size: 0.8rem; padding: 2px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 세션 상태(임시 저장소) 초기화 및 이월하기 함수 설정
# ---------------------------------------------------------
start_date = date(2026, 11, 23)
end_date = date(2026, 12, 23)
total_days = (end_date - start_date).days + 1
valid_dates = [start_date + timedelta(days=i) for i in range(total_days)]

for d in valid_dates:
    key = f"memo_{d.strftime('%Y_%m_%d')}"
    if key not in st.session_state:
        st.session_state[key] = ""

def rollover_task(curr_d, next_d):
    curr_key = f"memo_{curr_d.strftime('%Y_%m_%d')}"
    next_key = f"memo_{next_d.strftime('%Y_%m_%d')}"
    
    if next_key in st.session_state:
        curr_text = st.session_state[curr_key].strip()
        if curr_text: 
            existing_next = st.session_state[next_key]
            st.session_state[next_key] = existing_next + ("\n" if existing_next else "") + "➡️ [이월됨] " + curr_text
            st.session_state[curr_key] = ""

# ---------------------------------------------------------
# 2. 왼쪽 사이드바: 목표, 트래커, 타이머
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 나의 다짐")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    
    target_grade = st.selectbox(
        "목표 등급", 
        ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"]
    )
    
    st.divider()
    
    st.header("⚾ 오늘의 수학 타석")
    st.caption("매일 30문제 타격 목표! 꾸준함이 생명이다.")
    
    math_count = st.number_input(
        "오늘 푼 수학 문제 수", 
        min_value=0, 
        max_value=200, 
        value=0, 
        step=1
    )
    
    st.progress(min(math_count / 30.0, 1.0))
    
    if math_count >= 30:
        st.success("장외 홈런! ⚾ 오늘 수학 감각 완벽해!")
    elif math_count > 0:
        st.info("안타! 계속 배트를 휘둘러보자.")
        
    st.divider()

    st.header("🏀 하프타임 타이머")
    st.caption("50분 전력 질주 후 10분 휴식 (작전 타임)")
    
    timer_html = """
    <div style="text-align:center; padding:10px; border-radius:10px; background:#f3f4f6; border: 2px solid #e5e7eb;">
        <h1 id="time" style="color:#d97706; font-size: 2.5rem; margin: 10px 0;">50:00</h1>
        <button onclick="startTimer(50)" style="padding:8px 12px; margin:2px; cursor:pointer; background:#2563eb; color:white; border:none; border-radius:5px; font-weight:bold;">🔥 50분 집중</button>
        <button onclick="startTimer(10)" style="padding:8px 12px; margin:2px; cursor:pointer; background:#10b981; color:white; border:none; border-radius:5px; font-weight:bold;">💧 10분 휴식</button>
        <script>
            let timer;
            function startTimer(minutes) {
                clearInterval(timer);
                let time = minutes * 60;
                let display = document.getElementById('time');
                timer = setInterval(function () {
                    let min = parseInt(time / 60, 10);
                    let sec = parseInt(time % 60, 10);
                    min = min < 10 ? "0" + min : min;
                    sec = sec < 10 ? "0" + sec : sec;
                    display.textContent = min + ":" + sec;
                    if (--time < 0) {
                        clearInterval(timer);
                        display.textContent = "삐빅! 🏀";
                    }
                }, 1000);
            }
        </script>
    </div>
    """
    components.html(timer_html, height=180)

# ---------------------------------------------------------
# 3. 메인 화면: 맞춤형 기간 달력 (11.23 ~ 12.23)
# ---------------------------------------------------------
st.markdown('<p class="main-title">📅 기말고사 집중 달력 (11/23 ~ 12/23)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">계획을 못 지켰다면 자책하지 말고 [내일로 이월] 버튼을 눌러 털어버리세요.</p>', unsafe_allow_html=True)

all_dates = list(valid_dates)
while len(all_dates) % 7 != 0:
    all_dates.append(None)

weeks = [all_dates[i:i+7] for i in range(0, len(all_dates), 7)]
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    color = "red" if i == 6 else "#2563EB" if i == 5 else "#374151"
    header_cols[i].markdown(
        f"<div style='text-align: center; font-weight: bold; color: {color}; padding-bottom: 10px;'>{day_name}</div>", 
        unsafe_allow_html=True
    )

st.write("---")

for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None:
                day_color = "red" if i == 6 else "#2563EB" if i == 5 else "black"
                
                st.markdown(
                    f"<div style='color: {day_color}; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>{day.month}/{day.day}</div>", 
                    unsafe_allow_html=True
                )
                
                key = f"memo_{day.strftime('%Y_%m_%d')}"
                
                st.text_area(
                    label=f"{day.month}월 {day.day}일 시간표", 
                    label_visibility="collapsed", 
                    key=key, 
                    height=140, 
                    placeholder="국어 1강\n수학 15p"
                )
                
                if day < end_date:
                    next_day = day + timedelta(days=1)
                    st.button(
                        "➡️ 쿨하게 이월", 
                        key=f"btn_{key}", 
                        on_click=rollover_task, 
                        args=(day, next_day), 
                        use_container_width=True
                    )
            else:
                st.write("")
    st.write("")
