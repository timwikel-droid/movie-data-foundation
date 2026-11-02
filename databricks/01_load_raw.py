# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Load raw CSVs into Delta tables  (UNTESTED: no Databricks workspace was available when this was written)
# MAGIC Reads the synthetic CSVs from a Unity Catalog volume and writes them, unchanged, to `<catalog>.raw.*`.
# MAGIC Faults are kept on purpose: validation happens in dbt, not here.
# MAGIC
# MAGIC **Before running:** create the volume and upload `data/raw/*.csv` to it, e.g.
# MAGIC `CREATE VOLUME IF NOT EXISTS main.raw.landing;` then upload to `/Volumes/main/raw/landing/`.

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("landing_path", "/Volumes/main/raw/landing")
catalog = dbutils.widgets.get("catalog")
landing = dbutils.widgets.get("landing_path")

TABLES = ["users", "movies", "sessions", "mood_checkins", "recommendations", "ratings"]
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.raw")

# COMMAND ----------
for t in TABLES:
    df = (spark.read.option("header", True).option("inferSchema", True).csv(f"{landing}/{t}.csv"))
    (df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog}.raw.{t}"))
    print(f"{catalog}.raw.{t}: {df.count()} rows")
