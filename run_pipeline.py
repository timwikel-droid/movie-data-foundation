"""End-to-end run: generate -> stage -> check -> clean -> report. Usage: python run_pipeline.py [--regen]"""
import sqlite3, sys
from pathlib import Path
from src.generate_data import generate
from src.quality_checks import load_staging, run_checks
from src.build_clean import build_clean, SCHEMA
from src.report import build_report, write_markdown
from src.utils import md_table

ROOT = Path(__file__).resolve().parent
RAW, DB, OUT = ROOT / "data" / "raw", ROOT / "data" / "moodbox.db", ROOT / "outputs"


def main(regen: bool = False) -> None:
    OUT.mkdir(exist_ok=True)
    if regen or not (RAW / "users.csv").exists():
        print("Generating synthetic data...", generate(out_dir=RAW))
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA.read_text())                    # creates audit tables + clean tables
    print("Staged rows:", load_staging(conn, RAW))
    checks = run_checks(conn)
    checks.to_csv(OUT / "quality_report.csv", index=False)
    clean = build_clean(conn)
    clean.to_csv(OUT / "clean_summary.csv", index=False)
    (OUT / "quality_report.md").write_text(
        "# Data quality report\n\n## Checks on raw (staging) data\n\n"
        + md_table(checks.drop(columns=["run_at"]))
        + "\n## Staging -> clean tables\n\n" + md_table(clean)
        + "\nDropped rows include downstream records whose parent row was rejected (e.g. check-ins of a rejected session).\n")
    tables = build_report(conn)
    write_markdown(tables, OUT / "insights_report.md")
    print(checks[["check_id", "severity", "rows_flagged"]].to_string(index=False))
    print(clean.to_string(index=False))
    print("Wrote reports to", OUT)


if __name__ == "__main__":
    main(regen="--regen" in sys.argv)
