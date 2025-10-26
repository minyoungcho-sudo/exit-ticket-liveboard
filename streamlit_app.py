# ...existing code...
import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd
import altair as alt

# --- 한글 폰트 설정 (프로젝트 폴더의 fonts/NanumGothic 사용) ---
FONT_DIR = Path(__file__).parent / "fonts"

def _find_font_file():
    if not FONT_DIR.exists():
        return None
    # 우선 NanumGothic 이름을 포함한 ttf 검색, 없으면 첫 ttf 사용
    cand = list(FONT_DIR.glob("**/*NanumGothic*.ttf"))
    if not cand:
        cand = list(FONT_DIR.glob("**/*.ttf"))
    return cand[0] if cand else None

# ...existing code...
# ...existing code...
# ...existing code...
_FONT_FILE = _find_font_file()
if _FONT_FILE:
    FONT_PATH = str(_FONT_FILE.resolve())
    # 페이지 전역에 폰트 적용 (CSS 삽입) — 단, 아이콘용 폰트는 덮어쓰지 않도록 예외 처리
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
# ...existing code...
    

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
        # Altair 버전/등록 문제 시 무시
        pass
else:
    FONT_PATH = None
# --- end font setup ---

# 워드클라우드 라이브러리 시도 임포트 (matplotlib 없이도 표시 가능하도록 to_image 사용)
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

st.set_page_config(page_title="민영쌤의 질문방", layout="centered")

# ...existing code...
# 중앙 정렬된 제목으로 변경
st.markdown("<h1 style='text-align:center; margin-bottom:0.25rem;'>💡 민영쌤의 질문방 💡</h1>", unsafe_allow_html=True)
# ...existing code...

# DB 경로
DB_PATH = Path(__file__).parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")

    # 테이블 생성 (week는 없어도 됨 — 아래에서 조건부로 추가)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Else',
            grade TEXT NOT NULL DEFAULT '2학년',
            class_num INTEGER NOT NULL DEFAULT 1,
            student_no INTEGER NOT NULL DEFAULT 1,
            student_name TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            ts TEXT NOT NULL
        )
    """)
    conn.commit()

    # ✅ 여기부터 추가: 컬럼 존재 여부 점검 후 없으면 추가
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(keywords)")
    cols = [r[1] for r in cur.fetchall()]

    if "grade" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN grade TEXT DEFAULT '2학년'")
    if "class_num" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN class_num INTEGER DEFAULT 1")
    if "student_no" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN student_no INTEGER DEFAULT 1")
    if "student_name" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN student_name TEXT DEFAULT ''")
    if "note" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN note TEXT DEFAULT ''")
    # 🔽 바로 여기! week 컬럼 추가
    if "week" not in cols:
        conn.execute("ALTER TABLE keywords ADD COLUMN week INTEGER")
    # ▲ week 컬럼은 NULL 허용: 과거 데이터엔 비워두고, 이후 저장 시 채우면 됨

    conn.commit()
    return conn


conn = init_db()

def add_keyword(kw: str, category: str, grade: str, class_num: int, student_no: int, student_name: str, note: str, week: int | None):
    # 한국 시간으로 저장 권장
    ts = datetime.now().astimezone().isoformat()
    with conn:
        conn.execute(
            "INSERT INTO keywords (keyword, category, grade, class_num, student_no, student_name, note, ts, week) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kw, category, grade, class_num, student_no, student_name, note, ts, week)
        )


def get_keywords(limit: int = 500, category: str | None = None):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts FROM keywords WHERE category = ? ORDER BY id DESC LIMIT ?", (category, limit))
    else:
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts FROM keywords ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return list(reversed(rows))

# 새: 키워드로 부연설명 조회
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

# ...existing code...
# 세션 상태 초기화 (입력창 제어용)
if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""
if "note_input" not in st.session_state:
    st.session_state["note_input"] = ""
if "category_select" not in st.session_state:
    st.session_state["category_select"] = "Vocabulary"
if "grade_select" not in st.session_state:
    st.session_state["grade_select"] = "2학년"
if "class_select" not in st.session_state:
    st.session_state["class_select"] = "1반"
if "student_no_select" not in st.session_state:
    st.session_state["student_no_select"] = "1번"
if "student_name" not in st.session_state:
    st.session_state["student_name"] = ""
# 추가: 수업 주차 초기값 (1~17)
if "week_select" not in st.session_state:
    st.session_state["week_select"] = 1
# 추가: Reading 선택 시 사용할 지문/문장 선택 기본값
if "reading_passage" not in st.session_state:
    st.session_state["reading_passage"] = 1
if "reading_sentence" not in st.session_state:
    st.session_state["reading_sentence"] = 1

if "msg" not in st.session_state:
    st.session_state["msg"] = ""
if "msg_type" not in st.session_state:
    st.session_state["msg_type"] = None

st.markdown("---")

# 입력 파트: 학년/반/번호/이름을 한 줄로 배치
# 학생 정보 입력(분리) — 확장 패널에 한 줄로 배치
# ...existing code...
# 학생 정보 입력(고정 표시) — 한 줄로 배치 (확장 패널 대신 고정)
col_g, col_c, col_n, col_name = st.columns([1,1,1,3])
with col_g:
    grade = st.selectbox("학년", ["2학년"], key="grade_select")
with col_c:
    class_options = [f"{i}반" for i in range(1,13)]
    class_sel = st.selectbox("반", class_options, key="class_select")
with col_n:
    num_options = [f"{i}번" for i in range(1,33)]
    num_sel = st.selectbox("번호", num_options, key="student_no_select")
with col_name:
    student_name = st.text_input("이름", key="student_name", placeholder="이름 입력")
# ...existing code...

st.markdown("---")


# 안내 문구(학생 정보 아래, 질문 입력과 분리)
st.write("💬 카테고리를 먼저 선택한 후, 헷갈리는 개념을 키워드로 입력하세요.")

# 1) 입력용 카테고리 선택 (키워드 입력 시에 사용할 카테고리)
# 카테고리와 수업 주차를 한 줄에 배치
col_cat, col_week = st.columns([2,1])
with col_cat:
    category = st.selectbox("입력할 카테고리 선택", ["Vocabulary", "Grammar", "Reading", "Else"], key="category_select")
with col_week:
    week = st.selectbox("수업 주차", list(range(1, 18)), index=st.session_state.get("week_select", 1)-1, format_func=lambda x: f"{x}주차", key="week_select")

# 2) 키워드 입력 (입력 파트)
input_key = "keyword_input"
# Reading이면 키워드 대신 지문/문장 선택 창으로 대체 (1~20)
if category == "Reading":
    st.markdown("질문할 문장 번호를 선택하세요.")
    c1, c2 = st.columns([1,1])
    with c1:
        reading_passage = st.selectbox("지문 번호", list(range(1,21)), index=st.session_state.get("reading_passage",1)-1, key="reading_passage", format_func=lambda x: f"{x}번 지문")
    with c2:
        reading_sentence = st.selectbox("문장 번호", list(range(1,21)), index=st.session_state.get("reading_sentence",1)-1, key="reading_sentence", format_func=lambda x: f"{x}번 문장")
    
    # 빈 keyword_input 상태 유지
    st.session_state[input_key] = ""
else:
    # 일반 카테고리에서는 기존 텍스트 입력 유지
    keyword = st.text_input("질문 키워드 입력", key=input_key)

# 부연 설명 입력란(문장)
note = st.text_area("부연 설명 (문장으로 입력)", key="note_input", height=80, placeholder="예: 단어가 사용된 예문을 알고 싶어요, 현재완료시제와 과거완료시제의 차이점이 헷갈려요.")

def submit_callback():
    # Reading일 때는 지문/문장 조합을 keyword로 저장
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
    # 숫자만 추출
    try:
        class_num = int(''.join(filter(str.isdigit, class_val)))
    except Exception:
        class_num = 1
    try:
        student_no = int(''.join(filter(str.isdigit, st.session_state.get("student_no_select", "1번"))))
    except Exception:
        student_no = 1
    student_name_val = st.session_state.get("student_name", "").strip()

    if kw:
        # week_select 값 가져오기
        week_val = st.session_state.get("week_select", None)
        
        # week 포함해 저장
        add_keyword(kw, cat, grade_val, class_num, student_no, student_name_val, note_text, week_val)

        # 입력창 비우기
        st.session_state[input_key] = ""
        st.session_state["note_input"] = ""
        st.session_state["msg"] = f"제출됨: [{cat}] {kw}"
        st.session_state["msg_type"] = "success"
    else:
        st.session_state["msg"] = "먼저 입력해주세요."
        st.session_state["msg_type"] = "warning"

st.button(
    "제출하기", 
    on_click=submit_callback,
    use_container_width=True,  # 가로폭 확장
    type="primary"             # 파란색으로 지정
)

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

# 입력 파트 종료 — 결과 파트는 아래에서 별도로 표시

# 분석 결과 페이지 이동 버튼 추가
st.markdown("---")
if st.button(
    "📊 실시간 분석 보러가기", 
    use_container_width=True, # 👈 가로폭을 페이지 전체 폭만큼 확장
):
    st.switch_page("pages/data visualization.py")
