import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd
import altair as alt

# ------------------------------------
# 📌 1. 필수 설정 및 함수 정의 (기존 페이지와 동일)
# ------------------------------------

# --- 한글 폰트 설정 (프로젝트 폴더의 fonts/NanumGothic 사용) ---
# FONT_DIR 경로 설정은 페이지 파일 위치에 맞게 조정이 필요할 수 있습니다.
# 현재 페이지(live_board.py)는 pages 폴더 안에 있으므로, Path(__file__).parent.parent
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
    # 페이지 전역에 폰트 적용 (CSS 삽입)
    _css = f"""
    <style>
    @font-face {{
        font-family: 'NanumGothic';
        src: url('file://{FONT_PATH}') format('truetype');
        font-weight: normal;
        font-style: normal;
    }}
    /* 텍스트용 요소만 NanumGothic 적용 (아이콘 폰트는 덮어쓰지 않음) */
    html, body, .stApp, .block-container, h1, h2, h3, h4, h5, p, label, input, textarea {{
        font-family: 'NanumGothic', sans-serif !important;
    }}
    /* Material Icons 예외 처리 */
    .material-icons, .material-icons-outlined, .material-icons-round, i.material-icons {{
        font-family: 'Material Icons' !important;
        speak: none;
        font-style: normal;
        font-weight: normal;
        font-variant: normal;
        text-transform: none;
        line-height: 1;
        letter-spacing: normal;
        word-wrap: normal;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
    }}

    /* 워드클라우드 상위 단어 버튼 통일 스타일 */
    /* 컬럼 내부 버튼을 컬럼 폭에 맞춰 동일 너비로 표시 */
    div[data-testid="column"] .stButton > button {{
        width: 100% !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 6px 10px;
        min-height: 40px;
        box-sizing: border-box;
        font-size: 14px;
        border-radius: 6px;
    }}
    /* 컬럼 부모 요소가 축소될 때도 버튼이 줄바꿈 되지 않게 강제 */
    div[data-testid="column"] {{
        flex: 1 1 0%;
        min-width: 0;
    }}
    /* 버튼 텍스트 중앙 정렬 및 말줄임 처리 */
    div[data-testid="column"] .stButton > button > span {{
        display: inline-block;
        max-width: 100%;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    </style>
    """
    import streamlit as _st
    _st.markdown(_css, unsafe_allow_html=True)
    
    # Altair 테마로 한글 폰트 지정
    def _nanum_theme():
        return {
            "config": {
                "title": {"font": "NanumGothic"},
                "axis": {"labelFont": "NanumGothic", "titleFont": "NanumGothic"},
                "legend": {"labelFont": "NanumGothic", "titleFont": "NanumGothic"},
                "header": {"labelFont": "NanumGothic"}
            }
        }
    try:
        alt.themes.register("nanum", _nanum_theme)
        alt.themes.enable("nanum")
    except Exception:
        pass
else:
    FONT_PATH = None
# --- end font setup ---

# 워드클라우드 라이브러리 시도 임포트
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

# DB 경로 설정 (pages/live_board.py 기준)
DB_PATH = Path(__file__).parent.parent / "keywords.db"

def init_db():
    # 이 페이지에서는 데이터를 입력하지 않으므로, 테이블 생성/컬럼 추가 로직은 생략하거나 그대로 두어도 됩니다.
    # 안전하게 그대로 유지하는 것이 좋습니다.
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    
    # 이 페이지에서는 SELECT만 사용하므로, 테이블 생성/컬럼 추가 로직은 삭제해도 되지만
    # 안정성을 위해 최소한의 구조는 유지하는 것이 좋습니다.
    # 여기서는 SELECT에 필요한 함수만 남기고, 테이블 생성 로직은 생략합니다.
    return conn

conn = init_db()

# 데이터 조회 함수 (기존 코드와 동일)
def get_keywords(limit: int = 500, category: str | None = None):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts FROM keywords WHERE category = ? ORDER BY id DESC LIMIT ?", (category, limit))
    else:
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts FROM keywords ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return list(reversed(rows))

# 키워드로 부연설명 조회 함수 (기존 코드와 동일)
def get_explanations_by_keyword(keyword: str, category: str | None = None, limit: int = 200):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("""SELECT student_name, class_num, student_no, note, ts
                       FROM keywords WHERE keyword = ? AND category = ? ORDER BY id DESC LIMIT ?""",
                    (keyword, category, limit))
    else:
        cur.execute("""SELECT student_name, class_num, student_no, note, ts
                       FROM keywords WHERE keyword = ? ORDER BY id DESC LIMIT ?""",
                    (keyword, limit))
    return cur.fetchall()

def get_category_counts():
    cur = conn.cursor()
    cur.execute("SELECT category, COUNT(*) FROM keywords GROUP BY category")
    rows = cur.fetchall()
    return rows

# ------------------------------------
# 📌 2. 페이지 레이아웃 및 시각화 코드
# ------------------------------------

st.set_page_config(page_title="Exit Ticket Live Board", layout="centered")

st.markdown("<h1 style='text-align:center; margin-bottom:0.25rem;'>📊 실시간 질문 분석 보드 📊</h1>", unsafe_allow_html=True)
st.markdown("---")

# 보기용 카테고리 선택 전에 전체 카테고리별 제출 수를 파이 차트로 표시
counts = get_category_counts()
if counts:
    df_counts = pd.DataFrame(counts, columns=["category", "count"])
    # 백분율 칼럼 추가 (툴팁에 사용)
    df_counts["percent"] = (df_counts["count"] / df_counts["count"].sum() * 100).round(1)

    # 통합 제목 (파이 + 바 한 번에)
    st.markdown("### ▪️ 카테고리별 질문 현황")
    # 추가: 제목 아래 여백
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    # 일관된 색상 스케일 사용
    color_scale = alt.Scale(domain=df_counts["category"].tolist(), scheme="accent")

    with col1:
        pie = (
            alt.Chart(df_counts)
            .mark_arc(innerRadius=60)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("category:N", scale=color_scale, legend=alt.Legend(title="카테고리")),
                tooltip=[alt.Tooltip("category:N", title="카테고리"),
                         alt.Tooltip("count:Q", title="건수"),
                         alt.Tooltip("percent:Q", title="비율(%)")]
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
                tooltip=[alt.Tooltip("category:N", title="카테고리"),
                         alt.Tooltip("count:Q", title="건수")]
            )
            .properties(height=360)
        )
        # 막대 위에 숫자 레이블 추가
        labels = alt.Chart(df_counts).mark_text(dy=-8, color="black").encode(
            x=alt.X("category:N", sort="-y"),
            y=alt.Y("count:Q"),
            text=alt.Text("count:Q")
        )
        st.altair_chart(bar + labels, use_container_width=True)
else:
    st.info("아직 제출된 항목이 없어 카테고리 통계를 표시할 수 없습니다.")


# 보기용(필터) 카테고리 선택 — 결과 파트 시작
# 첫 페이지에서 설정한 view_category의 기본값을 사용합니다.
if "view_category" not in st.session_state:
    st.session_state["view_category"] = "All"
view_category = st.selectbox("보기용 카테고리 선택", ["All", "Vocabulary", "Grammar", "Reading", "Else"], index=["All", "Vocabulary", "Grammar", "Reading", "Else"].index(st.session_state["view_category"]), key="view_category")

# 제출된 키워드 목록을 접힘(버튼) 방식으로 보여주기 — Inventory tracker 스타일 표
# ...existing code...
with st.expander("제출된 키워드 목록 보기", expanded=False):
    items = get_keywords(category=view_category)
    if items:
        table_rows = []
        for r in items:
            # r 구조: (id, keyword, category, grade, class_num, student_no, student_name, note, ts)
            _id, kw, cat, grade_db, class_db, no_db, name_db, note_db, ts = r
            table_rows.append({
                "카테고리": cat,
                "키워드": kw,
                "부연설명": note_db,
                # "제출시간": ts  # 표시에서 제외됨
            })
        df_table = pd.DataFrame(table_rows)
        # 인덱스를 1부터 시작하도록 설정
        df_table.index = range(1, len(df_table) + 1)
        df_table.index.name = "No"
        cols_order = ["카테고리", "키워드", "부연설명"]  # 제출시간 제거
        st.dataframe(df_table[cols_order], use_container_width=True)
    else:
        st.info("해당 카테고리에 제출된 항목이 없습니다.")
# ...existing code...

# -----------------------------
# 빈도 집계 및 시각화 추가 (워드클라우드 먼저, 그 다음 빈도)
# -----------------------------
st.markdown("---")
st.subheader(f"▪️ 자주 언급한 질문 키워드")

# 키워드 문자열만 추출 (필터 적용된 items 사용)
keywords = [kw for (_id, kw, _cat, _grade, _class, _no, _name, _note, _ts) in items]

if keywords:
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    
    # 1) 워드클라우드 표시 (Top 키워드 제거, 기본형)
    st.markdown("#### ")
    if WORDCLOUD_AVAILABLE:
        freq_dict = dict(freq)

        # 기본 직사각형 워드클라우드
        wc = WordCloud(
            width=700,
            height=420,
            background_color="white",
            colormap="plasma",
            prefer_horizontal=0.9,
            contour_width=0,
            font_path=FONT_PATH if ('FONT_PATH' in globals() and FONT_PATH) else None,
            random_state=42
        ).generate_from_frequencies(freq_dict)

        img = wc.to_image()

        # 제목 및 워드클라우드 표시
        st.image(img, use_container_width=True)

        st.markdown(
            """
            <div style='height:8px;'></div>
            """,
            unsafe_allow_html=True
        )
        st.info('💬 키워드 버튼을 클릭하면 해당 키워드의 부연 설명을 볼 수 있어요.')
        st.markdown(
            """
            <div style='height:12px;'></div>
            """,
            unsafe_allow_html=True
        )

        # 상위 4개 키워드 버튼 (워드클라우드 빈도 기반)
        # 키워드가 4개 미만일 수 있으므로, 실제 개수에 맞게 컬럼을 준비합니다.
        top_buttons = df.head(4)["keyword"].tolist()
        num_buttons = len(top_buttons)
        
        if "selected_word" not in st.session_state:
            st.session_state["selected_word"] = ""
        
        # 버튼이 1개라도 있을 때만 컬럼을 생성합니다.
        if num_buttons > 0:
            btn_cols = st.columns(num_buttons) # 👈 키워드 개수(최대 4개)만큼 컬럼 생성
        
            for i in range(num_buttons):
                w = top_buttons[i]
                with btn_cols[i]: # 👈 각 컬럼에 버튼을 배치
                    # use_container_width=True를 제거하고 대신 CSS를 통해 100% 너비를 사용하도록 설정합니다.
                    # (이미 상단 CSS에 설정되어 있으므로 별도 인수는 필요 없으나, 명시적으로 추가하는 것도 좋습니다.)
                    # 단, Streamlit의 CSS가 적용되지 않을 경우를 대비해 인수는 제거한 상태로 둡니다.
                    if st.button(
                        w, 
                        key=f"kwbtn_{w}", 
                        type="secondary", # 파란색(primary) 대신 회색(secondary) 버튼 사용 권장
                        use_container_width=True # 👈 이 인수를 추가하여 버튼이 컬럼 폭을 꽉 채우도록 합니다.
                    ):
                        st.session_state["selected_word"] = w
                        # 부연 설명을 선택하면 해당 섹션이 즉시 업데이트 되도록 합니다.
# -------------------------------------------------------------

        # 선택 단어의 부연 설명 표시
        if st.session_state.get("selected_word"):
            selected_word = st.session_state["selected_word"]
            # view_category 값은 st.session_state["view_category"]를 통해 연동됩니다.
            view_cat = st.session_state.get("view_category", None) if "view_category" in st.session_state else None
            explanations = get_explanations_by_keyword(selected_word, category=view_cat)
            if explanations:
                notes = [ex[3] if ex[3] else "(부연 설명 없음)" for ex in explanations]
                df_notes = pd.DataFrame({"부연설명": notes})
                df_notes.index = range(1, len(df_notes) + 1)
                df_notes.index.name = "No"
                st.dataframe(df_notes, use_container_width=True)
            else:
                st.info("해당 단어에 대한 부연 설명이 없습니다.")
        # 워드클라우드 라이브러리가 없는 경우
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요.\n터미널에서: pip3 install wordcloud pillow")

    
    st.markdown("---")

    # 2) 빈도순 막대그래프 
    st.markdown("#### ▪️ 질문 키워드 RANKING")
# 추가: 제목 아래 여백
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    df_chart = df.copy()
    order = df_chart["keyword"].tolist()

    color_scheme = "accent" if len(order) <= 20 else "accent"
    kw_color_scale = alt.Scale(domain=order, scheme=color_scheme)

    bar = (
        alt.Chart(df_chart)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("keyword:N", sort=order, title="키워드"),
            y=alt.Y("count:Q", title="빈도", axis=alt.Axis(format="d")),
            color=alt.Color("keyword:N", scale=kw_color_scale, legend=None),
            tooltip=[alt.Tooltip("keyword:N", title="키워드"),
                     alt.Tooltip("count:Q", title="건수", format=".0f")]
        )
        .properties(height=360)
    )

    labels = (
        alt.Chart(df_chart)
        .mark_text(dy=-8, color="black", fontSize=12)
        .encode(
            x=alt.X("keyword:N", sort=order),
            y=alt.Y("count:Q"),
            text=alt.Text("count:Q", format=".0f")
        )
    )

    st.altair_chart(bar + labels, use_container_width=True)

else:
    st.info("집계할 키워드가 없습니다. 먼저 키워드를 제출해 주세요.")

# -----------------------------
