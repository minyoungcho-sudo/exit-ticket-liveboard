# random_quiz_modern_ui.py — Page 2 with the same modern UI as Page 1 (bright tone)
# Drop-in replacement for your current Page 2 (랜덤 퀴즈) code. 기능 동일, UI만 통일.

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import random
import json

# Google GenAI SDK 사용을 위한 임포트 (원래 로직 그대로 유지)
try:
    from google import genai
    from google.genai.errors import APIError
    GEMINI_AVAILABLE = True
except ImportError:
    st.error("Google GenAI 라이브러리가 설치되지 않았습니다. 'pip install google-genai' 명령어로 설치해주세요.")
    GEMINI_AVAILABLE = False


# ------------------------------------
# 📌 1) 공통 스타일: Page 1과 동일한 모던 UI 적용
# ------------------------------------

st.set_page_config(
    page_title="민영쌤 질문방 | Bright Modern UI",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Page 2는 pages 폴더 아래에 있으므로, 프로젝트 루트의 fonts 디렉토리를 바라보도록 설정
FONT_DIR = Path(__file__).parent.parent / "fonts"

def _find_font_file():
    if not FONT_DIR.exists():
        return None
    cand = list(FONT_DIR.glob("**/*NanumGothic*.ttf"))
    if not cand:
        cand = list(FONT_DIR.glob("**/*.ttf"))
    return cand[0] if cand else None

_FONT_FILE = _find_font_file()
if _FONT_FILE:
    FONT_PATH = str(_FONT_FILE.resolve())
    _css = f"""
    <style>
      :root {{
        --bg-color: #f9fafb;
        --card-bg: #ffffff;
        --card-bd: #e5e7eb;
        --text-main: #1f2937;
        --text-dim: #6b7280;
        --brand-1: #6366f1; /* indigo-500 */
        --brand-2: #06b6d4; /* cyan-500 */
        --radius-xxl: 18px;
        --radius-lg: 12px;
      }}

      @font-face {{
        font-family: 'NanumGothic';
        src: url('file://{FONT_PATH}') format('truetype');
      }}

      html, body, .stApp {{
        font-family: 'NanumGothic', sans-serif !important;
        background-color: var(--bg-color) !important;
        color: var(--text-main) !important;
      }}

      .stApp .block-container {{
        padding-top: 4rem !important;
        padding-bottom: 3rem !important;
        max-width: 900px !important;
      }}

      .hero-title {{
        text-align:center;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, var(--brand-1), var(--brand-2));
        -webkit-background-clip: text;
        color: transparent;
      }}
      .hero-sub {{
        text-align:center;
        color: var(--text-dim);
        margin-top: .25rem;
        margin-bottom: 1rem;
      }}

      .modern-card {{
        background: var(--card-bg);
        border: 1px solid var(--card-bd);
        border-radius: var(--radius-xxl);
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      }}
      .card-title {{
        font-weight: 700;
        font-size: 18px;
        margin-bottom: 8px;
        color: var(--brand-1);
      }}

      /* Buttons */
      .stButton > button {{
        border-radius: var(--radius-lg) !important;
        border: 1px solid #cbd5e1 !important;
        background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(6,182,212,0.25)) !important;
        box-shadow: 0 6px 16px rgba(99,102,241,0.15) !important;
        color: var(--text-main) !important;
        padding: 0.6rem 1rem !important;
        transition: transform .06s ease, box-shadow .2s ease !important;
      }}
      .stButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 8px 20px rgba(99,102,241,0.25) !important; }}
      .stButton > button:active {{ transform: translateY(0); filter: brightness(.97); }}

      /* Inputs */
      label {{ color: var(--text-dim) !important; font-weight: 600 !important; }}
      .stTextInput > div > div > input,
      .stTextArea textarea,
      .stSelectbox > div > div,
      .stNumberInput input {{
        background: #f3f4f6 !important;
        color: var(--text-main) !important;
        border-radius: var(--radius-lg) !important;
        border: 1px solid #d1d5db !important;
      }}

      /* Quiz options: 라디오 그룹 줄 간격 약간 여유 */
      .stRadio > div {{ gap: .35rem !important; }}

      /* Footer */
      .footer {{
        margin-top: 28px; color: var(--text-dim); font-size: 12px; text-align:center;
      }}
    </style>
    """
    st.markdown(_css, unsafe_allow_html=True)

# Header (Page 1과 동일한 히어로 섹션)
st.markdown("<div class='hero-title'>질문 키워드 랜덤 퀴즈</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>제출된 질문 키워드로 AI가 퀴즈를 생성해 드려요 ✨</div>", unsafe_allow_html=True)
st.markdown("---")


# ------------------------------------
# 📌 2) DB 초기화/유틸(원래 로직 유지)
# ------------------------------------

DB_PATH = Path(__file__).parent.parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = init_db()

def get_unique_keywords():
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT keyword FROM keywords")
    rows = cur.fetchall()
    return [row[0] for row in rows]


# ------------------------------------
# 📌 3) Gemini 퀴즈 생성 (원래 로직 유지)
# ------------------------------------

@st.cache_data(show_spinner="AI가 질문 키워드 기반으로 퀴즈를 생성하는 중...")
def generate_quiz_with_ai(keyword_list_str, num_questions):
    if not GEMINI_AVAILABLE:
        st.error("Google GenAI 라이브러리가 없어 퀴즈를 생성할 수 없습니다.")
        return None

    try:
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
            }}
          ]
        }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )
        return json.loads(response.text)

    except APIError as e:
        st.error(f"Gemini API 오류: {e}")
        st.info("API 키, 요금제 상태, 사용량 제한 등을 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"퀴즈 생성 중 오류가 발생했습니다: {e}")
        return None


# ------------------------------------
# 📌 4) 세션 상태 초기화 (원래 로직 유지)
# ------------------------------------

if "quiz_data" not in st.session_state:
    st.session_state["quiz_data"] = None
if "answers" not in st.session_state:
    st.session_state["answers"] = {}
if "submitted" not in st.session_state:
    st.session_state["submitted"] = False


# ------------------------------------
# 📌 5) 설정 카드 (카테고리 선택 / 문항 수 / 생성 버튼)
# ------------------------------------

# 여기는 컨테이너를 유지하여 설정 카드를 흰색 배경으로 유지합니다.
st.markdown("""
<div class='modern-card'>
  <div class='card-title'>⚙️ 퀴즈 설정</div>
  <div class='helper' style='color:var(--text-dim)'>문항 카테고리와 문항 수를 선택한 뒤, <b>새 퀴즈 생성</b>을 눌러주세요.</div>
</div>
""", unsafe_allow_html=True)

# DB에서 존재하는 카테고리 목록
def get_all_categories():
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM keywords")
    rows = cur.fetchall()
    cats = [r[0] for r in rows if r[0] is not None]
    return sorted(cats)

all_categories = get_all_categories()

# 기존 코드의 시작과 동일 (모든 내용을 이 안에 넣습니다)
# === 문항 카테고리: '생성할 퀴즈 문항 수' 폰트처럼 변경 ===
st.markdown("문항 카테고리", unsafe_allow_html=False) # HTML 클래스와 아이콘을 제거하고 일반 텍스트로 변경

selected_categories = []
if not all_categories:
    st.info("아직 등록된 카테고리가 없습니다. 먼저 키워드를 제출해 주세요.")
else:
    cols = st.columns(3)
    for i, cat in enumerate(all_categories):
        if cols[i % 3].checkbox(cat, value=True, key=f"cat_chk_{i}"):
            selected_categories.append(cat)

# 선택된 카테고리로 키워드 필터링
if selected_categories:
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in selected_categories)
    cur.execute(
        f"SELECT DISTINCT keyword FROM keywords WHERE category IN ({placeholders})",
        tuple(selected_categories)
    )
    kws = [r[0] for r in cur.fetchall()]
    unique_keywords = [k for k in kws if k]
else:
    unique_keywords = get_unique_keywords()

st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

# 문항 수 선택 (위)
num_questions = st.selectbox("생성할 퀴즈 문항 수", options=[1,2,3,4,5], index=2, key="num_q")

# 버튼을 문항 수 바로 아래로
st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
if st.button("✨ 새 퀴즈 생성 ✨", use_container_width=True, type="primary"):
    if not unique_keywords:
        st.info("아직 제출된 키워드가 없어 퀴즈를 생성할 수 없습니다.")
    else:
        st.session_state["quiz_data"] = None
        st.session_state["answers"] = {}
        st.session_state["submitted"] = False
        keyword_list_str = ", ".join(unique_keywords)
        quiz_json = generate_quiz_with_ai(keyword_list_str, num_questions)
        st.session_state["quiz_data"] = quiz_json
        st.rerun()




# ------------------------------------
# 📌 6) 퀴즈 영역 (폼 / 제출 / 채점)
# ------------------------------------

if st.session_state["quiz_data"]:
    quiz_data = st.session_state["quiz_data"]
    
    # 흰색 컨테이너 (modern-card) 시작 태그 제거
    st.markdown("---") # 퀴즈 시작 전에 구분선 추가 (선택 사항)
    
    # 제목 스타일 (card-title)은 그대로 유지하면서, 아래에 수평선을 추가하여 구분
    st.markdown(
        f"<div class='card-title' style='margin-bottom: 0;'>📝 {quiz_data.get('quiz_title','오늘의 영어 질문 키워드 퀴즈')}</div>", 
        unsafe_allow_html=True
    )


    questions = quiz_data.get('questions', [])

    with st.form(key="quiz_form"):
        for q in questions:
            # 문제 텍스트
            question_text = f"**Q{q['q_num']}.** {q['question']}"
            # 보기 텍스트만 추출
            options_text = [option.split('.', 1)[1].strip() if '.' in option else option for option in q['options']]

            # 제출 후 정오 표시 준비
            is_correct = None
            user_answer_num = None
            if st.session_state["submitted"]:
                user_answer_num = st.session_state["answers"].get(f"q_{q['q_num']}")
                if user_answer_num is not None:
                    is_correct = (user_answer_num == q['answer'])

            # 선택 라디오
            selected_option_text = st.radio(
                question_text,
                options=options_text,
                index=None,
                key=f"q_{q['q_num']}_radio",
                disabled=st.session_state["submitted"]
            )

            # 선택 저장
            if selected_option_text:
                selected_index = options_text.index(selected_option_text)
                st.session_state["answers"][f"q_{q['q_num']}"] = selected_index + 1

            # 제출 후 피드백
            if st.session_state["submitted"]:
                user_choice_text = selected_option_text if selected_option_text else "선택 안 함"
                if is_correct:
                    st.success(f"✅ 정답입니다! (선택: {user_choice_text})")
                else:
                    st.error(f"❌ 오답입니다. (선택: {user_choice_text})")
                correct_answer_text = options_text[q['answer'] - 1]
                st.info(f"⭐ 정답: {q['answer']}번 ({correct_answer_text})")

            st.markdown("<div class='soft-divider' style='height:1px;background:linear-gradient(90deg,transparent,#d1d5db,transparent);margin:10px 0 18px;'></div>", unsafe_allow_html=True)

        # 제출 버튼
        submitted = st.form_submit_button("제출하고 채점하기", disabled=st.session_state["submitted"])
        if submitted:
            if len(st.session_state["answers"]) < len(questions):
                st.warning("모든 질문에 답해주세요.")
            else:
                st.session_state["submitted"] = True
                st.rerun()

    # 채점 결과 (폼 아래)
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

    # 흰색 컨테이너 (modern-card) 끝 태그 제거


# ------------------------------------
# 📌 7) 메인으로 이동 (Page 1과 동일한 버튼 스타일 적용)
# ------------------------------------

st.markdown("---")
if st.button("🏠 메인 페이지로 돌아가기", use_container_width=True):
    st.switch_page("Home.py")


# ------------------------------------
# 📌 8) Footer (Page 1과 동일)
# ------------------------------------

st.markdown("""
<div class='footer'>
  © 민영쌤 질문방 ✨
</div>
""", unsafe_allow_html=True)