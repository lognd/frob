# vet subsystem audit -- false-negative / evasion hunt

North-star under test: "if `frob vet` approves, the dependency+code is actually
safe." Verdict up front: **that claim is false in many concrete ways.** The
approval gate (`scan_tree`) is a union of cheap lexical file-shape checks with
several structural fail-open holes. Real source resolution exists only for
Python capability scanning; everything else (all CVE fingerprints, all
TS/Rust/C/C++ capability scanning, all obfuscation entropy) is defeated by
rename, whitespace, string-splitting, non-installation, or a second lockfile.

Scope audited: `_scan.py`, `_capability.py`, `_capability_registry.py`,
`_obfuscation.py`, `_typosquat.py`, `_lifecycle.py`, `_ecosystem.py`,
`_lockfile.py`, `_source.py`, `_closedworld.py`, `_containment.py`,
`_registry.py`, CVE fingerprint catalog (`frob.strata`).

---

## (A) What vet actually checks, and how

`scan_tree(root)` (`_scan.py:736`) is the pass/fail gate. Per dependency in the
FIRST lockfile found:

- **VET001** (`_scan.py:120`): dep not in `[vet.allow]` -> ERROR. Pure config.
- **VET011 quarantine** (`_scan.py:85`): registry publish-date < cooldown ->
  ERROR; unverifiable date -> WARN. Only when `is_new and fetch`.
- **VET-JS003 typosquat** (`_scan.py:337` -> `_typosquat.py`): Damerau-Levenshtein
  distance <=1 vs a hardcoded popular-name list. Only when `is_new and fetch`.
- **Capability scan** (`_capability.py`): per-language substring needle tables
  COMPILED from `_capability_registry.DANGEROUS_OPERATIONS`. Python additionally
  gets import/alias/scope-aware resolution (T-0328/0337) and embedded-HTML/JS
  string detection (T-0244). TS/Rust/C-C++/Kotlin are raw substring only.
  Feeds VET002 (observed cap not declared -- only when allow value is a tuple)
  and VET003 (version bump adds a cap vs cached verdict).
- **VET004 obfuscation** (`_obfuscation.py`): Shannon entropy over single-quote
  string literals, Unicode bidi/zero-width scan, obfuscator.io `_0x` hex-ident
  ratio, plus decode-to-exec co-occurrence in one function body.
- **VET006 CVE fingerprint** (`_capability.py:1219`, catalog in `frob.strata`):
  13 hand-written lexical needles, raw substring, WARN only.
- **VET-JS lifecycle** (`_lifecycle.py`): package.json install-script NAMES under
  node_modules. **VET-PY001/002/003, VET-RS001/002, VET-JS004** ecosystem shape
  checks (`_ecosystem.py`). **VET005** osv-scanner subprocess (opt-in).

`closed_world_accounting`/`build_containment_report` are separate reporting
entry points, NOT wired into `scan_tree`'s pass/fail -- they do not gate.

---

## (B) Top-5 ranked defects

### 1. [HIGH] Source not installed => dependency silently APPROVED
`_scan.py:426-435` (`_scan_located_source`). If `_source._locate_source` returns
None (dependency not present in any local cache), the function appends a
`source-unavailable` signal and RETURNS with an empty capability set and **zero
violations** -- no VET002/003/004/006, no ecosystem rule. Repro: lockfile pins a
malicious pypi package that is not in `.venv`/uv-cache; `frob vet` emits VET001
(if unallowed) but once allow-listed the package's code is never scanned. Vet
"approves" code it never read. Fix: emit an explicit WARN/ERROR
`VET-SOURCE-UNAVAILABLE` finding (analogous to `VET-TIMEOUT`) so "not checked"
is never indistinguishable from "checked clean"; optionally fetch-on-consent.

### 2. [HIGH] Only the first lockfile is scanned in a polyglot repo
`_lockfile.py:34-47` (`_find_lockfile`) returns the FIRST hit in fixed order
(`uv.lock`, `package-lock.json`, `pnpm-lock.yaml`, `Cargo.lock`). Repro: a repo
with both `uv.lock` and `package-lock.json` gets only its pypi deps vetted;
every npm dependency (and its lifecycle scripts, if node_modules exists but the
npm lockfile is second) is completely unscanned by `scan_tree`. Fix: discover
and scan ALL supported lockfiles under root, not just the first.

### 3. [HIGH] CVE fingerprints + all non-Python capability needles are
rename/whitespace-evadable; fingerprints ignore even the Python resolver
Two compounding facts:
- `_scan_file_fingerprints` (`_capability.py:1219-1249`) is raw-substring ONLY;
  the T-0328 import/binding resolver is applied to capabilities but NOT to
  fingerprints. The catalog is 13 needles (`frob.strata`), several whitespace-
  sensitive: `shell=True` evaded by `shell = True`; `verify=False` by
  `verify = False`; `yaml.load(` by `from yaml import load; load(x)` or
  `yaml.load (x)`. Repro: `subprocess.run(cmd, shell = True)` -> no VET006.
- TS/Rust/C-C++ capability scan (`_capability.py:1090`, resolver gated on
  `language == "python"`) is defeated by import rename: Rust
  `use std::process::Command as Cmd; Cmd::new(x)` evades needle `Command::new(`;
  C `#define SYS system` then `SYS(cmd)`, or `void(*f)()=system; f(cmd)`, evades
  `system(`; JS `require('child_pro'+'cess')` evades the module needle.
Fix: at minimum apply the existing Python resolver path to fingerprint scanning
too; treat needle whitespace-insensitively; document TS/Rust/C aliasing as an
enforced limit rather than an implied guarantee.

### 4. [HIGH] C/C++ registry misses file I/O and most exec/net surfaces
`_capability_registry.py` c-cpp rows (confirmed via registry dump). `fs-write`
for C is `strcpy(`/`sprintf(`/`gets(` -- memory-unsafe string funcs, NOT file
writes. Actual file writes (`fopen(path,"w")`, `open()`, `write()`, `mkdir`,
`rename`, `unlink`) and reads (`open`/`read`/`mmap`, only `fread`/`fgets` are
listed) are absent. exec omits `posix_spawn`, `fexecve`, `execle`, `execvpe`,
Windows `CreateProcess`/`ShellExecute`/`WinExec`. net omits `send`/`recv`/
`sendto`/`recvfrom`/`getaddrinfo`. Repro: a `.c` dependency that opens and
writes an arbitrary file via `fopen`/`fwrite` scans as zero capabilities. Fix:
extend the c-cpp registry rows; separate the CWE-120 memory-unsafety needles
from the fs-write capability (they are mislabeled).

### 5. [HIGH/MEDIUM] Obfuscation entropy blind to triple-quoted / template /
split strings, and blind to C/C++/Kotlin files entirely
`_obfuscation.py:104` (`_iter_string_literals`) scans SINGLE-char `'`/`"`
delimiters only -- Python `"""..."""` and JS backtick `` `...` `` template
literals are never entropy-checked, so a base64 payload in a triple-quoted
Python string is invisible (`_high_entropy_strings`, line 199). `_MIN_STRING_LEN
= 24` + per-literal entropy means a blob split into <24-char concatenated
literals (`"aGVsb"+"G8gd"+...`) never fires. `_SCANNABLE_SUFFIXES`
(`_obfuscation.py:272`) excludes `.c/.h/.cpp/.hpp/.cc/.kt`, so the deterministic
Trojan-Source bidi/zero-width scan (CVE-2021-42574, demonstrated in C/C++) never
runs on C/C++/Kotlin dependency files. Fix: include triple-quoted/template
literals and all scanned-language suffixes in the obfuscation walk; consider a
whole-file entropy pass to blunt string-splitting.

---

## (C) Further gaps (still real, lower rank)

### 6. [MEDIUM] Source located by NAME, version ignored (pypi/npm)
`_source.py:43-64` (`_locate_pypi_source`) and `:68-75` (`_locate_npm_source`)
never compare `version`. Vet scans whatever is INSTALLED, not what the lockfile
PINS. Repro: lockfile pins `foo==2.0` (malicious); `.venv` still has clean
`foo==1.0`; vet scans 1.0 and approves 2.0. VET003 escalation
(`_scan.py:196`) compares on-disk artifact hashes, so a lockfile bump with a
stale install shows no diff and never escalates. Cargo locator does match
version (`_source.py:80-91`) -- pypi/npm should too.

### 7. [MEDIUM] `max_files=500` truncation fails open and is attacker-orderable
`_capability.py:1413` iterates extension-by-extension (`.py` first per dict
order) with a shared 500 budget; `_obfuscation.py:275`, `_closedworld.py:82`,
and `_artifact_hash` (`_scan.py:58`, first 500 SORTED files) do the same. A dep
padded with 500+ benign `.py` files exhausts the budget before any `.rs`/`.c`
file is read (only a WARN log). `_artifact_hash` hashing only the first 500
sorted paths means a payload in a later-sorted file leaves the verdict hash
unchanged -> VET003 blind. Fix: make truncation a hard ERROR finding, or scan
per-extension budgets, or raise/remove the cap for the hash.

### 8. [MEDIUM] setup.py install-exec detected only via `"cmdclass"` substring
`_ecosystem.py:35-51` (`_setup_py_violation`). A setup.py runs arbitrary Python
at `pip install` time regardless of `cmdclass`; a top-level `os.system(...)` in
setup.py with no cmdclass yields no VET-PY001. PEP517 build backends / pyproject
`[build-system]` hooks are not checked at all. (Capability scan does read
setup.py as `.py`, but under `allow = true` -- see #9 -- that produces no
finding.) Fix: flag ANY setup.py that reaches an exec/net/fs capability, not
just the `cmdclass` keyword; add a build-backend check.

### 9. [MEDIUM] `allow = true` disables VET002 capability enforcement entirely
`_scan.py:178-181` (`_vet002_violation`) returns None unless the allow value is
a tuple. The common `foo = true` allow form means ANY observed capability is
accepted silently forever. A compromised update of an `allow = true` dep that
adds `exec` never trips VET002 (only VET003, and only if the on-disk source hash
actually changed -- see #6/#7). Fix: document that `true` is a blanket waiver;
consider requiring an explicit capability tuple for effectful packages.

### 10. [MEDIUM] build-time Rust code beyond literal `build.rs` unscanned
`_ecosystem.py:115-136` checks only <!-- frob:waive DOC006 reason="source_dir is a variable placeholder, not a literal repo path" -->`source_dir/build.rs`. Cargo.toml can set
`build = "other.rs"` (custom build-script path); that script executes at build
time and is never capability-scanned. Fix: read Cargo.toml `build =` and scan
the named path.

### 11. [MEDIUM] Typosquat is distance-1 vs a thin list, and only new+fetch
`_typosquat.py:11` (`_MAX_DISTANCE = 1`) misses `reqessts` (dist 2), combosquats
(`python-requests`), and anything not in the small `ECOSYSTEM_POPULAR` list.
`_scan.py:406` gates the check on `is_new and fetch`, so an already-allowed dep
or a `--no-fetch` run never runs it. Fix: distance-2 with a length guard;
consider prefix/substring combosquat heuristics.

### 12. [LOW/MEDIUM] pnpm parser may silently under-report on newer formats
`_lockfile.py:144-168` parses a top-level `packages:` map with an `@version`
key regex. pnpm v9 splits `packages`/`snapshots` and changed key shapes; a
lockfile it cannot key returns zero deps -> silent empty scan (only an INFO
"parsed 0 package(s)"). yarn.lock/poetry.lock/bun are unsupported (loud Err).
Verify against a current pnpm-lock fixture.

### 13. [LOW] VET006 CVE-fingerprint match is WARN, never blocks
`_scan.py:156-171`. Even when a canonical vulnerable-usage needle fires, it
cannot fail the gate. Combined with #3's evadability, the fingerprint layer is
advisory-only in practice.

### 14. [LOW] Kotlin capability table is 2 net + 2 exec + 2 storage rows
`_capability_registry.py` kotlin rows. `Runtime.exec`/`ProcessBuilder` may be
covered but reflection, JNI (`System.loadLibrary`), file I/O, and most net are
absent; the module docstring's per-cell "excuses" acknowledge many empty cells.
Treat Kotlin coverage as nominal, not real.

---

## (D) Per-component pessimistic verdict

- **Python capability scan** (`_capability.py` resolver): the one genuinely good
  component -- import/alias/scope/copy-propagation aware. Still substring-based
  at the leaf and misses `from x import *`, dynamic `__import__`/`getattr`
  dispatch. RIGHT-ish, good enough as recall-over-precision.
- **TS/Rust/C/C++ capability scan**: FAST, not RIGHT. Rename/macro/split-string
  evades. Do not represent these as a safety guarantee.
- **C/C++ registry**: incomplete to the point of misleading (no file I/O). Not
  good enough.
- **CVE fingerprints**: 13 whitespace-brittle needles, no resolver, WARN-only.
  Cosmetic, not a control.
- **Obfuscation**: entropy blind to major literal forms + split strings; bidi
  scan blind to C/C++/Kotlin. The deterministic bidi scan (where it runs) is the
  one sound piece.
- **Typosquat**: thin list, distance-1, gated on fetch. Weak.
- **Lockfile/source location**: first-lockfile-only and version-blind are the
  two structural correctness holes that undermine everything downstream.
- **scan_tree fail-open surfaces**: source-unavailable, timeout (WARN),
  max_files truncation (WARN) -- all "not checked" outcomes that the report does
  not clearly separate from "checked clean" except VET-TIMEOUT.

## (E) Verified-correct / deliberately skimmed
- VET-TIMEOUT handling (`_scan.py:591`) is honest: timeout -> WARN verdict, never
  a silent drop; the `shutdown(wait=False)` note is accurate.
- Containment `unverified` vs `unmodeled` distinction (`_containment.py`) is
  sound and does not conflate an NVD outage with "safe".
- Self-match exclusion (`is_self_pattern_path`, T-0253) reasoning holds: gated on
  scanned-tree root identity, not path suffix alone; not an evasion vector for a
  real dependency scan.
- Comment-span filtering (T-0209) and the napi/compile boundary checks are
  correct for their stated FP class.
- Did NOT deeply audit: `_nvd.py`/`_osv.py` network parsers, `_cache.py` sqlite
  concurrency (docstring already discloses last-writer-wins under `jobs>1`),
  `_allow.py` config parsing, and the exact popular-name list contents. The
  `jobs>1` shared-cache race is disclosed, not silent -- left as accepted.
