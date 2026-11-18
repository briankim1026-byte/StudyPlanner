import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta

# 1. 화면 기본 설정
st.set_page_config(page_title="프리미엄 스터디 플래너", layout="wide")

# ✨ 디자인 끝판왕 CSS 적용 ✨
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e0eaf5 100%); }
    .main-title { 
        font-size: 2.8rem; font-weight: 900; 
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        text-align: center; margin-bottom: 5px; 
    }
    .sub-title { font-size: 1.1rem; color: #495057; font-weight: 600; text-align: center; margin-bottom: 30px; }
    .stTextArea textarea { 
        font-size: 0.95rem; line-height: 1.5; border-radius: 12px; 
        border: 1.5px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.04); 
        background-color: #ffffff; transition: all 0.2s ease; 
    }
    .stTextArea textarea:focus { border-color: #2575fc; box-shadow: 0 0 8px rgba(37, 117, 252, 0.3); }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 왼쪽 사이드바: 목표, 트래커, 맞춤 타이머, 사진 인증
# ---------------------------------------------------------
with st.sidebar:
    st.header("🎯 나의 다짐")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    target_grade = st.selectbox(
        "목표 등급", 
        ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"]
    )
    
    st.divider()
    
    # [수정됨] 설명글 삭제 및 결과가 바로 나오도록 배치
    st.header("⚾ 오늘의 수학 타석")
    math_count = st.number_input("오늘 푼 수학 문제 수 (목표: 30)", min_value=0, max_value=200, value=0, step=1)
    
    st.progress(min(math_count / 30.0, 1.0))
    if math_count >= 30:
        st.success("장외 홈런! ⚾ 오늘 수학 감각 완벽해!")
    elif math_count > 0:
        st.info("안타! 계속 배트를 휘둘러보자.")
        
    st.divider()

    # [수정됨] 원하는 분(시간)을 직접 입력하는 타이머
    st.header("⏱️ 맞춤형 집중 타이머")
    
    timer_html = """
    <div style="text-align:center; padding:10px; border-radius:12px; background
