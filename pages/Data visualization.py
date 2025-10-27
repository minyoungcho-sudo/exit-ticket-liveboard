# modern_ui_page2.py — Streamlit page 2 (Live Board) with the same bright Modern UI as Page 1
# 기능 동일, UI만 1페이지와 일치시킴

import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd
import altair as alt

# ------------------------------------
# 0) PAGE CONFIG
# ------------------------------------
st.set_page_config(
    page_title="민영쌤 질문방 | Live Board",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ------------------------------------
# 1) FONT & THEME (Page1와 동일 스타일)
# ------------------------------------
# 2페이지 파일이 pages/ 폴더 안에 있으므로 상위 폴더의 fonts 사용
FONT_DIR = Path(__file__).parent.parent / "fonts"

def _find_font_file():
    if not FONT_DIR.exists():
        return None
    cand = list(FONT_DIR.glob("**/*NanumGothic*.ttf"))
    if not cand:
        cand = list(FONT_DIR.glob("**/*.ttf"))
    return cand[0] if cand else None

_FONT_FILE = _find_font_file()
FONT_PATH = str(_FONT_FILE.resolve()) if _FONT_FILE else None

# 공통 CSS (Page1와 동일 톤)
_css = f"""
<style>
  :root {{
    --bg-color: #f9fafb; /* light gray background */
    --card-bg: #ffffff;
    --card-bd: #e5e7eb;
    --text-main: #1f2937;
    --text-dim: #6b7280;
    --brand-1: #6366f1; /* indigo-500 */
    --brand-2: #06b6d4; /* cyan-500 */
    --radius-xxl: 18px;
    --radius-lg: 12px;
  }}

  {'@font-face { font-family: "NanumGothic"; src: url("file://' + FONT_PATH + '") format("truetype"); }' if FONT_PATH else ''}

  html, body, .stApp {{
    font-family: {'"NanumGothic", ' if FONT_PATH else ''}sans-serif !important;
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
  .soft-divider {{ height:1px; background: linear-gradient(90deg, transparent, #d1d5db, transparent); margin: 10px 0 18px 0; }}

  /* Form labels & inputs */
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

  /* Chips */
  .chip {{
    display:inline-flex; align-items:center; gap:.35rem; padding:.25rem .6rem; 
    border-radius: 999px; font-size: 12px; border:1px solid #bae6fd;
    background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(14,165,233,0.05));
    color:#0369a1;
  }}

  /* Wordcloud top buttons (equal width) */
  div[data-testid="column"] .stButton > button {{
    width: 100% !important; display: inline-flex; align-items: center; justify-content: center;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 6px 10px; min-height: 40px;
    box-sizing: border-box; font-size: 14px; border-radius: 10px;
  }}
  div[data-testid="column"] {{ flex: 1 1 0%; min-width: 0; }}
  div[data-testid="column"] .stButton > button > span {{ display: inline-block; max-width: 100%; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

  /* Footer */
  .footer {{
    margin-top: 28px; color: var(--text-dim); font-size: 12px; text-align:center;
  }}
</style>
"""
st.markdown(_css, unsafe_allow_html=True)

# Altair 한글 폰트 테마
def _nanum_theme():
    return {
        "config": {
            "title": {"font": "NanumGothic" if FONT_PATH else None},
            "axis": {"labelFont": "NanumGothic" if FONT_PATH else None, "titleFont": "NanumGothic" if FONT_PATH else None},
            "legend": {"labelFont": "NanumGothic" if FONT_PATH else None, "titleFont": "NanumGothic" if FONT_PATH else None},
            "header": {"labelFont": "NanumGothic" if FONT_PATH else None}
        }
    }
try:
    alt.themes.register("nanum", _nanum_theme)
    alt.themes.enable("nanum")
except Exception:
    pass

# 워드클라우드 라이브러리
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

# ------------------------------------
# 2) HEADER
# ------------------------------------
st.markdown("<div class='hero-title'>실시간 질문 분석 보드</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>카테고리 현황, 키워드 워드클라우드 & 랭킹을 한눈에 확인하세요.</div>", unsafe_allow_html=True)
st.markdown("---")

# ------------------------------------
# 3) DB 연결 (2페이지 기준: 프로젝트 루트의 keywords.db)
# ------------------------------------
DB_PATH = Path(__file__).parent.parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = init_db()

# ------------------------------------
# 4) DATA ACCESS FUNCTIONS (기능 동일)
# ------------------------------------
def get_keywords(limit: int = 500, category: str | None = None):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("""
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts 
            FROM keywords 
            WHERE category = ? 
            ORDER BY id DESC 
            LIMIT ?""", (category, limit))
    else:
        cur.execute("""
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts 
            FROM keywords 
            ORDER BY id DESC 
            LIMIT ?""", (limit,))
    rows = cur.fetchall()
    return list(reversed(rows))

def get_explanations_by_keyword(keyword: str, category: str | None = None, limit: int = 200):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("""
            SELECT student_name, class_num, student_no, note, ts
            FROM keywords 
            WHERE keyword = ? AND category = ? 
            ORDER BY id DESC 
            LIMIT ?""", (keyword, category, limit))
    else:
        cur.execute("""
            SELECT student_name, class_num, student_no, note, ts
            FROM keywords 
            WHERE keyword = ? 
            ORDER BY id DESC 
            LIMIT ?""", (keyword, limit))
    return cur.fetchall()

def get_category_counts():
    cur = conn.cursor()
    cur.execute("SELECT category, COUNT(*) FROM keywords GROUP BY category")
    rows = cur.fetchall()
    return rows

# ------------------------------------
# 5) CONTENT - CARDS & CHARTS (UI만 Modern)
# ------------------------------------

# 5-1) 카테고리 현황 (Pie + Bar)
st.markdown("<div class='modern-card'><div class='card-title'>🏷️ 카테고리별 질문 현황</div>질문이 많은 카테고리를 확인하세요.", unsafe_allow_html=True)

counts = get_category_counts()
if counts:
    df_counts = pd.DataFrame(counts, columns=["category", "count"])
    df_counts["percent"] = (df_counts["count"] / df_counts["count"].sum() * 100).round(1)

    col1, col2 = st.columns([1,1])
    color_scale = alt.Scale(domain=df_counts["category"].tolist(), scheme="accent")

    with col1:
        pie = (
            alt.Chart(df_counts)
            .mark_arc(innerRadius=60)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("category:N", scale=color_scale, legend=alt.Legend(title="카테고리")),
                tooltip=[
                    alt.Tooltip("category:N", title="카테고리"),
                    alt.Tooltip("count:Q", title="건수"),
                    alt.Tooltip("percent:Q", title="비율(%)")
                ],
            )
            .properties(height=360)
        )
        st.altair_chart(pie, use_container_width=True)

    with col2:
        bar = (
            alt.Chart(df_counts)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("category:N", sort="-y", title=None),
                y=alt.Y("count:Q", title="제출 수"),
                color=alt.Color("category:N", scale=color_scale, legend=None),
                tooltip=[
                    alt.Tooltip("category:N", title="카테고리"),
                    alt.Tooltip("count:Q", title="건수"),
                ],
            )
            .properties(height=360)
        )
        labels = (
            alt.Chart(df_counts)
            .mark_text(dy=-8)
            .encode(
                x=alt.X("category:N", sort="-y"),
                y=alt.Y("count:Q"),
                text=alt.Text("count:Q"),
            )
        )
        st.altair_chart(bar + labels, use_container_width=True)
else:
    st.info("아직 제출된 항목이 없어 카테고리 통계를 표시할 수 없습니다.")
st.markdown("</div>", unsafe_allow_html=True)  # end card

# 5-2) 보기용 카테고리 선택 + 제출 목록 (Inventory 스타일 표)

if "view_category" not in st.session_state:
    st.session_state["view_category"] = "All"
view_category = st.selectbox(
    "보기용 카테고리",
    ["All", "Vocabulary", "Grammar", "Reading", "Else"],
    index=["All", "Vocabulary", "Grammar", "Reading", "Else"].index(st.session_state["view_category"]),
    key="view_category"
)

st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

with st.expander("📋 제출된 키워드 목록 보기", expanded=False):
    items = get_keywords(category=view_category)
    if items:
        table_rows = []
        for r in items:
            _id, kw, cat, grade_db, class_db, no_db, name_db, note_db, ts = r
            table_rows.append({
                "카테고리": cat,
                "키워드": kw,
                "부연설명": note_db,
            })
        df_table = pd.DataFrame(table_rows)
        df_table.index = range(1, len(df_table) + 1)
        df_table.index.name = "No"
        st.dataframe(df_table[["카테고리", "키워드", "부연설명"]], use_container_width=True)
    else:
        st.info("해당 카테고리에 제출된 항목이 없습니다.")
st.markdown("</div>", unsafe_allow_html=True)  # end card

# 5-3) 워드클라우드 & 상위 키워드 버튼 & 설명 보기
st.markdown("<div class='modern-card'><div class='card-title'>☁️ 워드클라우드 & 키워드 탐색</div>자주 등장하는 질문 키워드를 빠르게 파악하세요. <span class='chip'>클릭 가능한 TOP 키워드</span>", unsafe_allow_html=True)


# 키워드만 추출
items = get_keywords(category=view_category)
keywords = [kw for (_id, kw, _cat, _grade, _class, _no, _name, _note, _ts) in items] if items else []

if keywords:
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    # 워드클라우드
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    if WORDCLOUD_AVAILABLE:
        freq_dict = dict(freq)
        wc = WordCloud(
            width=700,
            height=420,
            background_color="white",
            colormap="plasma",
            prefer_horizontal=0.9,
            contour_width=0,
            font_path=FONT_PATH if FONT_PATH else None,
            random_state=42,
        ).generate_from_frequencies(freq_dict)
        img = wc.to_image()
        st.image(img, use_container_width=True)

        st.info("💬 상위 키워드 버튼을 클릭하면 해당 키워드의 부연 설명 목록을 볼 수 있어요.")
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        # 상위 4개 버튼
        top_buttons = df.head(4)["keyword"].tolist()
        if "selected_word" not in st.session_state:
            st.session_state["selected_word"] = ""
        if len(top_buttons) > 0:
            btn_cols = st.columns(len(top_buttons))
            for i, w in enumerate(top_buttons):
                with btn_cols[i]:
                    if st.button(w, key=f"kwbtn_{w}", type="secondary", use_container_width=True):
                        st.session_state["selected_word"] = w
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요. (예: pip install wordcloud pillow)")

    # 선택 단어 부연 설명
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    if st.session_state.get("selected_word"):
        selected_word = st.session_state["selected_word"]
        view_cat = st.session_state.get("view_category", None)
        explanations = get_explanations_by_keyword(selected_word, category=view_cat)
        st.markdown(f"**선택한 키워드:** `{selected_word}`")
        if explanations:
            notes = [ex[3] if ex[3] else "(부연 설명 없음)" for ex in explanations]
            df_notes = pd.DataFrame({"부연설명": notes})
            df_notes.index = range(1, len(df_notes) + 1)
            df_notes.index.name = "No"
            st.dataframe(df_notes, use_container_width=True)
        else:
            st.info("해당 단어에 대한 부연 설명이 없습니다.")
else:
    st.info("집계할 키워드가 없습니다. 먼저 키워드를 제출해 주세요.")
st.markdown("</div>", unsafe_allow_html=True)  # end card

# 5-4) 키워드 랭킹 (막대그래프)
st.markdown("<div class='modern-card'><div class='card-title'>📈 질문 키워드 RANKING</div>학생들이 헷갈리는 키워드 순위를 확인하세요.", unsafe_allow_html=True)

if keywords:
    df_chart = df.copy()
    order = df_chart["keyword"].tolist()
    color_scheme = "accent"
    kw_color_scale = alt.Scale(domain=order, scheme=color_scheme)

    bar = (
        alt.Chart(df_chart)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("keyword:N", sort=order, title="키워드"),
            y=alt.Y("count:Q", title="빈도", axis=alt.Axis(format="d")),
            color=alt.Color("keyword:N", scale=kw_color_scale, legend=None),
            tooltip=[
                alt.Tooltip("keyword:N", title="키워드"),
                alt.Tooltip("count:Q", title="건수", format=".0f"),
            ],
        )
        .properties(height=360)
    )

    labels = (
        alt.Chart(df_chart)
        .mark_text(dy=-8)
        .encode(
            x=alt.X("keyword:N", sort=order),
            y=alt.Y("count:Q"),
            text=alt.Text("count:Q", format=".0f"),
        )
    )
    st.altair_chart(bar + labels, use_container_width=True)
else:
    st.info("표시할 키워드 랭킹이 없습니다.")
st.markdown("</div>", unsafe_allow_html=True)  # end card

# ------------------------------------
# 6) FOOTER
# ------------------------------------
st.markdown("""
<div class='footer'>
  © 민영쌤 질문방 ✨
</div>
""", unsafe_allow_html=True)
