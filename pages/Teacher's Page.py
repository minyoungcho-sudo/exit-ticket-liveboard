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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        # ✅ week 컬럼이 있는 최신 스키마
        cur.execute("""
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts, week
            FROM keywords
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        rows = list(reversed(rows))
        conn.close()
        return rows, True   # (rows, has_week)
    except sqlite3.OperationalError:
        # ✅ 구버전(week 없음) 호환
        cur.execute("""
            SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts
            FROM keywords
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        rows = list(reversed(rows))
        conn.close()
        return rows, False  # (rows, has_week)


def compute_week_from_dates(df):
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

st.title("제출 데이터 탐색 (상세)")

# 세션 상태에서 메인 페이지 입력값을 가져와 기본 필터로 사용
ss = st.session_state

# main 페이지에서 사용한 키들(있다면)
main_class_select = ss.get("class_select", None)      # e.g. "1반"
main_week_select = ss.get("week_select", None)        # e.g. 3 (int)
main_category_select = ss.get("category_select", None) # e.g. "Reading"
main_view_category = ss.get("view_category", None)    # e.g. "All" (사용자가 보기용으로 고른 값)

# 전체 데이터 로드 및 전처리
# 전체 데이터 로드 및 전처리
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

# ✅ week 컬럼이 없으면 ts로 주차 재계산, 있으면 그대로 사용
if "week" not in df_all.columns:
    df_all = compute_week_from_dates(df_all)
else:
    df_all["week"] = pd.to_numeric(df_all["week"], errors="coerce").astype("Int64")


# 반(항상 1~12) — main 페이지의 단일 선택값을 반영해 기본값으로 설정
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

# 카테고리 필터 — main 페이지에서 '보기용 카테고리' 또는 입력 카테고리 반영
category_options = ["All", "Vocabulary", "Grammar", "Reading", "Else"]
default_category = main_view_category if main_view_category in category_options else (main_category_select if main_category_select in category_options else "All")
view_cat = st.selectbox("카테고리 필터", category_options, index=category_options.index(default_category))

# 주차 슬라이더 (1~17) — main 페이지에서 입력한 주차를 포함하도록 기본 범위 조정
# 주차 슬라이더 (1~17) — main 페이지의 week_select를 기본값으로 반영
min_week, max_week = 1, 17
data_weeks = df_all["week"].dropna().astype(int)
data_min = int(data_weeks.min()) if not data_weeks.empty else min_week
data_max = int(data_weeks.max()) if not data_weeks.empty else max_week

if isinstance(main_week_select, int):
    # 선택 주차만 보이도록 시작(원하면 범위를 넓게 잡아도 됨)
    start_default = end_default = max(min_week, min(int(main_week_select), max_week))
else:
    start_default, end_default = data_min, data_max

# 안전 보정
start_default = max(min_week, min(start_default, max_week))
end_default   = max(min_week, min(end_default,   max_week))
if start_default > end_default:
    start_default, end_default = data_min, data_max

week_range = st.slider("주차 범위", min_week, max_week, (start_default, end_default))

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
    # 카테고리×주차 표: 각 칸에 최빈 키워드 표시
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

    # ...existing code...
    table_df = pd.DataFrame.from_dict(top_map, orient="index")[categories]
    table_df.index.name = "주차"
    st.dataframe(table_df, use_container_width=True)

    # 추가: 선택한 주차 범위에 속하는 "원본 제출 항목"을 모두 보여줌
    st.markdown("#### 선택한 주차에 제출된 원본 항목 (모두 보기)")
    # 표시할 칼럼 정리
    raw_cols = ["ts", "category", "keyword", "note", "grade", "class_num", "student_no", "student_name"]
    df_display = df_filtered.copy()
    if not df_display.empty:
        # human friendly 컬럼명
        df_display = df_display[raw_cols].rename(columns={
            "ts": "제출시간",
            "category": "카테고리",
            "keyword": "키워드",
            "note": "부연설명",
            "grade": "학년",
            "class_num": "반",
            "student_no": "번호",
            "student_name": "이름"
        })
        # 인덱스를 1부터 시작하게 하고 정렬(최신 위)
        df_display = df_display.sort_values("제출시간", ascending=False).reset_index(drop=True)
        df_display.index = range(1, len(df_display) + 1)
        df_display.index.name = "No"
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("필터된 항목이 없습니다.")
# ...existing code...