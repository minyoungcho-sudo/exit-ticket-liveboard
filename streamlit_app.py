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

_FONT_FILE = _find_font_file()
if _FONT_FILE:
    FONT_PATH = str(_FONT_FILE.resolve())
    # 페이지 전역에 폰트 적용 (CSS 삽입)
    _css = f"""
    <style>
    @font-face {{
        font-family: 'NanumGothic';
        src: url('file://{FONT_PATH}') format('truetype');
    }}
    html, body, .stApp, .block-container, h1, h2, h3, h4, h5, p, label, div, span {{
        font-family: 'NanumGothic', sans-serif !important;
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

st.title("Exit Ticket Live Board")

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
# ...existing code...

# 2) 키워드 입력 (입력 파트)
input_key = "keyword_input"
keyword = st.text_input("질문 키워드 입력", key=input_key)
# 부연 설명 입력란(문장)
note = st.text_area("부연 설명 (문장으로 입력)", key="note_input", height=80, placeholder="예: 특정 문장에서 쓰임이 헷갈려요. 문장 전체를 적어주세요.")

def submit_callback():
    kw = st.session_state.get(input_key, "").strip()
    note_text = st.session_state.get("note_input", "").strip()
    cat = st.session_state.get("category_select", "Else")
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
        st.session_state[input_key] = ""
        st.session_state["note_input"] = ""
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
    st.markdown("### 전체 카테고리별 제출 수")
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
with st.expander("제출된 키워드 목록 보기", expanded=False):
    items = get_keywords(category=view_category)
    if items:
        table_rows = []
        for r in items:
            # r 구조: (id, keyword, category, grade, class_num, student_no, student_name, note, ts)
            _id, kw, cat, grade_db, class_db, no_db, name_db, note_db, ts = r
            submitter = f"{grade_db} {class_db}반 {no_db}번 {name_db}" if name_db else f"{grade_db} {class_db}반 {no_db}번"
            table_rows.append({
                "제출자": submitter,
                "카테고리": cat,
                "키워드": kw,
                "부연설명": note_db,
                "제출시간": ts
            })
        df_table = pd.DataFrame(table_rows)
        # Inventory tracker 느낌으로 정렬된 컬럼 표시
        cols_order = ["제출자", "카테고리", "키워드", "부연설명", "제출시간"]
        st.dataframe(df_table[cols_order], use_container_width=True)
    else:
        st.info("해당 카테고리에 제출된 항목이 없습니다.")
# ...existing code...

# -----------------------------
# 빈도 집계 및 시각화 추가 (워드클라우드 먼저, 그 다음 빈도)
# -----------------------------
st.markdown("---")
st.subheader(f"키워드 빈도 분석")

# 키워드 문자열만 추출 (필터 적용된 items 사용)
# items는 get_keywords(...)로부터 (id, keyword, category, grade, class_num, student_no, student_name, note, ts)
keywords = [kw for (_id, kw, _cat, _grade, _class, _no, _name, _note, _ts) in items]

if keywords:
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    # ...existing code...
    # 1) 워드클라우드 먼저
    st.markdown("#### 워드클라우드")
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

        # 클릭 가능한 단어 버튼(워드클라우드 아래)
        st.markdown("**워드클라우드 단어(클릭하면 부연설명 표시)**")
        word_options = df["keyword"].tolist() if not df.empty else []
        # 상위 30개만 버튼으로 표시
        max_buttons = min(30, len(word_options))
        cols = st.columns(6)
        if "selected_word" not in st.session_state:
            st.session_state["selected_word"] = ""

        for i, w in enumerate(word_options[:max_buttons]):
            col = cols[i % 6]
            if col.button(w):
                st.session_state["selected_word"] = w

        # 선택 단어가 있으면 부연설명 표시
        if st.session_state.get("selected_word"):
            selected_word = st.session_state["selected_word"]
            st.markdown(f"**선택된 단어:** {selected_word}")
            view_cat = st.session_state.get("view_category", None) if "view_category" in st.session_state else None
            explanations = get_explanations_by_keyword(selected_word, category=view_cat)
            if explanations:
                st.markdown("해당 단어를 입력한 학생들의 부연 설명:")
                for ex in explanations:
                    name, class_num, stu_no, note_text, ts = ex
                    student_label = f"{name}" if name else f"{class_num}반 {stu_no}번"
                    note_display = note_text if note_text else "(부연 설명 없음)"
                    st.write(f"- {student_label} — {note_display}")
            else:
                st.info("해당 단어에 대한 부연 설명이 없습니다.")
            # 선택 초기화 버튼
            if st.button("선택 초기화"):
                st.session_state["selected_word"] = ""
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요.\n터미널에서: pip3 install wordcloud pillow")
# ...existing code...
    # 2) 빈도순 막대그래프 (왼쪽=최대 -> 오른쪽=최소)
    st.markdown("#### 빈도순 막대그래프")
    df_chart = df.copy()
    order = df_chart["keyword"].tolist()
    chart = (
        alt.Chart(df_chart)
        .mark_bar()
        .encode(
            x=alt.X("keyword:N", sort=order, title="키워드"),
            y=alt.Y("count:Q", title="빈도"),
            tooltip=["keyword", "count"]
        )
        .properties(width="container", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

    st.markdown("#### 키워드 빈도")
    for idx, row in df.iterrows():
        st.write(f"{idx+1}. {row['keyword']} — {row['count']}")
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
st.markdown("---")
st.subheader("제출 데이터 탐색 (샘플 템플릿)")

# DB에서 전체 항목 불러오기
all_items = get_keywords(limit=2000, category=None)  # 전체 카테고리

# DataFrame으로 변환 (dt 컬럼으로 일시 파싱)
rows = []
for r in all_items:
    # r: (id, keyword, category, grade, class_num, student_no, student_name, ts)
    rows.append({
        "id": r[0],
        "keyword": r[1],
        "category": r[2],
        "grade": r[3],
        "class_num": r[4],
        "student_no": r[5],
        "student_name": r[6],
        "ts": r[7],
    })
df_all = pd.DataFrame(rows)

if df_all.empty:
    st.info("제출된 항목이 없습니다. 먼저 키워드를 제출해 주세요.")
else:
    # ts -> datetime 변환
    df_all["dt"] = pd.to_datetime(df_all["ts"], errors="coerce")

    # 학기(또는 기준) 시작 주를 데이터의 가장 빠른 제출일의 주 월요일로 잡아 주차(1~17) 계산
    from datetime import timedelta
    min_dt = df_all["dt"].min()
    if pd.isna(min_dt):
        term_start = None
    else:
        # 해당 날짜의 주 월요일을 시작(주차 1)으로 사용
        term_start = (min_dt - timedelta(days=min_dt.weekday())).date()

    def compute_academic_week(dt):
        if pd.isna(dt) or term_start is None:
            return None
        days = (dt.date() - term_start).days
        week = (days // 7) + 1
        # 범위를 1~17로 고정
        if week < 1:
            return 1
        if week > 17:
            return 17
        return int(week)

    df_all["week"] = df_all["dt"].apply(compute_academic_week)

    # ...existing code...
    # 반(chips 스타일) 멀티셀렉트 — 항상 1~12반 선택 가능하도록
    all_classes = list(range(1, 13))  # 1반 ~ 12반 고정 목록
    # 데이터에 실제로 존재하는 반은 따로 확인할 수 있지만, 옵션은 항상 1~12로 고정
    class_options = all_classes
    # 기본: 모두 선택
    class_sel = st.multiselect("반 필터 (chips)", class_options, default=class_options, format_func=lambda x: f"{x}반")
# ...existing code...

   # ...existing code...
    # 주차 슬라이더 (범위 1주차 ~ 17주차)
    min_week = 1
    max_week = 17
    # 데이터 기반 기본값
    data_weeks = df_all["week"].dropna().astype(int)
    data_min = int(data_weeks.min()) if not data_weeks.empty else min_week
    data_max = int(data_weeks.max()) if not data_weeks.empty else max_week
    default_start = max(min_week, data_min)
    default_end = min(max_week, data_max)

    # 학생 입력한 주차(입력 파트의 week_select)를 반영하여 기본 범위가 그 주차를 반드시 포함하도록 조정
    selected_week = st.session_state.get("week_select", None)
    if isinstance(selected_week, int):
        selected_week = max(min_week, min(max_week, selected_week))
        default_start = min(default_start, selected_week)
        default_end = max(default_end, selected_week)

    # 만약 데이터가 전혀 없을 때 기본값을 선정
    if default_start > default_end:
        default_start, default_end = min_week, min_week

    week_range = st.slider("주차 범위 (1~17주)", min_week, max_week, (default_start, default_end))
# ...existing code...
    # 필터 적용
    df_filtered = df_all.copy()
    if class_sel:
        df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
    df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]

    st.markdown(f"필터 적용: 반 = {', '.join([f'{c}반' for c in class_sel])} / 주차 = {week_range[0]} ~ {week_range[1]}")
    st.write(f"결과 항목: {len(df_filtered)}개")

    if not df_filtered.empty:
        # 카테고리별/주차별 최다 빈도 키워드 표 생성
        categories = ["Vocabulary", "Grammar", "Reading", "Else"]
        weeks = list(range(week_range[0], week_range[1] + 1))

        top_map = {}
        for w in weeks:
            row_vals = {}
            for c in categories:
                sub = df_filtered[(df_filtered["week"] == w) & (df_filtered["category"] == c)]
                if not sub.empty:
                    kw_counts = sub.groupby("keyword").size().reset_index(name="count").sort_values("count", ascending=False)
                    top = kw_counts.iloc[0]
                    row_vals[c] = f"{top['keyword']} ({int(top['count'])})"
                else:
                    row_vals[c] = ""
            top_map[w] = row_vals

        table_df = pd.DataFrame.from_dict(top_map, orient="index")[categories]
        table_df.index.name = "주차"
        st.markdown("#### 주차 × 카테고리 별 최다 빈도 키워드")
        st.dataframe(table_df)
    else:
        st.info("필터 조건에 맞는 항목이 없습니다.")
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
