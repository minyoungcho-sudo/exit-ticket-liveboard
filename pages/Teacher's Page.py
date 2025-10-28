import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import altair as alt

st.set_page_config(page_title="제출 데이터 탐색", layout="centered")

# 🔒-------------------- 비밀번호 보호 (페이지 전용) --------------------
PAGE_LOCK_KEY = "auth_explorer_page"  # 이 페이지 전용 세션 키
DEFAULT_PASSWORD = "1234"       # secrets가 없을 때 기본 비밀번호
PASSWORD = st.secrets.get("page_password", DEFAULT_PASSWORD)

def require_password():
    """비밀번호가 맞을 때만 아래 콘텐츠가 렌더되도록 막아줍니다."""
    if PAGE_LOCK_KEY not in st.session_state:
        st.session_state[PAGE_LOCK_KEY] = False

    if not st.session_state[PAGE_LOCK_KEY]:
        st.title("🔐 관리자 전용 페이지")
        st.write("이 페이지를 보려면 비밀번호가 필요합니다.")
        pw = st.text_input("비밀번호", type="password")
        col1, col2 = st.columns([1,3])
        with col1:
            ok = st.button("접속")
        if (ok or pw) and pw == PASSWORD:
            st.session_state[PAGE_LOCK_KEY] = True
            st.success("접속 성공! 페이지를 불러오는 중…")
            st.rerun()
        elif (ok or pw) and pw:
            st.error("비밀번호가 올바르지 않습니다.")
        st.stop()  # 🔑 비밀번호가 맞지 않으면 이후 코드 실행을 중단

require_password()
# 🔒------------------ /비밀번호 보호 (여기 아래는 보호됨) ------------------

# DB 경로 (프로젝트 루트의 keywords.db 사용)
DB_PATH = Path(__file__).parents[1] / "keywords.db"

def get_all_items(limit: int = 5000):
    """
    DB에서 항목을 불러옵니다.
    최신 스키마(week 컬럼 포함)인 경우와 구버전(week 없음)을 모두 처리해서
    (rows, has_week) 형태로 반환합니다.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts, week
            FROM keywords
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return list(reversed(rows)), True
    except sqlite3.OperationalError:
        cur.execute(
            """
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts
            FROM keywords
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return list(reversed(rows)), False

def compute_week_from_dates(df):
    """ts를 기준으로 학기 시작을 가장 이른 제출일의 주 월요일로 잡아 1~17주로 계산."""
    if df.empty:
        return df
    df["dt"] = pd.to_datetime(df["ts"], errors="coerce")
    min_dt = df["dt"].min()
    if pd.isna(min_dt):
        term_start = None
    else:
        term_start = (min_dt - timedelta(days=min_dt.weekday())).date()
    def _wk(dt):
        if pd.isna(dt) or term_start is None:
            return None
        days = (dt.date() - term_start).days
        w = (days // 7) + 1
        if w < 1: return 1
        if w > 17: return 17
        return int(w)
    df["week"] = df["dt"].apply(_wk)
    return df

# --- 페이지 본문 (비밀번호 통과 시에만 렌더) ---
st.markdown("<h1 style='text-align:center; margin:0.25rem 0;'>제출 데이터 탐색</h1>", unsafe_allow_html=True)
st.markdown("---")

# 메인 페이지의 입력값을 세션에서 가져와 기본 필터로 반영
ss = st.session_state
main_class_select = ss.get("class_select", None)       # 예: "1반"
main_week_select  = ss.get("week_select", None)        # 예: 3 (int)
main_category_select = ss.get("category_select", None) # 예: "Reading"
main_view_category   = ss.get("view_category", None)   # 예: "All"

# 데이터 로드
items, has_week = get_all_items()
rows = []
for r in items:
    if has_week:
        rows.append({
            "id": r[0],
            "keyword": r[1],
            "category": r[2],
            "grade": r[3],
            "class_num": r[4],
            "student_no": r[5],
            "student_name": r[6],
            "note": r[7],
            "ts": r[8],
            "week": r[9],
        })
    else:
        rows.append({
            "id": r[0],
            "keyword": r[1],
            "category": r[2],
            "grade": r[3],
            "class_num": r[4],
            "student_no": r[5],
            "student_name": r[6],
            "note": r[7],
            "ts": r[8],
        })
df_all = pd.DataFrame(rows)

if df_all.empty:
    st.info("제출된 항목이 없습니다. 메인 페이지에서 키워드를 먼저 제출하세요.")
    st.stop()

# week 컬럼이 없으면 재계산, 있으면 정수형으로 정리
if "week" not in df_all.columns:
    df_all = compute_week_from_dates(df_all)
else:
    df_all["week"] = pd.to_numeric(df_all["week"], errors="coerce").astype("Int64")

# 반 필터 (항상 1~12) — 메인 페이지 선택을 기본값으로 반영
class_options = list(range(1,13))
if main_class_select:
    try:
        main_class_num = int(''.join(filter(str.isdigit, str(main_class_select))))
        default_classes = [main_class_num] if main_class_num in class_options else class_options
    except Exception:
        default_classes = class_options
else:
    default_classes = class_options

class_sel = st.multiselect("반 필터 (chips)", class_options, default=default_classes, format_func=lambda x: f"{x}반")

# 카테고리 필터 — 메인 페이지의 보기용 카테고리 또는 입력 카테고리 반영
category_options = ["All", "Vocabulary", "Grammar", "Reading", "Else"]
default_category = main_view_category if main_view_category in category_options else (main_category_select if main_category_select in category_options else "All")
view_cat = st.selectbox("카테고리 필터", category_options, index=category_options.index(default_category))

# 주차 슬라이더 (1~17)
min_week, max_week = 1, 17
data_weeks = df_all["week"].dropna().astype(int) if "week" in df_all.columns else pd.Series(dtype=int)
data_min = int(data_weeks.min()) if not data_weeks.empty else min_week
data_max = int(data_weeks.max()) if not data_weeks.empty else max_week

# 메인 페이지에서 저장한 week_select 가져오기(있으면 정수로 변환)
main_week_select = st.session_state.get("week_select", None)
try:
    main_week_int = int(main_week_select) if main_week_select is not None else None
except Exception:
    main_week_int = None

# 슬라이더 기본값 결정 및 세션 초기화 (🚨 수정된 부분)
if "teacher_week_range" not in st.session_state:
    if main_week_int is not None and min_week <= main_week_int <= max_week:
        # main_week_int가 유효하면 해당 주차 하나로 기본값 설정
        default_start = default_end = main_week_int
    else:
        # 그렇지 않으면 데이터 전체 범위로 기본값 설정
        default_start = max(min_week, data_min)
        default_end = min(max_week, data_max)
    st.session_state["teacher_week_range"] = (default_start, default_end) # 👈 첫 실행 시에만 기본값 저장

# 별도 키를 사용해 슬라이더 상태 관리 (🚨 value 인자를 제거)
week_range = st.slider(
    "주차 범위", 
    min_week, 
    max_week, 
    key="teacher_week_range" # 👈 key만 남겨서 Session State의 값을 사용하도록 함
    # st.session_state["teacher_week_range"] 이 값은 삭제!
)

# 필터링을 위해 위젯의 현재 값 가져오기
# week_range 변수는 st.session_state["teacher_week_range"]와 동일합니다.
week_range = st.session_state["teacher_week_range"]

# 필터 적용
df_filtered = df_all.copy()
if class_sel:
    df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
if view_cat and view_cat != "All":
    df_filtered = df_filtered[df_filtered["category"] == view_cat]
df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]

if df_filtered.empty:
    st.info("필터 조건에 맞는 항목이 없습니다.")
else:
    # 카테고리×주차 표: 각 칸에 최다 빈도 키워드 표시
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
    st.dataframe(table_df, use_container_width=True)

# 선택한 주차 범위에 속하는 원본 제출 항목 모두 표시
st.markdown("#### 선택한 주차에 제출된 원본 항목 (모두 보기)")
raw_cols = ["ts", "category", "keyword", "note", "grade", "class_num", "student_no", "student_name"]
df_display = df_filtered.copy()
if not df_display.empty:
    df_display = df_display[raw_cols].rename(columns={
        "ts": "제출시간",
        "category": "카테고리",
        "keyword": "키워드",
        "note": "부연설명",
        "grade": "학년",
        "class_num": "반",
        "student_no": "번호",
        "student_name": "이름"
    }).sort_values("제출시간", ascending=False).reset_index(drop=True)

    df_display.index = range(1, len(df_display) + 1)
    df_display.index.name = "No"

    cols_order = ["학년", "반", "번호", "이름", "카테고리", "키워드", "부연설명", "제출시간"]
    st.dataframe(df_display[cols_order], use_container_width=True)
else:
    st.info("필터된 항목이 없습니다.")

# 반별 제출량 합계 그래프
st.markdown("---")
st.markdown("### 🧮 반별 제출량 합계")

counts_series = df_filtered.groupby("class_num").size()
all_classes = list(range(1, 13))
counts_full = counts_series.reindex(all_classes, fill_value=0).reset_index()
counts_full.columns = ["class_num", "count"]
counts_full["class_str"] = counts_full["class_num"].astype(str) + "반"

bar = (
    alt.Chart(counts_full)
    .mark_bar(cornerRadius=6)
    .encode(
        x=alt.X("class_str:N", sort=[f"{i}반" for i in all_classes], title=" "),
        y=alt.Y("count:Q", title="제출 수", axis=alt.Axis(format="d", tickMinStep=1)),
        color=alt.Color("count:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
        tooltip=[
            alt.Tooltip("class_str:N", title="반"),
            alt.Tooltip("count:Q", title="제출 수", format="d")
        ],
    )
    .properties(height=320)
)
labels = alt.Chart(counts_full).mark_text(dy=-8, color="#222", fontSize=12).encode(
    x=alt.X("class_str:N", sort=[f"{i}반" for i in all_classes]),
    y=alt.Y("count:Q", axis=alt.Axis(format="d", tickMinStep=1)),
    text=alt.Text("count:Q", format="d")
)
st.altair_chart(bar + labels, use_container_width=True)

def _clear_board_data():
    """DB의 keywords 테이블을 비우고 관련 session_state 키를 초기화합니다."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM keywords")
        conn.commit()
        cur.execute("VACUUM")
    finally:
        conn.close()

    keys_to_clear = [
        "week_select", "class_select", "category_select", "view_category",
        "teacher_week_range", "quiz_data", "answers", "submitted"
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

st.markdown("---")
with st.expander("⚠️ 보드 초기화 (관리자 전용)", expanded=False):
    st.warning("모든 제출 데이터가 완전히 삭제됩니다. 되돌릴 수 없습니다.")
    confirm_text = st.text_input("위 작업을 진행하려면 확인 문구 '초기화' 를 입력하세요.")
    if st.button("보드 초기화", key="move_reset_btn"):
        if confirm_text.strip() == "초기화":
            _clear_board_data()
            st.success("초기화 완료 — 페이지가 다시 로드됩니다.")
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()
        else:
            st.error("확인 문구가 일치하지 않습니다. '초기화' 를 입력해야 합니다.")
