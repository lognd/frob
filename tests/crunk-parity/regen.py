#!/usr/bin/env python3
"""Regenerate the crunk parity corpus (fixtures/, expected/, PROVENANCE, index).

Usage:
    python regen.py --crunk-repo PATH --python PATH [--commit REV]

--crunk-repo is the Python crunk git repository (read-only: only `git
archive` and `git log` run against it).  --python is an interpreter that has
crunk's dependencies installed (the repository's own .venv works); crunk
itself is imported from a scratch copy of the archived commit, never from
the repository.  Output is deterministic: absolute paths, timestamps and
the scratch layout are normalized away, so a second run is byte-identical.
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from capture_plugin import _delta, _snapshot  # noqa: E402

log = logging.getLogger("crunk_parity.regen")

CAPTURED_NOTE = "first captured 2026-10-04"
STATIC_PROJECTS = ["web_pages", "tailwind_v4", "screens_v1_1", "gallery005_routes"]
# Projects with a crunk.toml that the command matrix runs against.
MATRIX_PROJECTS = ["int04_default", "init_default", "gallery005_routes", "screens_v1_1"]
SKIP_SLOW = ["--deselect", "tests/system/test_build.py",
             "--ignore=tests/system/test_wheel_contents.py"]


def matrix_commands(project: str) -> list[list[str]]:
    """The fixed crunk command matrix run against each matrix project."""
    other = "../gallery005_routes" if project == "int04_default" else "../int04_default"
    return [
        ["check", "--json"],
        ["check", "--report"],
        ["check", "--contrast"],
        ["tokens", "--format", "css"],
        ["tokens", "--format", "json"],
        ["tokens", "--format", "tailwind"],
        ["tokens", "--check"],
        ["fix", "--dry-run"],
        ["map", "--json"],
        ["query", "find", "card", "--json"],
        ["query", "component", "card", "--json"],
        ["query", "dupes", "--json"],
        ["query", "unused", "--json"],
        ["query", "uses", "color-ink", "--json"],
        ["query", "color", "#1a1a1a", "--json"],
        ["query", "violations", "--json"],
        ["explain", "color-ink", "--json"],
        ["explain", "color-ink"],
        ["preview"],
        ["diff", other],
    ]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing text output, and log it."""
    log.info("run: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class Normalizer:
    """Rewrites absolute paths and timestamps to stable placeholders."""

    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self.pairs = sorted(pairs, key=lambda p: -len(p[0]))

    def __call__(self, text: str) -> str:
        for real, token in self.pairs:
            text = text.replace(real, token)
        text = re.sub(r"\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:?\d\d)?", "<TIMESTAMP>", text)
        # Cache store ids hash the (scratch-dependent) project path.
        text = re.sub(r"(<TMP>/cache-home\d*/)[0-9a-f]{16}\b", r"\1<STORE_ID>", text)
        return text


def slug(node: str) -> str:
    """Filesystem-safe scenario id from a pytest node id."""
    path, _, rest = node.partition("::")
    stem = Path(path).stem.removeprefix("test_")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", rest.removeprefix("test_")).strip("_")
    if len(name) > 90:
        name = name[:80] + "_" + format(abs(hash_str(name)) % 0xFFFFFF, "06x")
    return f"{stem}/{name}"


def hash_str(s: str) -> int:
    """Stable (process-independent) string hash for slug truncation."""
    h = 5381
    for ch in s:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return h


def write_text(path: Path, text: str) -> None:
    """Write ASCII text (LF), failing loudly on any non-ASCII content."""
    if not text.isascii():
        raise SystemExit(f"non-ASCII content for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("ascii"))


def write_files(base: Path, delta: dict, norm: Normalizer) -> list[str]:
    """Write a snapshot delta under base; return the relative paths written."""
    written = []
    for rel, b64 in sorted(delta["changed"].items()):
        raw = base64.b64decode(b64)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            log.warning("skipping non-utf8 file %s", rel)
            continue
        write_text(base / rel, norm(text))
        written.append(rel)
    return written


def int_e2e_ids(path: str) -> list[str]:
    """E2E-nn / INT-nn ids named by a test file name (combined files give several)."""
    stem = Path(path).stem
    m = re.match(r"test_(e2e|int)_((?:\d+_?)+)", stem)
    if not m:
        return []
    kind = m.group(1).upper()
    return [f"{kind}-{n}" for n in m.group(2).strip("_").split("_")]


def capture_suite(args, scratch: Path, src: Path, env: dict, norm: Normalizer) -> dict:
    """Run the crunk e2e+integration suites under the recorder; write e2e corpus."""
    out = scratch / "capture"
    shutil.rmtree(out, ignore_errors=True)
    env = {**env, "CRUNK_CAPTURE_OUT": str(out)}
    r = run([args.python, "-m", "pytest", "-p", "capture_plugin", f"--basetemp={scratch / 'bt'}",
             "-p", "no:cacheprovider", "-q", "tests/system", "tests/integration",
             "-m", "not slow", *SKIP_SLOW], cwd=src, env=env)
    log.info("pytest tail: %s", r.stdout.strip().splitlines()[-1:])
    if r.returncode != 0:
        raise SystemExit(f"crunk suite failed:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    index: dict[str, dict] = {}
    steps_seen: dict[str, int] = {}
    for line in (out / "raw.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        node = rec["node"]
        sid = slug(node)
        n = steps_seen.get(sid, 0) + 1
        steps_seen[sid] = n
        root, cwd = rec["root"], rec["cwd"]
        local = Normalizer([(root, "<ROOT>")] + norm.pairs)
        rel_cwd = os.path.relpath(cwd, root)
        fx = HERE / "fixtures" / "e2e" / sid
        ex = HERE / "expected" / "e2e" / sid
        write_files(fx / f"{n:02d}.setup", rec["setup"], local)
        step = {
            "node": node.replace("\\", "/"),
            "argv": [local(a) for a in rec["argv"]],
            "cwd": "." if rel_cwd == "." else rel_cwd,
            "env": {k: local(v) for k, v in sorted(rec["env"].items())},
            "stdin": rec["stdin"],
            "setup_deleted": rec["setup"]["deleted"],
            "command": "python -m crunk " + " ".join(local(a) for a in rec["argv"]),
        }
        write_text(fx / f"{n:02d}.step.json", json.dumps(step, indent=2, sort_keys=True) + "\n")
        write_text(ex / f"{n:02d}.result.json",
                   json.dumps({"exit": rec["exit"], "effects_deleted": rec["effects"]["deleted"]},
                              indent=2, sort_keys=True) + "\n")
        write_text(ex / f"{n:02d}.stdout", local(rec["stdout"]))
        write_text(ex / f"{n:02d}.stderr", local(rec["stderr"]))
        write_files(ex / f"{n:02d}.effects", rec["effects"], local)
        for ident in int_e2e_ids(node.split("::")[0]):
            e = index.setdefault(ident, {"source": node.split("::")[0], "scenarios": []})
            if sid not in e["scenarios"]:
                e["scenarios"].append(sid)
    return index


def capture_matrix(args, scratch: Path, src: Path, env: dict, norm: Normalizer) -> dict:
    """Write static fixtures and run the command matrix; return the index part."""
    fixtures = HERE / "fixtures" / "static"
    for name in STATIC_PROJECTS:
        shutil.copytree(src / "tests" / "fixtures" / name, fixtures / name)
    tree = ast.parse((src / "tests/integration/test_int_04_tokens_spec.py").read_text())
    consts = {t.targets[0].id: ast.literal_eval(t.value) for t in tree.body
              if isinstance(t, ast.Assign) and isinstance(t.targets[0], ast.Name)}
    write_text(fixtures / "int04_default" / "crunk.toml", consts["_TOML"])
    write_text(HERE / "expected" / "int-04-golden" / "tokens.css", consts["_EXPECTED_CSS"])

    work = scratch / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    for name in ("int04_default", "gallery005_routes", "screens_v1_1"):
        shutil.copytree(fixtures / name, work / name)
    (work / "init_default").mkdir()
    local = Normalizer([(str(work), "<WORK>")] + norm.pairs)
    r = run([args.python, "-m", "crunk", "init"],
            cwd=work / "init_default", env=env)
    if r.returncode != 0:
        raise SystemExit(f"crunk init failed: {r.stderr}")
    init_files = _snapshot(work / "init_default")
    for rel, data in sorted(init_files.items()):
        write_text(fixtures / "init_default" / rel, data.decode("utf-8"))
    write_text(HERE / "expected" / "matrix" / "init_default" / "_init.stdout", local(r.stdout))

    index: dict[str, dict] = {}
    for project in MATRIX_PROJECTS:
        cwd = work / project
        for argv in matrix_commands(project):
            pre = _snapshot(cwd)
            r = run([args.python, "-m", "crunk", *argv], cwd=cwd, env=env)
            eff = _delta(pre, _snapshot(cwd))
            name = re.sub(r"[^A-Za-z0-9._-]+", "_", " ".join(argv)).strip("_")
            base = HERE / "expected" / "matrix" / project / name
            meta = {"project": project, "argv": [local(a) for a in argv], "exit": r.returncode,
                    "command": f"python -m crunk {' '.join(local(a) for a in argv)}",
                    "cwd": f"fixtures/static/{project}"}
            write_text(base.with_suffix(".cmd.json"), json.dumps(meta, indent=2, sort_keys=True) + "\n")
            write_text(base.with_suffix(".stdout"), local(r.stdout))
            write_text(base.with_suffix(".stderr"), local(r.stderr))
            write_files(base.with_suffix(".effects"), eff, local)
            index.setdefault(project, {"commands": []})["commands"].append(name)
    return index


def provenance(args, src: Path, py_version: str, crunk_version: str, commit: str, cdate: str) -> str:
    """Render the PROVENANCE file text."""
    return (
        "crunk parity corpus provenance\n"
        "==============================\n"
        "Source repository : the Python crunk repository (MIT; same owner as frob v2, MIT)\n"
        f"Source commit     : {commit}\n"
        f"Commit date       : {cdate}\n"
        f"crunk version     : {crunk_version} (python -m crunk --version, from the archived commit)\n"
        f"Interpreter       : {py_version}\n"
        f"Corpus note       : {CAPTURED_NOTE}; regen is deterministic\n"
        "\n"
        "Regenerate:\n"
        "  python tests/crunk-parity/regen.py --crunk-repo <crunk checkout> \\\n"
        "      --python <interpreter with crunk deps> --commit " + commit + "\n"
        "\n"
        "Golden output commands (cwd = fixtures/static/<project>, NO_COLOR=1):\n"
        "  - e2e: every `python -m crunk ...` call made by crunk tests/system and\n"
        "    tests/integration, recorded by capture_plugin.py; the exact argv of each\n"
        "    call is in fixtures/e2e/<scenario>/NN.step.json (field `command`).\n"
        "  - matrix: expected/matrix/<project>/<name>.cmd.json (field `command`).\n"
        "  - int-04 golden: tokens.css extracted verbatim from\n"
        "    tests/integration/test_int_04_tokens_spec.py (_EXPECTED_CSS), spec _TOML.\n"
        "\n"
        "Normalization: pytest tmp roots -> <ROOT>, matrix work dir -> <WORK>,\n"
        "scratch, cache and home paths -> <CRUNK_SRC>/<CACHE>/<HOME>, timestamps ->\n"
        "<TIMESTAMP>.  Not captured: playwright-backed tests (E2E-60, 61, 70, web\n"
        "pages) skip without a browser; build/wheel tests are excluded.\n"
    )


def main() -> int:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crunk-repo", required=True, type=Path)
    ap.add_argument("--python", required=True)
    ap.add_argument("--commit", default="HEAD")
    args = ap.parse_args()

    repo = args.crunk_repo.resolve()
    commit = run(["git", "-C", str(repo), "rev-parse", args.commit]).stdout.strip()
    cdate = run(["git", "-C", str(repo), "log", "-1", "--format=%cI", commit]).stdout.strip()
    scratch = Path(tempfile.mkdtemp(prefix="crunk-parity-"))
    try:
        src = scratch / "src"
        src.mkdir()
        arc = subprocess.run(["git", "-C", str(repo), "archive", commit], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(src)], input=arc.stdout, check=True)
        (scratch / "home").mkdir()
        (scratch / "cache").mkdir()
        env = {**os.environ, "NO_COLOR": "1", "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPATH": os.pathsep.join([str(src / "src"), str(HERE)]),
               "HOME": str(scratch / "home"), "CRUNK_CACHE_DIR": str(scratch / "cache"),
               "XDG_CACHE_HOME": str(scratch / "cache")}
        env.pop("VIRTUAL_ENV", None)
        pairs = [(str(scratch / "src"), "<CRUNK_SRC>"), (str(scratch / "cache"), "<CACHE>"),
                 (str(scratch / "home"), "<HOME>"), (str(scratch / "bt"), "<TMP>"),
                 (str(scratch), "<SCRATCH>"), (str(repo), "<CRUNK_REPO>"),
                 (str(Path.home()), "<HOME>")]
        norm = Normalizer(pairs)
        for d in ("fixtures", "expected"):
            shutil.rmtree(HERE / d, ignore_errors=True)
        crunk_version = run([args.python, "-m", "crunk", "--version"], cwd=src, env=env).stdout.strip()
        py_version = run([args.python, "--version"]).stdout.strip()

        index = {"e2e_int": capture_suite(args, scratch, src, env, norm),
                 "matrix": capture_matrix(args, scratch, src, env, norm)}
        # INT ids with no CLI capture: name their source test (library-level).
        for p in sorted((src / "tests/integration").glob("test_int_*.py")):
            for ident in int_e2e_ids(p.name):
                index["e2e_int"].setdefault(ident, {"source": f"tests/integration/{p.name}",
                                                    "scenarios": []})
                index["e2e_int"][ident]["source"] = f"tests/integration/{p.name}"
        index["e2e_int"]["INT-04"]["golden"] = "expected/int-04-golden/tokens.css"
        index["e2e_int"]["INT-04"]["fixture"] = "fixtures/static/int04_default"
        index["static_fixtures"] = {n: f"fixtures/static/{n}" for n in STATIC_PROJECTS + ["int04_default", "init_default"]}
        for ident, e in index["e2e_int"].items():
            e["fixture_dirs"] = [f"fixtures/e2e/{s}" for s in e["scenarios"]]
            e["expected_dirs"] = [f"expected/e2e/{s}" for s in e["scenarios"]]
            if not e["scenarios"]:
                e["note"] = "library-level test (no CLI subprocess); source named, fixtures inline in the test"
        write_text(HERE / "index.json", json.dumps(index, indent=2, sort_keys=True) + "\n")
        write_text(HERE / "PROVENANCE", provenance(args, src, py_version, crunk_version, commit, cdate))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    # Final scan: no absolute home/tmp paths, ASCII only.
    bad = []
    for p in HERE.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.name not in ("regen.py",):
            t = p.read_bytes().decode("utf-8", "replace")
            if re.search(r"/home/|/tmp/|/Users/|claude-1000|pytest-of-", t) or not t.isascii():
                bad.append(str(p.relative_to(HERE)))
    if bad:
        log.error("path or non-ASCII leak in: %s", bad[:20])
        return 1
    log.info("corpus written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
