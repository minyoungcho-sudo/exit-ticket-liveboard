# modern_ui_page1.py — Streamlit page with refined UI (all original features preserved)

import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
import altair as alt

st.set_page_config(
    page_title="민영쌤 질문방 | Bright Modern UI",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ----- Korean font setup -----
FONT_DIR = Path(__file__).parent / "fonts"

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
        --brand-1: #6366f1;
        --brand-2: #06b6d4;
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
        padding-bottom: 3rem;
        max-width: 900px;
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

      .chip {{
        display:inline-flex; align-items:center; gap:.35rem; padding:.25rem .6rem; 
        border-radius: 999px; font-size: 12px; border:1px solid #bae6fd;
        background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(14,165,233,0.05));
        color:#0369a1;
      }}

      .soft-divider {{ height:1px; background: linear-gradient(90deg, transparent, #d1d5db, transparent); margin: 10px 0 18px 0; }}

      div[data-testid="column"] .stButton > button {{
        width: 100% !important; display: inline-flex; align-items: center; justify-content: center;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 6px 10px; min-height: 40px;
        box-sizing: border-box; font-size: 14px; border-radius: 10px;
      }}
      div[data-testid="column"] {{ flex: 1 1 0%; min-width: 0; }}
      div[data-testid="column"] .stButton > button > span {{ display: inline-block; max-width: 100%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

      .footer {{
        margin-top: 28px; color: var(--text-dim); font-size: 12px; text-align:center;
      }}
    </style>
    """
    st.markdown(_css, unsafe_allow_html=True)

# Header
st.markdown("<div class='hero-title'>민영쌤 질문방</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>24시간 열려있는 학습 지원 공간. 질문을 남겨주세요.</div>", unsafe_allow_html=True)
st.markdown("---")

# DB setup
DB_PATH = Path(__file__).parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            grade TEXT,
            class_num INTEGER,
            student_no INTEGER,
            student_name TEXT,
            note TEXT,
            ts TEXT,
            week INTEGER
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# ✅ FIX: DB에 한 줄 추가하는 함수 정의
def add_keyword(keyword, category, grade, class_num, student_no, student_name, note, week):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute(
            """
            INSERT INTO keywords (keyword, category, grade, class_num, student_no, student_name, note, ts, week)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (keyword, category, grade, class_num, student_no, student_name, note, ts, week),
        )

# Student Info Card
st.markdown("<div class='modern-card'><div class='card-title'>🧑‍🎓 학생 정보</div>질문자의 이름은 공개되지 않습니다. 마음 편히 질문하세요 😊", unsafe_allow_html=True)
col_g, col_c, col_n, col_name = st.columns([1,1,1,3])

# ✅ FIX: submit_callback에서 읽는 key들과 일치하도록 key 지정
with col_g:
    st.selectbox("학년", ["2학년"], key="grade_select")
with col_c:
    st.selectbox("반", [f"{i}반" for i in range(1,13)], key="class_select")
with col_n:
    st.selectbox("번호", [f"{i}번" for i in range(1,33)], key="student_no_select")
with col_name:
    st.text_input("이름", placeholder="이름 입력", key="student_name")

# -----------------------------
# CATEGORY & WEEK CARD
# -----------------------------
st.markdown("---")
st.markdown("""
<div class='modern-card'>
  <div class='card-title'>🏷️ 카테고리 & 수업 주차</div>
  <div class='helper'>먼저 카테고리를 선택하고, 해당 수업 주차를 지정하세요.</div>
</div>
""", unsafe_allow_html=True)

with st.container():
    col_cat, col_week = st.columns([2,1])
    with col_cat:
        st.selectbox("입력할 카테고리 선택", ["Vocabulary", "Grammar", "Reading", "Else"], key="category_select")
    with col_week:
        st.selectbox(
            "수업 주차",
            list(range(1, 18)),
            index=(st.session_state.get("week_select", 1) - 1),
            format_func=lambda x: f"{x}주차",
            key="week_select"
        )

# -----------------------------
# QUESTION INPUT CARD
# -----------------------------
st.markdown("---")

st.markdown("""
<div class='modern-card'>
  <div class='card-title'>✍️ 질문 입력</div>
  <div class='helper'>키워드와 부연 설명을 간결하게 적어주세요. <span class='chip'>예: 현재완료 / 시제 비교</span></div>
</div>
""", unsafe_allow_html=True)

input_key = "keyword_input"
if st.session_state.get("category_select") == "Reading":
    st.markdown("질문할 문장 번호를 선택하세요.")
    c1, c2 = st.columns([1,1])
    with c1:
        st.selectbox("지문 번호", list(range(1,21)), index=st.session_state.get("reading_passage",1)-1, key="reading_passage", format_func=lambda x: f"{x}번 지문")
    with c2:
        st.selectbox("문장 번호", list(range(1,21)), index=st.session_state.get("reading_sentence",1)-1, key="reading_sentence", format_func=lambda x: f"{x}번 문장")
    st.session_state[input_key] = ""
else:
    st.text_input("질문 키워드 입력", key=input_key, placeholder="예: present perfect, 가정법, collocation …")

st.text_area(
    "부연 설명 (문장으로 입력)",
    key="note_input",
    height=100,
    placeholder="예: 단어가 사용된 예문을 알고 싶어요 / 현재완료와 과거완료의 차이점이 헷갈려요",
)

# -----------------------------
# SUBMIT AREA
# -----------------------------
def submit_callback():
    cat = st.session_state.get("category_select", "Else")
    if cat == "Reading":
        passage = st.session_state.get("reading_passage", 1)
        sentence = st.session_state.get("reading_sentence", 1)
        kw = f"지문{passage}번_문장{sentence}번"
    else:
        kw = st.session_state.get(input_key, "").strip()

    note_text = st.session_state.get("note_input", "").strip()
    grade_val = st.session_state.get("grade_select", "2학년")
    class_val = st.session_state.get("class_select", "1반")

    try:
        class_num = int(''.join(filter(str.isdigit, class_val)))
    except Exception:
        class_num = 1
    try:
        student_no = int(''.join(filter(str.isdigit, st.session_state.get("student_no_select", "1번"))))
    except Exception:
        student_no = 1

    student_name_val = st.session_state.get("student_name", "").strip()
    week_val = st.session_state.get("week_select", None)

    if kw:
        add_keyword(kw, cat, grade_val, class_num, student_no, student_name_val, note_text, week_val)
        st.session_state[input_key] = ""
        st.session_state["note_input"] = ""
        st.session_state["msg"] = f"제출됨: [{cat}] {kw}"
        st.session_state["msg_type"] = "success"
    else:
        st.session_state["msg"] = "먼저 입력해주세요."
        st.session_state["msg_type"] = "warning"

c1, c2 = st.columns([2,1])
with c1:
    st.button("제출하기", on_click=submit_callback, use_container_width=True, type="primary")
with c2:
    if st.button("📊 실시간 분석 보러가기", use_container_width=True):
        # 페이지 파일명은 프로젝트 구조에 맞게 조정하세요.
        st.switch_page("pages/Data visualization.py")

# Feedback toast
if st.session_state.get("msg"):
    if st.session_state.get("msg_type") == "success":
        st.success(st.session_state["msg"])
    elif st.session_state.get("msg_type") == "warning":
        st.warning(st.session_state["msg"])
    else:
        st.info(st.session_state["msg"])
    st.session_state["msg"] = ""
    st.session_state["msg_type"] = None

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("""
<div class='footer'>
  © 민영쌤 질문방 ✨
</div>
""", unsafe_allow_html=True)
