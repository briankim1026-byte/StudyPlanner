import streamlit as st
from datetime import date
import time

# 1. 화면 기본 설정
st.set_page_config(page_title="나만의 스터디 플래너", layout="wide")

# 세션 상태(데이터 저장) 초기화
if 'todos' not in st.session_state:
    st.session_state.todos = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'elapsed_time' not in st.session_state:
    st.session_state.elapsed_time = 0

# 2. 사이드바 (목표 및 디데이)
with st.sidebar:
    st.header("🎯 나의 목표")
    goal = st.text_input("목표 대학이나 다짐을 적어보세요", placeholder="예: 연세대학교")
    if goal:
        st.success(f"목표: {goal}")
    
    st.divider()
    st.header("⏳ D-Day 계산기")
    d_day_name = st.text_input("시험 이름", placeholder="예: 기말고사, 모의고사")
    d_day_date = st.date_input("시험 날짜를 선택하세요")
    
    if d_day_name:
        today = date.today()
        delta = d_day_date - today
        if delta.days > 0:
            st.info(f"**{d_day_name}**까지 **D-{delta.days}** 남았어요! 파이팅!")
        elif delta.days == 0:
            st.error(f"오늘은 **{d_day_name}** 당일입니다! 실력 발휘 제대로 해봐요!")
        else:
            st.write(f"{d_day_name} 시험이 끝났습니다. 수고했어요!")

# 3. 메인 화면 (제목 및 날짜)
st.title("📚 나만의 스터디 플래너")
st.subheader(f"오늘은 {date.today().strftime('%Y년 %m월 %d일')} 입니다.")
st.write("---")

# 4. 할 일 추가 섹션
st.markdown("### ✨ 새로운 할 일 추가")
col1, col2 = st.columns([1, 2])
with col1:
    subject = st.text_input("과목명", placeholder="예: 수학")
with col2:
    task = st.text_input("할 일 내용", placeholder="예: 확률과 통계 15쪽 풀기")

if st.button("할 일 추가하기", use_container_width=True):
    if subject and task:
        st.session_state.todos.append({"subject": subject, "task": task, "done": False})
        st.rerun() # 추가 후 화면 새로고침
    else:
        st.warning("과목명과 할 일을 모두 적어주세요!")

st.write("---")

# 5. 할 일 목록 및 타이머 섹션
st.markdown("### 📝 오늘 할 일 및 타이머")

timer_col, list_col = st.columns([1, 2])

# [타이머(스톱워치) 기능]
with timer_col:
    st.info("⏱️ 집중 스톱워치")
    
    # 스톱워치 버튼 로직
    if st.button("▶️ 공부 시작 (타이머 켜기)"):
        if not st.session_state.is_running:
            st.session_state.start_time = time.time() - st.session_state.elapsed_time
            st.session_state.is_running = True
            
    if st.button("⏸️ 일시 정지"):
        if st.session_state.is_running:
            st.session_state.elapsed_time = time.time() - st.session_state.start_time
            st.session_state.is_running = False
            
    if st.button("🔄 초기화"):
        st.session_state.is_running = False
        st.session_state.elapsed_time = 0
        st.session_state.start_time = None

    # 현재 진행된 시간 계산
    current_time = st.session_state.elapsed_time
    if st.session_state.is_running:
        current_time = time.time() - st.session_state.start_time

    # 시간, 분, 초 계산해서 예쁘게 보여주기
    hours = int(current_time // 3600)
    minutes = int((current_time % 3600) // 60)
    seconds = int(current_time % 60)
    
    st.metric(label="총 공부 시간", value=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    if st.session_state.is_running:
        st.success("🔥 집중하는 중! 화면을 새로고침하면 시간이 업데이트됩니다.")

# [할 일 체크리스트 기능]
with list_col:
    if len(st.session_state.todos) == 0:
        st.write("아직 할 일이 없어요. 위에서 추가해 보세요!")
    else:
        for i, todo in enumerate(st.session_state.todos):
            # 체크박스 생성
            is_checked = st.checkbox(f"**[{todo['subject']}]** {todo['task']}", value=todo['done'], key=f"todo_{i}")
            # 체크 상태 저장
            st.session_state.todos[i]['done'] = is_checked
