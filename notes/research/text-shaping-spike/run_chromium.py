"""Measure the corpus in headless Chromium: run_chromium.py corpus.json out.json font0 font1 font2."""
import json, logging, subprocess, sys, glob, os, re, tempfile
logging.basicConfig(level=logging.INFO, format="%(message)s", filename="spike.log")
log = logging.getLogger(__name__)
corpus, out, *fonts = sys.argv[1:]
html = open(os.path.join(os.path.dirname(__file__), "chromium.html")).read()
html = html.replace("CORPUS", open(corpus).read())
for i, f in enumerate(fonts):
    html = html.replace(f"FONT{i}", os.path.abspath(f))
chrome = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))[-1]
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "m.html"); open(p, "w").write(html)
    r = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--allow-file-access-from-files",
        "--virtual-time-budget=10000", "--dump-dom", "file://" + p], capture_output=True, text=True, timeout=120)
m = re.search(r"RESULT(.*?)ENDRESULT", r.stdout, re.S)
if not m:
    sys.exit("no result: " + r.stderr[-500:] + r.stdout[-500:])
res = json.loads(m.group(1)); res["chrome"] = chrome
json.dump(res, open(out, "w"))
log.info("ok %s", chrome)
