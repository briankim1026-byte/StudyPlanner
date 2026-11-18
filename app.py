import streamlit as st
from datetime import date, timedelta

# 1. 화면 기본 설정
st.set_page_config(page_title="기말고사 집중 스터디 플래너", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #6B7280; margin-bottom: 20px; }
    .stTextArea textarea { font-size: 0.9rem; line-height: 1.4; }
    </style>
""", unsafe_allow_html=True)

# 2. 왼쪽 사이드바: 나의 다짐 & D-Day
with st.sidebar:
    st.header("🎯 나의 다짐 & 목표")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    target_grade = st.selectbox("목표 등급", ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"])
    
    if goal:
        st.success(f"🔥 목표: {goal}")
    if target_grade != "선택하세요":
        st.info(f"📈 다짐: 반드시 {target_grade} 달성!")
    
    st.divider()
    
    st.header("⏳ 기말고사 D-Day")
    exam_name = st.text_input("시험 이름", value="2학기 기말고사")
    exam_date = st.date_input("기말고사 날짜를 선택하세요", value=date(2026, 12, 23))
    
    if exam_name:
        today = date.today()
        delta = exam_date - today
        if delta.days > 0:
            st.error(f"🚨 **{exam_name}**까지 **D-{delta.days}** 남았습니다!")
            st.progress(max(0, min(100, 100 - (delta.days * 2)))) 
        elif delta.days == 0:
            st.success(f"🎉 오늘은 **{exam_name}** 당일! 파이팅!")
        else:
            st.write(f"**{exam_name}**이 끝났습니다. 수고 많았어요!")

# 3. 메인 화면: 맞춤형 기간 달력 (11.23 ~ 12.23)
st.markdown('<p class="main-title">📅 기말고사 집중 달력 (11/23 ~ 12/23)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">다음 주 월요일부터 12월 23일까지의 실전 계획을 세워보세요.</p>', unsafe_allow_html=True)

# 날짜 계산 로직 (2026년 11월 23일 ~ 2026년 12월 23일)
start_date = date(2026, 11, 23)
end_date = date(2026, 12, 23)
total_days = (end_date - start_date).days + 1

# 시작일부터 종료일까지의 모든 날짜 리스트 만들기
all_dates = [start_date + timedelta(days=i) for i in range(total_days)]

# 마지막 주 빈칸 채우기 (7칸을 맞추기 위해)
while len(all_dates) % 7 != 0:
    all_dates.append(None)

# 7일씩 묶어서 주(Week) 단위 리스트로 만들기
weeks = [all_dates[i:i+7] for i in range(0, len(all_dates), 7)]

# 요일 헤더 출력 (월~일 7칸)
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    color = "red" if i == 6 else "#2563EB" if i == 5 else "#374151"
    header_cols[i].markdown(f"<div style='text-align: center; font-weight: bold; color: {color}; padding-bottom: 10px;'>{day_name}</div>", unsafe_allow_html=True)

st.write("---")

# 달력 네모 칸 만들기
for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day is not None: # 진짜 날짜가 있는 칸
                day_color = "red" if i == 6 else "#2563EB" if i == 5 else "black"
                
                # '11/23' 형식으로 날짜 표시
                st.markdown(f"<div style='color: {day_color}; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px;'>{day.month}/{day.day}</div>", unsafe_allow_html=True)
                
                # 메모장 생성
                st.text_area(
                    label=f"{day.month}월 {day.day}일 시간표", 
                    label_visibility="collapsed",
                    key=f"memo_{day.year}_{day.month}_{day.day}", 
                    height=180, 
                    placeholder="계획 입력..."
                )
            else: # 날짜가 없는 빈칸 (12월 24일 이후 칸들)
                st.write("")
    st.write("") # 한 주가 끝날 때마다 간격 띄우기
