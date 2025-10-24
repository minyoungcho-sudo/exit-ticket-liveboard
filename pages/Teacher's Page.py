import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import altair as alt

st.set_page_config(page_title="제출 데이터 탐색", layout="wide")

# DB 경로 (프로젝트 루트의 keywords.db 사용)
DB_PATH = Path(__file__).parents[1] / "keywords.db"

def get_all_items(limit: int = 2000):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id, keyword, category, grade, class_num, student_no, student_name, note, ts FROM keywords ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))

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

st.title("제출 데이터 탐색")
items = get_all_items()
rows = []
for r in items:
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

df_all = compute_week_from_dates(df_all)

# 반 필터(항상 1~12)
class_options = list(range(1,13))
class_sel = st.multiselect("반 필터 (chips)", class_options, default=class_options, format_func=lambda x: f"{x}반")

# 주차 범위 (1~17)
week_range = st.slider("주차 범위", 1, 17, (1, 17))

# 필터 적용
df_filtered = df_all.copy()
if class_sel:
    df_filtered = df_filtered[df_filtered["class_num"].isin(class_sel)]
df_filtered = df_filtered[df_filtered["week"].between(week_range[0], week_range[1])]


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

    table_df = pd.DataFrame.from_dict(top_map, orient="index")[categories]
    table_df.index.name = "주차"
    st.dataframe(table_df, use_container_width=True)