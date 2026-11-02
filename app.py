"""MoodBox data foundation dashboard. Run: streamlit run app.py  (after: python run_pipeline.py)"""
import sqlite3
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st
from src.report import build_report, LIMITATIONS, MIN_CELL

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "moodbox.db"

st.set_page_config(page_title="MoodBox data foundation", layout="wide")
st.title("MoodBox data foundation")
st.caption("Synthetic data only. Demonstrates data-quality checks, governance controls and consent-aware reporting.")

if not DB.exists():
    st.error("Database not found. Run `python run_pipeline.py` first.")
    st.stop()

conn = sqlite3.connect(DB)
tab_q, tab_i, tab_g = st.tabs(["Data quality", "Insights", "Governance"])

with tab_q:
    q = pd.read_csv(ROOT / "outputs" / "quality_report.csv")
    s = pd.read_csv(ROOT / "outputs" / "clean_summary.csv")
    c1, c2, c3 = st.columns(3)
    c1.metric("Checks run", len(q))
    c2.metric("Checks with findings", int((q.rows_flagged > 0).sum()))
    c3.metric("Rows dropped to clean tables", int(s.rows_dropped.sum()))
    st.subheader("Checks on raw data")
    st.dataframe(q.drop(columns=["run_at"]), width="stretch", hide_index=True)
    st.bar_chart(q[q.severity == "error"].set_index("check_id")["rows_flagged"])
    st.subheader("Staging to clean")
    st.dataframe(s, width="stretch", hide_index=True)

with tab_i:
    t = build_report(conn)
    st.dataframe(t["headline"], hide_index=True, width="stretch")
    st.subheader("Share of recommended genres by mood")
    heat = alt.Chart(t["genre_mix"]).mark_rect().encode(
        x="genre:N", y="mood:N", color=alt.Color("share_pct:Q", title="% of recs"),
        tooltip=["mood", "genre", "recs", "share_pct"])
    st.altair_chart(heat, width="stretch")
    st.subheader("Best-rated genre per mood")
    st.dataframe(t["best_by_mood"], hide_index=True, width="stretch")
    st.subheader("Rating behaviour by rank")
    st.dataframe(t["by_rank"], hide_index=True, width="stretch")
    st.subheader("Limitations")
    st.markdown("\n".join(f"- {x}" for x in LIMITATIONS))
    st.caption(f"Cells under {MIN_CELL} records are suppressed. Only users with analytics consent are included.")

with tab_g:
    for name in ("governance", "data_dictionary"):
        with st.expander(name.replace("_", " ").title(), expanded=(name == "governance")):
            st.markdown((ROOT / "docs" / f"{name}.md").read_text())
