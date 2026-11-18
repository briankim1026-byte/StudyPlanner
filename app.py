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
    /* 이월 버튼 스타일 살짝 다듬기 */
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

# 각 날짜별 메모장을 세션에 미리 만들어두기
for d in valid_dates:
    key = f"memo_{d.strftime('%Y_%m_%d')}"
    if key not in st.session_state:
        st.session_state[key] = ""

# ➡️ [기능 3] 내일로 쿨하게 이월하기 로직
def rollover_task(curr_d, next_d):
    curr_key = f"memo_{curr_d.strftime('%Y_%m_%d')}"
    next_key = f"memo_{next_d.strftime('%Y_%m_%d')}"
    
    if next_key in st.session_state:
        curr_text = st.session_state[curr_key].strip()
        if curr_text: # 적힌 내용이 있을 때만 이월
            existing_next = st.session_state[next_key]
            # 다음날 메모장 밑에 이월된 내용 추가
            st.session_state[next_key] = existing_next + ("\n" if existing_next else "") + "➡️ [이월됨] " + curr_text
            # 오늘 메모장은 비우기
            st.session_state[curr_key] = ""

# ---------------------------------------------------------
# 2. 왼쪽 사이드바: 목표, 트래커, 타이머
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 나의 다짐")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    target_grade = st.selectbox("목표 등급", ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"])
    
    st.divider()
    
    # ⚾ [기능 1] 수학 전용 타격 트래커
    st.header("⚾ 오늘의 수학 타석")
    st.caption("매일 30문제 타격 목표! 꾸준함이 생명이다.")
    math_count = st.number_input("오늘 푼 수학 문제 수", min_value=0, max_value=200, value=0, step=1)
    
    # 프로그레스 바 (30문제 기준 100%)
    st.progress(min(math_count / 30.0, 1.0))
    if math_count >= 30:
        st.success("장외 홈런! ⚾ 오늘 수학 감각 완벽해!")
    elif math_count > 0:
        st.info("안타! 계속 배트를 휘둘러보자.")
        
    st.divider()

    # 🏀 [기능 2] 농구 하프타임 타이머
    st.header("🏀 하프타임 타이머")
    st.caption("50분 전력 질주 후 10분 휴식 (작전 타임)")
    
    # 타이머용 HTML/JS 코드 (화면 멈춤 방지)
    timer_html = """
    <div style="text-align:center; padding:10px; border-radius:10px; background:#f3f4f6; border: 2px solid #e5e7eb;">
        <h1 id="time" style="
