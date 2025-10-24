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
    /* 텍스트용 요소만 NanumGothic 적용 (span/div/전체 선택자 사용 금지) */
    html, body, .stApp, .block-container, h1, h2, h3, h4, h5, p, label, input, textarea {{
        font-family: 'NanumGothic', sans-serif !important;
    }}
    /* Material Icons(리게이처 방식)를 사용하는 요소는 원래 폰트를 유지하도록 예외 처리 */
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

st.set_page_config(page_title="Exit Ticket Live Board", layout="centered")

# ...existing code...
# 중앙 정렬된 제목으로 변경
st.markdown("<h1 style='text-align:center; margin-bottom:0.25rem;'>💡 Exit Ticket Live Board 💡</h1>", unsafe_allow_html=True)
# ...existing code...

# DB 경로
DB_PATH = Path(__file__).parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    # note 컬럼 추가 (부연 설명 저장)
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
    # 기존 DB에 새 컬럼이 없을 경우 안전하게 추가
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
    conn.commit()
    return conn

conn = init_db()

def add_keyword(kw: str, category: str, grade: str, class_num: int, student_no: int, student_name: str, note: str):
    ts = datetime.utcnow().isoformat()
    with conn:
        conn.execute(
            "INSERT INTO keywords (keyword, category, grade, class_num, student_no, student_name, note, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (kw, category, grade, class_num, student_no, student_name, note, ts)
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
st.write("카테고리를 먼저 선택한 후, 헷갈리는 개념을 키워드로 입력하세요.")

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
        add_keyword(kw, cat, grade_val, class_num, student_no, student_name_val, note_text)
        # 입력창 비우기
        st.session_state[input_key] = ""
        st.session_state["note_input"] = ""
        # Reading이면 선택값은 유지하거나 비울 수 있음 — 여기선 유지
        st.session_state["msg"] = f"제출됨: [{cat}] {kw}"
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

# 입력 파트 종료 — 결과 파트는 아래에서 별도로 표시
st.markdown("---")

# 보기용 카테고리 선택 전에 전체 카테고리별 제출 수를 파이 차트로 표시
def get_category_counts():
    cur = conn.cursor()
    cur.execute("SELECT category, COUNT(*) FROM keywords GROUP BY category")
    rows = cur.fetchall()
    return rows

# ...existing code...
# ...existing code...
counts = get_category_counts()
if counts:
    df_counts = pd.DataFrame(counts, columns=["category", "count"])
    # 백분율 칼럼 추가 (툴팁에 사용)
    df_counts["percent"] = (df_counts["count"] / df_counts["count"].sum() * 100).round(1)

    # 통합 제목 (파이 + 바 한 번에)
    st.markdown("### 📊 카테고리별 질문 현황")
    col1, col2 = st.columns([1,1])

    # 일관된 색상 스케일 사용
    color_scale = alt.Scale(domain=df_counts["category"].tolist(), scheme="category10")

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
# ...existing code...
# ...existing code...

# ...existing code...
# 보기용(필터) 카테고리 선택 — 결과 파트 시작
view_category = st.selectbox("보기용 카테고리 선택", ["All", "Vocabulary", "Grammar", "Reading", "Else"], index=0, key="view_category")

# 제출된 키워드 목록을 접힘(버튼) 방식으로 보여주기 — Inventory tracker 스타일 표
# ...existing code...
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
                "제출시간": ts
            })
        df_table = pd.DataFrame(table_rows)
        # 인덱스를 1부터 시작하도록 설정
        df_table.index = range(1, len(df_table) + 1)
        df_table.index.name = "No"
        cols_order = ["카테고리", "키워드", "부연설명", "제출시간"]
        st.dataframe(df_table[cols_order], use_container_width=True)
    else:
        st.info("해당 카테고리에 제출된 항목이 없습니다.")
# ...existing code...

# -----------------------------
# 빈도 집계 및 시각화 추가 (워드클라우드 먼저, 그 다음 빈도)
# -----------------------------
st.markdown("---")
st.subheader(f"🔍 자주 언급한 질문 키워드")

# 키워드 문자열만 추출 (필터 적용된 items 사용)
# items는 get_keywords(...)로부터 (id, keyword, category, grade, class_num, student_no, student_name, note, ts)
keywords = [kw for (_id, kw, _cat, _grade, _class, _no, _name, _note, _ts) in items]

if keywords:
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    # ...existing code...
    # 1) 워드클라우드 먼저
    st.markdown("#### ")
    if WORDCLOUD_AVAILABLE:
        freq_dict = dict(freq)
        # 로컬 NanumGothic 폰트를 사용하도록 font_path 전달
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            font_path=FONT_PATH if ('FONT_PATH' in globals() and FONT_PATH) else None,
        )
        wc.generate_from_frequencies(freq_dict)
        
        img = wc.to_image()
        st.image(img, use_container_width=True)

        st.markdown("---")

        # 워드클라우드 안내 문구 (기존 안내문과 동일한 스타일)
        st.markdown("<div style='font-size:14px; color:#333; margin-top:8px; margin-bottom:8px;'>💬 키워드를 클릭하면 질문을 확인할 수 있습니다.</div>", unsafe_allow_html=True)
        # 버튼과의 간격 확보용 추가 여백
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        # 클릭 가능한 상위 5개 단어 버튼(워드클라우드 아래, 빈도 순) — 고정 5칸 배치로 간격 통일
        top_words = df.head(5)["keyword"].tolist()
# ...existing code...
        if "selected_word" not in st.session_state:
            st.session_state["selected_word"] = ""

        cols = st.columns(5)
        for i in range(5):
            if i < len(top_words):
                w = top_words[i]
                if cols[i].button(w):
                    st.session_state["selected_word"] = w
            else:
                # 빈 칸 유지하여 레이아웃 균일화
                cols[i].write("")

        # 선택 단어가 있으면 부연설명만 표로 예쁘게 표시 (반/번호 제거), 인덱스는 1부터 시작
        if st.session_state.get("selected_word"):
            selected_word = st.session_state["selected_word"]
            view_cat = st.session_state.get("view_category", None) if "view_category" in st.session_state else None
            explanations = get_explanations_by_keyword(selected_word, category=view_cat)
            # explanations: (student_name, class_num, student_no, note, ts)
            if explanations:
                notes = [ex[3] if ex[3] else "(부연 설명 없음)" for ex in explanations]
                df_notes = pd.DataFrame({"부연설명": notes})
                df_notes.index = range(1, len(df_notes) + 1)  # 번호 1부터 시작
                df_notes.index.name = "No"
                # 컨테이너 폭을 사용하여 칼럼 폭 자동 정렬 (통일감)
                st.dataframe(df_notes, use_container_width=True)
            else:
                st.info("해당 단어에 대한 부연 설명이 없습니다.")
            
# ...existing code...
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요.\n터미널에서: pip3 install wordcloud pillow")
# ...existing code...
    
    st.markdown("---")

    # 2) 빈도순 막대그래프 (왼쪽=최대 -> 오른쪽=최소) - 색상/디자인 통일감 있게 개선
    st.markdown("#### 🚩 질문 키워드 RANKING")
    df_chart = df.copy()
    # df는 이미 내림차순 정렬되어 있어 order 그대로 사용하면 왼쪽이 최대
    order = df_chart["keyword"].tolist()

    # 통일된 색상 스케일 (키워드 수에 따라 scheme 선택)
    color_scheme = "category20" if len(order) <= 20 else "category20"
    kw_color_scale = alt.Scale(domain=order, scheme=color_scheme)

    bar = (
        alt.Chart(df_chart)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("keyword:N", sort=order, title="키워드"),
            # y축을 정수 형식으로 표시하도록 axis.format 추가
            y=alt.Y("count:Q", title="빈도", axis=alt.Axis(format="d")),
            color=alt.Color("keyword:N", scale=kw_color_scale, legend=None),
            tooltip=[alt.Tooltip("keyword:N", title="키워드"),
                     alt.Tooltip("count:Q", title="건수", format=".0f")]
        )
        .properties(height=360)
    )

    # 숫자 레이블을 위에 붙여 가독성 향상 (정수 표기)
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
# ...existing code...

else:
    st.info("집계할 키워드가 없습니다. 먼저 키워드를 제출해 주세요.")
# ...existing code...

# ...existing code...
# -----------------------------
# 샘플 탐색 섹션: movies 템플릿 변형
# - genre chips -> '반' 멀티셀렉트(chips 스타일)
# - year slider -> 주차(week) 슬라이더
# -----------------------------
# ...existing code...

# ...existing code...
st.markdown("---")
with st.container():
    st.subheader("보드 초기화")
    confirm = st.checkbox("정말 초기화할래요? (그래프/표/입력 모두 비워짐)")

    if st.button("🧹 완전 초기화", use_container_width=True, disabled=not confirm):
        try:
            # 1) DB 비우기 (테이블 전체 삭제)
            #   - 전체 초기화: 아래 DELETE 그대로 사용
            #   - 특정 학년/반만 초기화하고 싶으면 WHERE 절 추가 예시:
            #     conn.execute("DELETE FROM keywords WHERE grade=? AND class_num=?", (선택학년, 선택반))
            with conn:
                conn.execute("DELETE FROM keywords;")

            # (선택) WAL 체크포인트/용량 정리 — WAL 모드라면 아래가 가볍고 안전합니다
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:
                pass
            # VACUUM을 쓰고 싶다면 트랜잭션 밖에서 호출해야 합니다.
            # try:
            #     conn.execute("VACUUM;")
            # except Exception:
            #     pass

            # 2) 세션/캐시 비우기
            keys_to_reset = [
                "keyword_input","note_input","selected_word","msg","msg_type",
                "view_category","category_select","grade_select","class_select",
                "student_no_select","student_name"
            ]
            for k in keys_to_reset:
                st.session_state.pop(k, None)

            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass

            st.success("✅ 모든 데이터가 초기화되었습니다. (DB+세션)")
            st.rerun()  # 즉시 빈 상태로 다시 렌더링

        except Exception as e:
            st.error(f"초기화 중 오류: {e}")
