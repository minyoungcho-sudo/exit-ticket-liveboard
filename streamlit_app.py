# ...existing code...
import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd

# 워드클라우드 라이브러리 시도 임포트 (matplotlib 없이도 표시 가능하도록 to_image 사용)
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

st.set_page_config(page_title="수업 헷갈렸던 영어 키워드", layout="centered")

st.title("Exit Ticket Live Board")
st.write("쓰임을 알고 싶은 영단어나 헷갈리는 문법 개념을 키워드로 입력하세요. 제출된 항목은 모든 사용자가 볼 수 있도록 서버에 저장됩니다.")

# DB 경로
DB_PATH = Path(__file__).parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            ts TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def add_keyword(kw: str):
    ts = datetime.utcnow().isoformat()
    with conn:
        conn.execute("INSERT INTO keywords (keyword, ts) VALUES (?, ?)", (kw, ts))

def get_keywords(limit: int = 500):
    cur = conn.cursor()
    cur.execute("SELECT id, keyword, ts FROM keywords ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return list(reversed(rows))

# 세션 상태 초기화 (입력창 제어용)
if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""

if "msg" not in st.session_state:
    st.session_state["msg"] = ""
if "msg_type" not in st.session_state:
    st.session_state["msg_type"] = None

input_key = "keyword_input"
keyword = st.text_input("단어 또는 문법 개념 입력", key=input_key)

def submit_callback():
    kw = st.session_state.get(input_key, "").strip()
    if kw:
        add_keyword(kw)
        # 입력창 비우기 (버튼 콜백 내에서 안전하게 변경)
        st.session_state[input_key] = ""
        st.session_state["msg"] = f"제출됨: {kw}"
        st.session_state["msg_type"] = "success"
    else:
        st.session_state["msg"] = "먼저 입력해주세요."
        st.session_state["msg_type"] = "warning"

st.button("제출", on_click=submit_callback)

# 콜백에서 설정한 메세지 표시
if st.session_state.get("msg"):
    if st.session_state.get("msg_type") == "success":
        st.success(st.session_state["msg"])
    elif st.session_state.get("msg_type") == "warning":
        st.warning(st.session_state["msg"])
    else:
        st.info(st.session_state["msg"])
    st.session_state["msg"] = ""
    st.session_state["msg_type"] = None

st.markdown("---")
st.subheader("제출된 키워드 목록 (최신 항목 맨 아래)")

items = get_keywords()
if items:
    for i, (row_id, kw, ts) in enumerate(items, start=1):
        st.write(f"{i}. {kw}  —  {ts} UTC")
else:
    st.info("아직 제출된 항목이 없습니다.")

# -----------------------------
# 빈도 집계 및 시각화 추가
# -----------------------------
st.markdown("---")
st.subheader("키워드 빈도 분석")

# 키워드 문자열만 추출
keywords = [kw for (_id, kw, _ts) in items]

if keywords:
    # 빈도 집계 (대소문자 구분을 원치 않으면 .lower() 사용)
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    # 막대그래프 (빈도순)
    st.markdown("#### 빈도순 막대그래프")
    bar_df = df.set_index("keyword")
    st.bar_chart(bar_df["count"])

    # 워드클라우드
    st.markdown("#### 워드클라우드")
    if WORDCLOUD_AVAILABLE:
        freq_dict = dict(freq)
        wc = WordCloud(width=800, height=400, background_color="white")
        wc.generate_from_frequencies(freq_dict)
        # matplotlib 없이도 PIL 이미지로 변환하여 표시
        img = wc.to_image()
        st.image(img, use_column_width=True)
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요.\n터미널에서: pip3 install wordcloud pillow")
else:
    st.info("집계할 키워드가 없습니다. 먼저 키워드를 제출해 주세요.")
# ...existing code...