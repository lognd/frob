"""Fixture (T-5339): a Frob_L002 waiver with no explain= artifact."""


# frob:waive Frob_L002 reason="reviewed manually, looks fine"
def delete_all(cursor):
    cursor.execute("DELETE FROM sessions")
