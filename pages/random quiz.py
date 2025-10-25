import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import random
import json

# Google GenAI SDK 사용을 위한 임포트
try:
    from google import genai
    from google.genai.errors import APIError
    GEMINI_AVAILABLE = True
except ImportError:
    st.error("Google GenAI 라이브러리가 설치되지 않았습니다. 'pip install google-genai' 명령어로 설치해주세요.")
    GEMINI_AVAILABLE = False


# ------------------------------------
# 📌 1. 필수 설정 및 함수 정의
# ------------------------------------

# Streamlit 설정 및 DB 경로 설정
# 레이아웃을 wide로 변경하여 퀴즈 화면을 넓게 사용할 것을 권장합니다.
st.set_page_config(page_title="랜덤 퀴즈 생성", layout="wide") 

# DB 경로 설정 (pages/random_quiz.py 기준)
DB_PATH = Path(__file__).parent.parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = init_db()

# 데이터 조회 함수: 모든 고유 키워드를 가져옵니다.
def get_unique_keywords():
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT keyword FROM keywords")
    rows = cur.fetchall()
    return [row[0] for row in rows]

# ------------------------------------
# 📌 2. 퀴즈 생성 함수 (Gemini Pro 사용)
# ------------------------------------

# @st.cache_data를 사용하여 퀴즈 생성 비용 절감 (키워드가 변경되지 않으면 캐시 사용)
@st.cache_data(show_spinner="AI가 질문 키워드 기반으로 퀴즈를 생성하는 중...")
def generate_quiz_with_ai(keyword_list_str, num_questions):
    if not GEMINI_AVAILABLE:
        st.error("Google GenAI 라이브러리가 없어 퀴즈를 생성할 수 없습니다.")
        return None
    
    try:
        # Streamlit Secrets에서 API 키 가져오기
        client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except Exception:
        st.error("Gemini API 키를 Streamlit Secrets에 설정해주세요. (gemini.api_key)")
        return None
        
    prompt = f"""
    당신은 훌륭한 영어 교사입니다. 다음 키워드 목록을 활용하여 {num_questions}개의 객관식 퀴즈를 생성해 주세요.
    각 퀴즈는 키워드의 의미나 용법에 대한 질문이어야 합니다.
    
    키워드 목록: {keyword_list_str}
    
    ---
    
    요구사항:
    1. 각 퀴즈는 질문, 4개의 보기, 정답(보기 번호 1~4)을 포함해야 합니다.
    2. 생성된 퀴즈는 반드시 다음 JSON 형식으로만 출력해야 합니다.
       
       {{
         "quiz_title": "오늘의 영어 질문 키워드 퀴즈",
         "questions": [
           {{
             "q_num": 1,
             "question": "질문 내용...",
             "options": ["1. 보기 1", "2. 보기 2", "3. 보기 3", "4. 보기 4"],
             "answer": 2
           }},
           // 다음 질문...
         ]
       }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # 더 빠르고 비용 효율적인 모델 사용
            contents=prompt,
            config={
                "response_mime_type": "application/json", # JSON 출력 형식 강제
                "temperature": 0.7
            }
        )
        
        # response.text에 JSON 문자열이 포함되어 있습니다.
        return json.loads(response.text)
        
    except APIError as e:
        st.error(f"Gemini API 오류: {e}")
        st.info("API 키, 요금제 상태, 사용량 제한 등을 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"퀴즈 생성 중 오류가 발생했습니다: {e}")
        return None

# ------------------------------------
# 📌 3. 페이지 렌더링 (나머지 코드는 그대로 사용)
# ------------------------------------

# 세션 상태 초기화 (퀴즈 관련)
if "quiz_data" not in st.session_state:
    st.session_state["quiz_data"] = None
if "answers" not in st.session_state:
    st.session_state["answers"] = {}
if "submitted" not in st.session_state:
    st.session_state["submitted"] = False

st.markdown("<h1 style='text-align:center; margin-bottom:0.25rem;'>🎲 질문 키워드 랜덤 퀴즈 🎲</h1>", unsafe_allow_html=True)
st.markdown("---")


# ------------------------------------
# 퀴즈 설정 및 생성
# ------------------------------------
unique_keywords = get_unique_keywords()
keyword_list_str = ", ".join(unique_keywords)

if not unique_keywords:
    st.info("아직 제출된 키워드가 없습니다. 퀴즈를 생성할 수 없습니다.")
else:
    st.info(f"현재 총 {len(unique_keywords)}개의 질문 키워드가 있습니다. 이를 기반으로 퀴즈를 생성합니다.")
    
    # 퀴즈 설정
    col_num, col_btn = st.columns([3, 1])
    with col_num:
        num_questions = st.slider("생성할 퀴즈 문항 수", min_value=1, max_value=10, value=3, key="num_q")
    
    # 퀴즈 생성 버튼 (키워드 목록이 변경되면 캐시를 무효화)
    if col_btn.button("✨ 새 퀴즈 생성 ✨", use_container_width=True, type="primary"):
        # 기존 세션 상태 초기화
        st.session_state["quiz_data"] = None
        st.session_state["answers"] = {}
        st.session_state["submitted"] = False
        
        # 새 퀴즈 생성 및 저장 (캐시를 사용)
        quiz_json = generate_quiz_with_ai(keyword_list_str, num_questions)
        st.session_state["quiz_data"] = quiz_json
        
        # 퀴즈 생성 후 바로 표시되도록 Rerun
        st.rerun()

# ------------------------------------
# 퀴즈 풀기 및 채점
# ------------------------------------

if st.session_state["quiz_data"]:
    quiz_data = st.session_state["quiz_data"]
    st.subheader(f"📝 {quiz_data['quiz_title']}")
    st.markdown("---")

    questions = quiz_data['questions']
    
    # 퀴즈 폼 시작
    with st.form(key="quiz_form"):
        # 각 질문 렌더링
        for q in questions:
            question_text = f"**Q{q['q_num']}.** {q['question']}"
            
            # 보기 텍스트만 추출
            options_text = [option.split(".")[1].strip() for option in q['options']]
            
            # 정답을 알고 있는 경우 (제출 후)
            is_correct = None
            user_answer_num = None
            if st.session_state["submitted"]:
                # 저장된 답변은 1, 2, 3, 4 번호입니다.
                user_answer_num = st.session_state["answers"].get(f"q_{q['q_num']}")
                if user_answer_num is not None:
                    is_correct = (user_answer_num == q['answer'])
                    
            
            # 사용자 답변 선택
            selected_option_text = st.radio(
                question_text,
                options=options_text,
                index=None, # 기본값은 선택하지 않음
                key=f"q_{q['q_num']}_radio",
                disabled=st.session_state["submitted"]
            )
            
            # 선택된 보기 텍스트를 기반으로 보기 번호를 찾아서 딕셔너리에 저장
            if selected_option_text:
                # 선택된 텍스트의 인덱스(0부터 시작) + 1 이 보기 번호입니다.
                selected_index = options_text.index(selected_option_text)
                st.session_state["answers"][f"q_{q['q_num']}"] = selected_index + 1

            
            # 제출 후 피드백 표시
            if st.session_state["submitted"]:
                
                # 사용자가 선택한 답변의 텍스트를 찾습니다.
                user_choice_text = selected_option_text if selected_option_text else '선택 안 함'
                
                if is_correct:
                    st.success(f"✅ 정답입니다! (선택: {user_choice_text})")
                else:
                    st.error(f"❌ 오답입니다. (선택: {user_choice_text})")
                
                # 정답 번호에 해당하는 텍스트를 찾습니다.
                correct_answer_text = options_text[q['answer'] - 1] 
                st.info(f"⭐ 정답: {q['answer']}번 ({correct_answer_text})")
            
            st.markdown("---")


        # 제출 버튼
        submitted = st.form_submit_button("제출하고 채점하기", disabled=st.session_state["submitted"])
        
        if submitted:
            # 모든 질문에 답했는지 확인
            if len(st.session_state["answers"]) < len(questions):
                 st.warning("모든 질문에 답해주세요.")
            else:
                st.session_state["submitted"] = True
                st.rerun()

    # 채점 결과 표시
    if st.session_state["submitted"]:
        total = len(questions)
        correct_count = 0
        for q in questions:
            user_answer_num = st.session_state["answers"].get(f"q_{q['q_num']}")
            if user_answer_num == q['answer']:
                correct_count += 1
                
        score = (correct_count / total) * 100
        
        st.metric(label="최종 점수", value=f"{score:.1f}점", delta=f"{correct_count} / {total} 문제 정답")
        st.balloons()


# ------------------------------------
# 메인 페이지 링크 버튼
# ------------------------------------
st.markdown("---")
col_empty, col_home = st.columns([3, 1])

with col_home:
    if st.button("🏠 메인 페이지로 돌아가기", use_container_width=True):
        st.switch_page("main_page.py")