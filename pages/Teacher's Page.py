import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import altair as alt

st.set_page_config(page_title="제출 데이터 탐색", layout="wide")

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

st.title("제출 데이터 탐색")

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

# ...existing code...

# 주차 슬라이더 (1~17) — 메인 페이지에서 선택한 주차를 기본으로 반영
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

# 슬라이더 기본값 결정: main_week_int가 유효하면 그 주차로 고정, 아니면 데이터 범위 사용
if main_week_int is not None and min_week <= main_week_int <= max_week:
    default_start = default_end = main_week_int
else:
    default_start = max(min_week, data_min)
    default_end = min(max_week, data_max)

# 별도 키를 사용해 슬라이더 상태 관리 (teacher_week_range)
week_range = st.slider("주차 범위", min_week, max_week, (default_start, default_end), key="teacher_week_range")

# 안전 보정: 만약 main_week_int가 존재하고 현재 슬라이더가 그 주차를 포함하지 않으면 강제 포함
if main_week_int is not None:
    if week_range[0] > main_week_int or week_range[1] < main_week_int:
        st.session_state["teacher_week_range"] = (main_week_int, main_week_int)
        week_range = (main_week_int, main_week_int)

# ...existing code continues (필터 적용 등) ...

# 필터 적용
df_filtered = df_all.copy()
if class_sel:
    df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
if view_cat and view_cat != "All":
    df_filtered = df_filtered[df_filtered["category"] == view_cat]
df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]

st.markdown(f"필터 적용: 반 = {', '.join([f'{c}반' for c in class_sel])} / 카테고리 = {view_cat} / 주차 = {week_range[0]} ~ {week_range[1]}")
st.write(f"결과 항목: {len(df_filtered)}개")

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

    # 인덱스를 1부터 시작하고, 인덱스 이름을 'No'로
    df_display.index = range(1, len(df_display) + 1)
    df_display.index.name = "No"

    # ✅ 표 컬럼 순서 지정 (인덱스 'No'는 자동으로 가장 왼쪽에 표시됨)
    cols_order = ["학년", "반", "번호", "이름", "카테고리", "키워드", "부연설명", "제출시간"]
    st.dataframe(df_display[cols_order], use_container_width=True)
else:
    st.info("필터된 항목이 없습니다.")
