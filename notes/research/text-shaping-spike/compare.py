"""Compare lib widths against Chromium: compare.py libs.json chrome.json."""
import json, sys, statistics as st
import logging
logging.basicConfig(level=logging.INFO, format="%(message)s", filename="compare.log", filemode="w")
log = logging.getLogger(__name__)
libs, ch = (json.load(open(p)) for p in sys.argv[1:3])
fams = libs["families"]
for lib in ("cosmic-text", "parley"):
    log.info(f"== {lib}  {libs[lib]['us_per_string']:.1f} us/string  deterministic={libs[lib]['deterministic']}")
    allm = []
    for i, fam in enumerate(fams):
        w, c = libs[lib]["widths"][fam][1:], ch[f"F{i}"][1:]  # skip the empty string (parley reports a 5px phantom)
        d = [abs(a - b) for a, b in zip(w, c)]
        allm += d
        n1 = sum(x > 0.5 for x in d); n2 = sum(x > 0.05 for x in d)
        worst = max(range(len(d)), key=d.__getitem__)
        log.info(f"  {fam:18s} mean|d|={st.mean(d):.4f} p95={sorted(d)[int(len(d)*.95)]:.4f} max={max(d):.4f} (idx {worst}) >0.05px:{n2} >0.5px:{n1}")
    log.info(f"  ALL mean={st.mean(allm):.4f} max={max(allm):.4f}")
