# ...existing code...
import streamlit as st
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd
import altair as alt

# 워드클라우드 라이브러리 시도 임포트 (matplotlib 없이도 표시 가능하도록 to_image 사용)
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

st.set_page_config(page_title="수업 헷갈렸던 영어 키워드", layout="centered")

st.title("Exit Ticket Live Board")

# DB 경로
DB_PATH = Path(__file__).parent / "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Else',
            grade TEXT NOT NULL DEFAULT '2학년',
            class_num INTEGER NOT NULL DEFAULT 1,
            student_no INTEGER NOT NULL DEFAULT 1,
            student_name TEXT NOT NULL DEFAULT '',
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
    conn.commit()
    return conn

conn = init_db()

def add_keyword(kw: str, category: str, grade: str, class_num: int, student_no: int, student_name: str):
    ts = datetime.utcnow().isoformat()
    with conn:
        conn.execute(
            "INSERT INTO keywords (keyword, category, grade, class_num, student_no, student_name, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kw, category, grade, class_num, student_no, student_name, ts)
        )

def get_keywords(limit: int = 500, category: str | None = None):
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, ts FROM keywords WHERE category = ? ORDER BY id DESC LIMIT ?", (category, limit))
    else:
        cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, ts FROM keywords ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return list(reversed(rows))

# 세션 상태 초기화 (입력창 제어용)
if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""
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
category = st.selectbox("입력할 카테고리 선택", ["Vocabulary", "Grammar", "Reading", "Else"], key="category_select")

# 2) 키워드 입력 (입력 파트)
input_key = "keyword_input"
keyword = st.text_input("질문 키워드 입력", key=input_key)

def submit_callback():
    kw = st.session_state.get(input_key, "").strip()
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
        add_keyword(kw, cat, grade_val, class_num, student_no, student_name_val)
        st.session_state[input_key] = ""
        st.session_state["msg"] = f"제출됨: [{cat}] {kw} ({grade_val} {class_num}반 {student_no}번 {student_name_val})"
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

counts = get_category_counts()
if counts:
    df_counts = pd.DataFrame(counts, columns=["category", "count"])
    pie = (
        alt.Chart(df_counts)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("count:Q", title="제출 수"),
            color=alt.Color("category:N", legend=alt.Legend(title="카테고리")),
            tooltip=["category", "count"]
        )
        .properties(width=350, height=350)
    )
    st.markdown("### 전체 카테고리별 제출 수")
    st.altair_chart(pie, use_container_width=False)
else:
    st.info("아직 제출된 항목이 없어 카테고리 통계를 표시할 수 없습니다.")

# 보기용(필터) 카테고리 선택 — 결과 파트 시작
view_category = st.selectbox("보기용 카테고리 선택", ["All", "Vocabulary", "Grammar", "Reading", "Else"], index=0, key="view_category")

st.subheader(f"제출된 키워드 목록")

# 필터를 적용해서 항목 불러오기
items = get_keywords(category=view_category)

if items:
    for row in items:
        # row 구조: (id, keyword, category, grade, class_num, student_no, student_name, ts)
        kw = row[1]
        cat = row[2]
        # 카테고리와 키워드만 표시
        st.write(f"[{cat}] {kw}")
else:
    st.info("해당 카테고리에 제출된 항목이 없습니다.")

# -----------------------------
# 빈도 집계 및 시각화 추가 (워드클라우드 먼저, 그 다음 빈도)
# -----------------------------
st.markdown("---")
st.subheader(f"키워드 빈도 분석")

# 키워드 문자열만 추출 (필터 적용된 items 사용)
keywords = [kw for (_id, kw, _cat, _grade, _class, _no, _name, _ts) in items]

if keywords:
    freq = Counter(keywords)
    df = pd.DataFrame(freq.items(), columns=["keyword", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    # 1) 워드클라우드 먼저
    st.markdown("#### 워드클라우드")
    if WORDCLOUD_AVAILABLE:
        freq_dict = dict(freq)
        wc = WordCloud(width=800, height=400, background_color="white")
        wc.generate_from_frequencies(freq_dict)
        img = wc.to_image()
        st.image(img, use_container_width=True)
    else:
        st.info("워드클라우드를 보려면 'wordcloud'와 'pillow' 패키지를 설치하세요.\n터미널에서: pip3 install wordcloud pillow")

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
st.markdown("---")
st.subheader("제출 데이터 탐색 (샘플 템플릿)")

# DB에서 전체 항목 불러오기
all_items = get_keywords(limit=2000, category=None)  # 전체 카테고리

# DataFrame으로 변환
rows = []
for r in all_items:
    # r: (id, keyword, category, grade, class_num, student_no, student_name, ts)
    try:
        dt = datetime.fromisoformat(r[7])
        week = dt.isocalendar().week
    except Exception:
        dt = None
        week = None
    rows.append({
        "id": r[0],
        "keyword": r[1],
        "category": r[2],
        "grade": r[3],
        "class_num": r[4],
        "student_no": r[5],
        "student_name": r[6],
        "ts": r[7],
        "week": week
    })
df_all = pd.DataFrame(rows)

if df_all.empty:
    st.info("제출된 항목이 없습니다. 먼저 키워드를 제출해 주세요.")
else:
    # 반(chips 스타일) 멀티셀렉트
    class_options = sorted(df_all["class_num"].dropna().unique().astype(int).tolist())
    # 기본: 모두 선택
    class_sel = st.multiselect("반 필터 (chips)", class_options, default=class_options, format_func=lambda x: f"{x}반")

    # 주차 슬라이더 (범위)
    min_week = int(df_all["week"].dropna().min()) if not df_all["week"].dropna().empty else 1
    max_week = int(df_all["week"].dropna().max()) if not df_all["week"].dropna().empty else 52
    week_range = st.slider("주차 범위", 1, 52, (min_week, max_week))

    # 필터 적용
    df_filtered = df_all.copy()
    if class_sel:
        df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
    df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]

    st.markdown(f"필터 적용: 반 = {', '.join([f'{c}반' for c in class_sel])} / 주차 = {week_range[0]} ~ {week_range[1]}")
    st.write(f"결과 항목: {len(df_filtered)}개")

    if not df_filtered.empty:
        # 키워드별 집계 (내림차순)
        df_counts = df_filtered.groupby("keyword").size().reset_index(name="count")
        df_counts = df_counts.sort_values("count", ascending=False).reset_index(drop=True)

        # 파이 차트 (상위 몇개만)
        top_n = st.slider("파이 차트에 표시할 상위 개수", 3, min(20, max(3, len(df_counts))), value=min(6, len(df_counts)))
        df_pie = df_counts.head(top_n)

        pie = (
            alt.Chart(df_pie)
            .mark_arc(innerRadius=40)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("keyword:N", legend=alt.Legend(title="키워드")),
                tooltip=["keyword", "count"]
            )
            .properties(height=300)
        )
        st.altair_chart(pie, use_container_width=True)

        # 막대그래프: 왼쪽=빈도 높은 순서
        order = df_counts["keyword"].tolist()
        bar = (
            alt.Chart(df_counts)
            .mark_bar()
            .encode(
                x=alt.X("keyword:N", sort=order, title="키워드"),
                y=alt.Y("count:Q", title="빈도"),
                tooltip=["keyword", "count"]
            )
            .properties(height=300)
        )
        st.altair_chart(bar, use_container_width=True)

        # 테이블: 상위 항목과 예시 제출(최신)
        st.markdown("#### 키워드별 샘플 제출 (최신)")
        for _, row in df_counts.head(20).iterrows():
            kw = row["keyword"]
            cnt = row["count"]
            examples = df_filtered[df_filtered["keyword"] == kw].sort_values("id", ascending=False).head(3)
            example_texts = []
            for _, ex in examples.iterrows():
                example_texts.append(f"{int(ex['grade']) if isinstance(ex['grade'], int) else ex['grade']} {int(ex['class_num']) if not pd.isna(ex['class_num']) else ''}반 — {ex['student_name'] or str(ex['student_no'])}")
            st.write(f"{kw} — {cnt}회 — 예: {', '.join(example_texts)}")

        # 원하면 전체 결과 테이블도 표시
        if st.checkbox("필터된 원본 데이터 보기"):
            st.dataframe(df_filtered.sort_values("ts", ascending=False))
    else:
        st.info("필터 조건에 맞는 항목이 없습니다.")
# ...existing code...
# -----------------------------
# 샘플 탐색 섹션: movies 템플릿 변형
# - genre chips -> '반' 멀티셀렉트(chips 스타일)
# - year slider -> 주차(week) 슬라이더
# -----------------------------
st.markdown("---")
st.subheader("제출 데이터 탐색 (샘플 템플릿)")

# DB에서 전체 항목 불러오기
all_items = get_keywords(limit=2000, category=None)  # 전체 카테고리

# DataFrame으로 변환
rows = []
for r in all_items:
    # r: (id, keyword, category, grade, class_num, student_no, student_name, ts)
    try:
        dt = datetime.fromisoformat(r[7])
        week = dt.isocalendar().week
    except Exception:
        dt = None
        week = None
    rows.append({
        "id": r[0],
        "keyword": r[1],
        "category": r[2],
        "grade": r[3],
        "class_num": r[4],
        "student_no": r[5],
        "student_name": r[6],
        "ts": r[7],
        "week": week
    })
df_all = pd.DataFrame(rows)

if df_all.empty:
    st.info("제출된 항목이 없습니다. 먼저 키워드를 제출해 주세요.")
else:
    # 반(chips 스타일) 멀티셀렉트
    class_options = sorted(df_all["class_num"].dropna().unique().astype(int).tolist())
    # 기본: 모두 선택
    class_sel = st.multiselect("반 필터 (chips)", class_options, default=class_options, format_func=lambda x: f"{x}반")

    # 주차 슬라이더 (범위)
    min_week = int(df_all["week"].dropna().min()) if not df_all["week"].dropna().empty else 1
    max_week = int(df_all["week"].dropna().max()) if not df_all["week"].dropna().empty else 52
    week_range = st.slider("주차 범위", 1, 52, (min_week, max_week))

    # 필터 적용
    df_filtered = df_all.copy()
    if class_sel:
        df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
    df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]

    st.markdown(f"필터 적용: 반 = {', '.join([f'{c}반' for c in class_sel])} / 주차 = {week_range[0]} ~ {week_range[1]}")
    st.write(f"결과 항목: {len(df_filtered)}개")

    if not df_filtered.empty:
        # 키워드별 집계 (내림차순)
        df_counts = df_filtered.groupby("keyword").size().reset_index(name="count")
        df_counts = df_counts.sort_values("count", ascending=False).reset_index(drop=True)

        # 파이 차트 (상위 몇개만)
        top_n = st.slider("파이 차트에 표시할 상위 개수", 3, min(20, max(3, len(df_counts))), value=min(6, len(df_counts)))
        df_pie = df_counts.head(top_n)

        pie = (
            alt.Chart(df_pie)
            .mark_arc(innerRadius=40)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("keyword:N", legend=alt.Legend(title="키워드")),
                tooltip=["keyword", "count"]
            )
            .properties(height=300)
        )
        st.altair_chart(pie, use_container_width=True)

        # 막대그래프: 왼쪽=빈도 높은 순서
        order = df_counts["keyword"].tolist()
        bar = (
            alt.Chart(df_counts)
            .mark_bar()
            .encode(
                x=alt.X("keyword:N", sort=order, title="키워드"),
                y=alt.Y("count:Q", title="빈도"),
                tooltip=["keyword", "count"]
            )
            .properties(height=300)
        )
        st.altair_chart(bar, use_container_width=True)

        # 테이블: 상위 항목과 예시 제출(최신)
        st.markdown("#### 키워드별 샘플 제출 (최신)")
        for _, row in df_counts.head(20).iterrows():
            kw = row["keyword"]
            cnt = row["count"]
            examples = df_filtered[df_filtered["keyword"] == kw].sort_values("id", ascending=False).head(3)
            example_texts = []
            for _, ex in examples.iterrows():
                example_texts.append(f"{int(ex['grade']) if isinstance(ex['grade'], int) else ex['grade']} {int(ex['class_num']) if not pd.isna(ex['class_num']) else ''}반 — {ex['student_name'] or str(ex['student_no'])}")
            st.write(f"{kw} — {cnt}회 — 예: {', '.join(example_texts)}")

        # 원하면 전체 결과 테이블도 표시
        if st.checkbox("필터된 원본 데이터 보기"):
            st.dataframe(df_filtered.sort_values("ts", ascending=False))
    else:
        st.info("필터 조건에 맞는 항목이 없습니다.")
# ...existing code...