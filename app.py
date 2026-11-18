import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta

# 1. 화면 기본 설정
st.set_page_config(page_title="프리미엄 스터디 플래너", layout="wide")

# ✨ 디자인 끝판왕 CSS 적용 ✨
st.markdown("""
    <style>
    /* 전체 배경을 은은한 파스텔 톤으로 */
    .stApp { 
        background: linear-gradient(135deg, #f8f9fa 0%, #e0eaf5 100%); 
    }
    /* 메인 타이틀: 홀로그램 그라데이션 텍스트 */
    .main-title { 
        font-size: 2.8rem; 
        font-weight: 900; 
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        text-align: center; 
        margin-bottom: 5px; 
    }
    .sub-title { 
        font-size: 1.1rem; 
        color: #495057; 
        font-weight: 600; 
        text-align: center; 
        margin-bottom: 30px; 
    }
    /* 달력 메모장(텍스트 입력창) 고급스럽게 다듬기 */
    .stTextArea textarea { 
        font-size: 0.95rem; 
        line-height: 1.5;
        border-radius: 12px; 
        border: 1.5px solid #dee2e6; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.04); 
        background-color: #ffffff;
        transition: all 0.2s ease; 
    }
    /* 메모장 클릭(집중)했을 때 파란색 테두리와 네온 그림자 효과 */
    .stTextArea textarea:focus { 
        border-color: #2575fc; 
        box-shadow: 0 0 8px rgba(37, 117, 252, 0.3); 
    }
    </style>
""", unsafe_allow_html=True)

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
    <div style="text-align:center; padding:10px; border-radius:12px; background:#ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;">
        <h1 id="time" style="color:#d97706; font-size: 2.5rem; margin: 10px 0;">50:00</h1>
        <button onclick="startTimer(50)" style="padding:8px 12px; margin:2px; cursor:pointer; background:linear-gradient(45deg, #2563eb, #3b82f6); color:white; border:none; border-radius:8px; font-weight:bold;">🔥 50분 집중</button>
        <button onclick="startTimer(10)" style="padding:8px 12px; margin:2px; cursor:pointer; background:linear-gradient(45deg, #10b981, #34d399); color:white; border:none; border-radius:8px; font-weight:bold;">💧 10분 휴식</button>
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
st.markdown('<p class="main-title">📅 기말고사 집중 달력</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">11/23 ~ 12/23 실전 대비 시간표</p>', unsafe_allow_html=True)

# 날짜 계산 (11월 23일 ~ 12월 23일)
start_date = date(2026, 11, 23)
end_date = date(2026, 12, 23)
total_days = (end_date - start_date).days + 1
valid_dates = [start_date + timedelta(days=i) for i in range(total_days)]

all_dates = list(valid_dates)
while len(all_dates) % 7 != 0:
    all_dates.append(None)

weeks = [all_dates[i:i+7] for i in range(0, len(all_dates), 7)]
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

# 요일 헤더
header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    color = "red" if i == 6 else "#2575fc" if i == 5 else "#495057"
    header_cols[i].markdown(
        f"<div style='text-align: center; font-weight: 800; color: {color}; padding-bottom: 10px;'>{day_name}</div>", 
        unsafe_allow_html=True
    )

st.write("---")

# 달력 칸 생성
for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None:
                day_color = "red" if i == 6 else "#2575fc" if i == 5 else "#343a40"
                
                st.markdown(
                    f"<div style='color: {day_color}; font-weight: 800; font-size: 1.1rem; margin-bottom: 5px; padding-left: 5px;'>{day.month}/{day.day}</div>", 
                    unsafe_allow_html=True
                )
                
                key = f"memo_{day.strftime('%Y_%m_%d')}"
                
                st.text_area(
                    label=f"{day.month}월 {day.day}일 시간표", 
                    label_visibility="collapsed", 
                    key=key, 
                    height=150, 
                    placeholder="국어 1강\n수학 15p"
                )
            else:
                st.write("")
    st.write("")
