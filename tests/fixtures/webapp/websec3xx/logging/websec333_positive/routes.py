@app.route("/debug/dump")
def debug_dump():
    return internal_state()
