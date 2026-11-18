import streamlit as st
import pandas as pd
from datetime import date

# 1. 화면 기본 설정 (넓게 쓰기)
st.set_page_config(page_title="프리미엄 스터디 플래너", layout="wide")

# 세련된 디자인을 위한 커스텀 CSS (배경색, 둥근 모서리 등)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #6B7280;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# 데이터를 컴퓨터(세션)에 임시 저장하기 위한 설정
if 'schedules' not in st.session_state:
    st.session_state.schedules = {}

# 2. 왼쪽 사이드바: 나의 목표 & D-Day
with st.sidebar:
    st.header("🎯 나의 다짐 & 목표")
    goal = st.text_input("최종 목표", placeholder="예: 연세대학교 경영학과")
    
    # 목표 등급 선택 칸 (드롭다운)
    target_grade = st.selectbox("목표 등급", ["선택하세요", "1등급 (상위 4%)", "2등급 (상위 11%)", "3등급 (상위 23%)", "올백(만점)"])
    
    if goal:
        st.success(f"🔥 목표: {goal}")
    if target_grade != "선택하세요":
        st.info(f"📈 다짐: 반드시 {target_grade} 달성!")
    
    st.divider()
    
    st.header("⏳ 기말고사 D-Day")
    exam_name = st.text_input("시험 이름", value="2학기 기말고사")
    exam_date = st.date_input("기말고사 날짜를 선택하세요")
    
    # D-Day 계산 로직
    if exam_name:
        today = date.today()
        delta = exam_date - today
        if delta.days > 0:
            st.error(f"🚨 **{exam_name}**까지 **D-{delta.days}** 남았습니다!")
            st.progress(max(0, 100 - (delta.days * 2))) # 긴장감 주는 프로그레스 바
        elif delta.days == 0:
            st.success(f"🎉 오늘은 **{exam_name}** 당일! 실력 발휘 제대로 하자!")
        else:
            st.write(f"**{exam_name}**이 끝났습니다. 수고 많았어요!")

# 3. 메인 화면: 달력(날짜 선택) & 일일 시간표
st.markdown('<p class="main-title">✨ 프리미엄 스터디 플래너</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">달력에서 날짜를 선택하고 오늘 하루의 시간표를 설계하세요.</p>', unsafe_allow_html=True)

# 달력 위젯 (여기서 날짜를 고르면 그날의 시간표가 뜸)
selected_date = st.date_input("📅 달력 (날짜 선택)", value=date.today())
date_str = str(selected_date)

st.write("---")
st.subheader(f"📝 {selected_date.strftime('%Y년 %m월 %d일')}의 시간표")

# 선택한 날짜의 시간표 데이터가 없으면 기본 표 만들어주기
if date_str not in st.session_state.schedules:
    st.session_state.schedules[date_str] = pd.DataFrame({
        "시간": ["09:00 - 10:30", "10:30 - 12:00", "13:00 - 15:00", "", ""],
        "과목": ["수학", "영어", "국어", "", ""],
        "학습 계획 (상세)": ["확률과 통계 기출 1회독", "영단어 100개 암기", "비문학 지문 3개 분석", "", ""],
        "완료": [False, False, False, False, False]
    })

# 노션(Notion) 스타일의 깔끔한 데이터 에디터 (표) 띄우기
# 표 안의 내용을 마우스로 클릭해서 엑셀처럼 바로 수정하고 행을 추가(Dynamic) 할 수 있음
edited_df = st.data_editor(
    st.session_state.schedules[date_str],
    num_rows="dynamic", # 밑에 빈칸을 계속 추가할 수 있는 기능
    use_container_width=True,
    column_config={
        "시간": st.column_config.TextColumn("⏰ 시간 (예: 14:00-16:00)", width="small"),
        "과목": st.column_config.TextColumn("📚 과목", width="small"),
        "학습 계획 (상세)": st.column_config.TextColumn("📝 구체적인 학습 계획", width="large"),
        "완료": st.column_config.CheckboxColumn("✅ 완료", default=False, width="small")
    }
)

# 수정한 시간표를 컴퓨터(세션)에 다시 저장
st.session_state.schedules[date_str] = edited_df

# 오늘 얼마나 완료했는지 보여주는 기능
total_tasks = len(edited_df[edited_df["과목"] != ""]) # 과목이 적혀있는 줄만 진짜 할 일로 계산
if total_tasks > 0:
    completed_tasks = edited_df["완료"].sum()
    st.caption(f"오늘의 달성률: {completed_tasks} / {total_tasks} 완료")
    if completed_tasks == total_tasks:
        st.balloons() # 다 하면 풍선 날리기!
