"""Fixture (T-5339): a Frob_L002 waiver WITH a real explain= artifact."""

# frob:waive Frob_L002 reason="single-tenant table, plan checked" \
# explain="tests/fixtures/sql/explain/delete_all_sessions.explain.txt"
def delete_all(cursor):
    cursor.execute("DELETE FROM sessions")
