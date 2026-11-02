# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Delete one user everywhere  (UNTESTED: written from Delta/Unity Catalog documentation, not run)
# MAGIC Why this differs from the SQLite version:
# MAGIC * Delta tables have **no ON DELETE CASCADE**; Unity Catalog primary/foreign keys are informational only. Every table is deleted explicitly, children first.
# MAGIC * dbt rebuilds the marts **from the raw tables**, so the user must also be removed from `raw.*`, or the next `dbt build` brings them back.
# MAGIC * `DELETE` on Delta is logical: old files stay readable through time travel until `VACUUM` removes them (default retention 7 days).
# MAGIC   Physical erasure is only complete after the retention window and a VACUUM.

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("user_id", "")
catalog, uid = dbutils.widgets.get("catalog"), dbutils.widgets.get("user_id")
assert uid, "user_id is required"
M, R = f"{catalog}.moodbox", f"{catalog}.raw"
run = lambda sql: spark.sql(sql, args={"uid": uid})   # named parameter markers: no string-built SQL

# COMMAND ----------
# 1. Derived tables that carry no user_id: delete via the keys that belong to this user.
run(f"""DELETE FROM {M}.rec_facts WHERE rec_id IN (
          SELECT rec.rec_id FROM {M}.fct_recommendations rec
          JOIN {M}.fct_mood_checkins c ON c.checkin_id = rec.checkin_id WHERE c.user_id = :uid)""")

# 2. Marts, children before parents.
run(f"DELETE FROM {M}.fct_ratings WHERE user_id = :uid")
run(f"""DELETE FROM {M}.fct_recommendations WHERE checkin_id IN (
          SELECT checkin_id FROM {M}.fct_mood_checkins WHERE user_id = :uid)""")
run(f"DELETE FROM {M}.fct_mood_checkins WHERE user_id = :uid")
run(f"DELETE FROM {M}.fct_sessions WHERE user_id = :uid")
run(f"DELETE FROM {M}.dim_users WHERE user_id = :uid")

# 3. Raw tables (so a dbt rebuild cannot resurrect the user).
run(f"DELETE FROM {R}.ratings WHERE user_id = :uid")
run(f"""DELETE FROM {R}.recommendations WHERE checkin_id IN (
          SELECT checkin_id FROM {R}.mood_checkins WHERE user_id = :uid)""")
run(f"DELETE FROM {R}.mood_checkins WHERE user_id = :uid")
run(f"DELETE FROM {R}.sessions WHERE user_id = :uid")
run(f"DELETE FROM {R}.users WHERE user_id = :uid")

# COMMAND ----------
# 4. Audit: store only a one-way hash (same formula as src/privacy.py), never the id itself.
spark.sql(f"""CREATE TABLE IF NOT EXISTS {M}.deletion_log
              (user_hash STRING, action STRING, processed_at TIMESTAMP)""")
run(f"""INSERT INTO {M}.deletion_log
        SELECT substr(sha2(:uid, 256), 1, 16), 'user_deletion', current_timestamp()""")

# COMMAND ----------
# MAGIC %md
# MAGIC **Then:** re-run the dbt job so `mood_genre_summary` no longer includes this user, and schedule
# MAGIC `VACUUM <table>` (after the retention window) for every table above to remove the underlying files.
