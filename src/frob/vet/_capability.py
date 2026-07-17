"""Tree-sitter-backed capability scan over a dependency's local source
(docs/vet.md "Capability taxonomy" + "Mechanics").

Detection is a per-language token/substring scan over `frob.lang`-parsed
source (Python/JS-TS/Rust first-class, per docs/vet.md); C/C++ is scanned
honestly-empty (no idiomatic literal exists yet -- see docs/vet.md
"Python, Rust, C/C++"). A missing/unreadable file never crashes the scan;
it degrades to an empty capability set plus a `source-unavailable`-shaped
note (docs/vet.md "Honest limits").
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.logging import get_logger

_log = get_logger(__name__)

# extension -> language bucket used to pick a pattern table
_EXT_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",  # same substring vocabulary; no dedicated JS grammar entry
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
}

# capability -> substrings that, if present anywhere in the file's source
# text, mark the capability observed. Deliberately coarse (recall over
# precision): a false positive here just means an extra declaration line in
# [vet.allow]; a false negative is a missed attack.
_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "python": {
        "exec": ("subprocess.", "os.system(", "os.popen(", "os.exec", "Popen("),
        "eval": (
            "eval(",
            "exec(",
            "compile(",
            "__import__(",
            "importlib.import_module(",
        ),
        "net": (
            "socket.",
            "urllib.",
            "http.client",
            "requests.",
            "aiohttp.",
            "httpx.",
        ),
        "fs-write": ("os.remove(", "shutil.rmtree(", "os.rename(", "open(", ".write("),
        "env": ("os.environ", "os.getenv("),
        "ffi": ("ctypes.", "import ctypes", "cffi"),
        "install-hook": ("cmdclass",),
    },
    "typescript": {
        "exec": ("child_process", "execSync(", "spawn(", "execFile("),
        "eval": ("eval(", "new Function(", "vm.runInContext(", "vm.runInNewContext("),
        "net": (
            'require("http")',
            "require('http')",
            "fetch(",
            "axios.",
            "net.connect(",
            "http.request(",
            "https.request(",
        ),
        "fs-write": ("fs.writeFile", "fs.appendFile", "fs.unlink", "fs.rm("),
        "env": ("process.env",),
        "ffi": ("ffi-napi", "node-gyp", "napi"),
        "install-hook": ("cmdclass",),  # unreachable in JS; kept for table symmetry
    },
    "rust": {
        "exec": ("Command::new(",),
        "eval": (),
        "net": ("TcpStream", "reqwest::", "hyper::", "std::net::"),
        "fs-write": ("File::create(", "fs::write(", "fs::remove_file("),
        "env": ("std::env::var(", "std::env::vars("),
        "ffi": ('extern "C"', "libc::"),
        "install-hook": (),
    },
}


# frob:doc docs/vet.md#public-api
def language_for(path: Path) -> str | None:
    """The pattern-table bucket for `path`'s extension, or `None` (e.g. C/C++)."""
    return _EXT_LANGUAGE.get(path.suffix.lower())


# frob:doc docs/vet.md#public-api
def scan_file_capabilities(path: Path) -> frozenset[str]:
    """Capability tokens observed in one source file's raw text."""
    language = language_for(path)
    if language is None:
        _log.debug("vet: no capability pattern table for %s; treating as opaque", path)
        return frozenset()
    table = _PATTERNS[language]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s for capability scan: %s", path, exc)
        return frozenset()

    found: set[str] = set()
    for capability, needles in table.items():
        if any(needle in text for needle in needles):
            found.add(capability)
    if found:
        _log.info("vet: %s: capabilities observed: %s", path, sorted(found))
    return frozenset(found)


# frob:doc docs/vet.md#public-api
def decode_to_exec_signal(path: Path) -> bool:
    """True if one function's body reaches both a decode-ish and an exec-ish
    token (docs/vet.md "eval-reachability": the highest-precision detector).

    Uses `frob.lang` symbol extraction so the two tokens must co-occur inside
    the SAME function body, not merely the same file.
    """
    language = language_for(path)
    if language is None:
        return False
    parsed = parse_file(path)
    if parsed.is_err:
        _log.debug(
            "vet: %s: parse failed for decode-to-exec scan: %s", path, parsed.danger_err
        )
        return False

    decode_needles = (
        "base64",
        "b64decode",
        "atob",
        "fromhex",
        "fromCharCode",
        "decode(",
        "zlib.decompress",
    )
    exec_needles = (
        "eval",
        "exec",
        "Function",
        "compile",
        "__import__",
        "vm.runInContext",
    )

    for symbol in parsed.danger_ok.symbols:
        body = " ".join(symbol.body_tokens)
        has_decode = any(needle in body for needle in decode_needles)
        has_exec = any(needle in body for needle in exec_needles)
        if has_decode and has_exec:
            _log.warning(
                "vet: decode-to-exec dataflow in %s::%s", path, symbol.qualname
            )
            return True
    return False


# frob:doc docs/vet.md#public-api
def scan_directory_capabilities(
    source_dir: Path, *, max_files: int = 500
) -> tuple[frozenset[str], bool]:
    """Aggregate capabilities across every scannable file under `source_dir`.

    Returns `(capabilities, decode_to_exec_hit)`. Bounded by `max_files` so a
    huge vendored dependency tree cannot make `frob vet` unusable.
    """
    capabilities: set[str] = set()
    decode_to_exec_hit = False
    scanned = 0
    for ext in _EXT_LANGUAGE:
        if scanned >= max_files:
            break
        for path in source_dir.rglob(f"*{ext}"):
            if scanned >= max_files:
                _log.warning(
                    "vet: %s: capability scan truncated at %d file(s)",
                    source_dir,
                    max_files,
                )
                break
            if "test" in path.parts or "tests" in path.parts:
                # test fixtures routinely exercise every capability on purpose;
                # scanning them produces pure noise for the shipped package.
                continue
            capabilities |= scan_file_capabilities(path)
            if not decode_to_exec_hit:
                decode_to_exec_hit = decode_to_exec_signal(path)
            scanned += 1
    _log.info(
        "vet: %s: scanned %d file(s), capabilities=%s, decode-to-exec=%s",
        source_dir,
        scanned,
        sorted(capabilities),
        decode_to_exec_hit,
    )
    return frozenset(capabilities), decode_to_exec_hit


__all__ = [
    "decode_to_exec_signal",
    "language_for",
    "scan_directory_capabilities",
    "scan_file_capabilities",
]
