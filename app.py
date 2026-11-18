import streamlit as st
import calendar
from datetime import date, datetime

# 1. 화면 기본 설정 (달력을 넓게 쓰기 위해 화면을 최대로 확장)
st.set_page_config(page_title="월간 달력 스터디 플래너", layout="wide")

# 세련된 디자인을 위한 커스텀 CSS
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #6B7280; margin-bottom: 20px; }
    /* 텍스트 입력창 디자인 다듬기 */
    .stTextArea textarea { font-size: 0.9rem; line-height: 1.4; }
    </style>
""", unsafe_allow_html=True)

# 2. 왼쪽 사이드바: 나의 다짐 & D-Day
with st.sidebar:
    st.header("🎯 나의 다짐 & 목표")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    
    # 목표 등급 선택 칸
    target_grade = st.selectbox("목표 등급", ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"])
    
    if goal:
        st.success(f"🔥 목표: {goal}")
    if target_grade != "선택하세요":
        st.info(f"📈 다짐: 반드시 {target_grade} 달성!")
    
    st.divider()
    
    st.header("⏳ 기말고사 D-Day")
    exam_name = st.text_input("시험 이름", value="2학기 기말고사")
    exam_date = st.date_input("기말고사 날짜를 선택하세요")
    
    if exam_name:
        today = date.today()
        delta = exam_date - today
        if delta.days > 0:
            st.error(f"🚨 **{exam_name}**까지 **D-{delta.days}** 남았습니다!")
            st.progress(max(0, 100 - (delta.days * 2))) # 날짜에 맞춰 줄어드는 게이지
        elif delta.days == 0:
            st.success(f"🎉 오늘은 **{exam_name}** 당일! 파이팅!")
        else:
            st.write(f"**{exam_name}**이 끝났습니다. 수고 많았어요!")

# 3. 메인 화면: 30일 달력형 플래너
st.markdown('<p class="main-title">📅 월간 스터디 플래너</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">탁상달력처럼 한눈에 한 달 계획을 세워보세요. (적은 내용은 자동 저장됩니다)</p>', unsafe_allow_html=True)

# 현재 컴퓨터의 연도와 월 가져오기
now = datetime.now()
year = now.year
month = now.month

st.subheader(f"✨ {year}년 {month}월")

# 달력 생성기 (이번 달 날짜 계산)
cal = calendar.Calendar()
month_days = cal.monthdatescalendar(year, month)

# 요일 헤더 출력 (월~일 7칸)
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    # 토요일은 파란색, 일요일은 빨간색으로 표시
    color = "red" if i == 6 else "#2563EB" if i == 5 else "#374151"
    header_cols[i].markdown(f"<div style='text-align: center; font-weight: bold; color: {color}; padding-bottom: 10px;'>{day_name}</div>", unsafe_allow_html=True)

st.write("---")

# 달력 네모 칸 만들기 (7칸씩 줄 바꿈)
for week in month_days:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day.month == month:
                # 토요일(5), 일요일(6) 색상 다르게 적용
                day_color = "red" if i == 6 else "#2563EB" if i == 5 else "black"
                
                # 날짜 표시
                st.markdown(f"<div style='color: {day_color}; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>{day.day}일</div>", unsafe_allow_html=True)
                
                # 시간표를 자유롭게 적을 수 있는 큰 메모장(텍스트 에어리어)
                # key 값을 날짜별로 다르게 줘서 각 칸마다 따로 저장되게 설정
                st.text_area(
                    label=f"{day.day}일 시간표", 
                    label_visibility="collapsed", # 위쪽 라벨 숨기기 (깔끔하게)
                    key=f"memo_{year}_{month}_{day.day}", 
                    height=180, # 칸 높이 (더 길게 원하면 숫자 늘리기)
                    placeholder="국어: 1강\n수학: 15p"
                )
            else:
                # 이번 달 날짜가 아닌 빈칸 처리
                st.write("")
    st.write("") # 한 주(가로줄)가 끝날 때마다 간격 띄우기
