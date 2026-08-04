"""The (capability_kind x language) coverage matrix: `CAPABILITY_MATRIX_
EXCUSES`, `NO_CAPABILITY_MODULES`, and the `capability_matrix`/
`_unexcused_empty_cells`/`_validate_registry_kinds` computation over the
`DANGEROUS_OPERATIONS` table -- split out (T-1420) as its own concern,
distinct from the tables it reasons over."""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.vet._capability_registry._dangerous_ops_other import _OTHER_OPERATIONS
from frob.vet._capability_registry._dangerous_ops_python import _PYTHON_OPERATIONS
from frob.vet._capability_registry._kinds import CAPABILITY_KINDS, LANGUAGES
from frob.vet._capability_registry._schemas import _DangerousOperation, _MatrixExcuse

_log = get_logger(__name__)

# frob:doc docs/modules/vet.md#public-api
# frob:doc docs/guides/extending/capability-registry.md#capability-registry
# frob:ticket T-0158
#: `DANGEROUS_OPERATIONS`'s own re-assembly from its per-language slices
#: (T-1420 split) -- the matrix functions below need the whole table, not
#: either half alone.
DANGEROUS_OPERATIONS: tuple[_DangerousOperation, ...] = (
    _PYTHON_OPERATIONS + _OTHER_OPERATIONS
)

# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
#: every (kind, language) cell with NO `_DangerousOperation` entry above
#: gets a SPECIFIC excuse naming the missing idiom -- the blanket C/C++
#: "honestly-empty" exemption is retired (T-0158). An unexcused empty cell
#: is a `capability_matrix()` gate failure.
CAPABILITY_MATRIX_EXCUSES: tuple[_MatrixExcuse, ...] = (
    _MatrixExcuse(
        capability_kind="eval",
        language="c-cpp",
        reason="no idiomatic C/C++ 'evaluate a string as code' primitive in "
        "the standard library; dlopen (ffi) is the closest native-code-"
        "loading analog and is already patterned separately",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="c-cpp",
        reason="getenv()/setenv() reads are pervasive, unprefixed C identifiers "
        "(`getenv(` collides with countless unrelated tokens under a plain-"
        "substring scanner) -- tracked as a real gap, not silently dropped; "
        "see docs/modules/vet.md 'Honest limits'",
    ),
    # T-0771 (net/env mode split): the coarse "env" excuse above is a
    # collision problem inherent to the bare identifier `getenv`/`setenv`,
    # not something a mode split fixes -- both the read side (getenv) and
    # the write side (setenv/putenv) share the exact same unprefixed-
    # identifier hazard, so each precise mode gets its own excuse citing
    # the same root cause rather than silently inheriting the old one.
    _MatrixExcuse(
        capability_kind="env-read",
        language="c-cpp",
        reason="getenv() is a pervasive, unprefixed C identifier (collides "
        "with countless unrelated tokens under a plain-substring scanner) "
        "-- tracked as a real gap, not silently dropped; see "
        "docs/modules/vet.md 'Honest limits'",
    ),
    _MatrixExcuse(
        capability_kind="env-write",
        language="c-cpp",
        reason="setenv()/putenv() are pervasive, unprefixed C identifiers "
        "(collide with countless unrelated tokens under a plain-substring "
        "scanner) -- tracked as a real gap, not silently dropped; see "
        "docs/modules/vet.md 'Honest limits'",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="c-cpp",
        reason="no C/C++ packaging-install-hook idiom analogous to setuptools "
        "cmdclass; native builds hook via Makefile/CMake, outside this "
        "scanner's per-source-file text model",
    ),
    # T-0771: the JVM/kotlin System.getenv() view is unmodifiable -- there
    # is no supported API that mutates the CALLING process's own
    # environment (ProcessBuilder.environment() mutates a not-yet-spawned
    # CHILD's environment map, a distinct exec-adjacent concept, not a
    # self-mutation), so kotlin has no dominant env-write idiom to pattern.
    _MatrixExcuse(
        capability_kind="env-write",
        language="kotlin",
        reason="System.getenv() returns an unmodifiable view; the JVM has "
        "no supported API to mutate the calling process's own environment "
        "(ProcessBuilder.environment() mutates a child process's "
        "environment map instead, a distinct exec-adjacent concept)",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="c-cpp",
        reason="no C/C++ standard-library DOM/HTML-rendering concept; "
        "browser-only capability",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="c-cpp",
        reason="no single dominant C/C++ DB-API string-interpolation idiom "
        "(libpq/sqlite3 C APIs use bound parameters as the common path); "
        "tracked as a gap for the next C SQL-client survey, not claimed covered",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="c-cpp",
        reason="no single dominant C/C++ URL-fetch idiom in the standard "
        "library (libcurl is third-party); covered via the closed-world "
        "vetted-library path for libcurl-linked dependencies, not a hand "
        "pattern here",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="c-cpp",
        reason="no C/C++ standard-library object-deserialization primitive "
        "analogous to pickle/marshal; unsafe deserialization in C/C++ is a "
        "buffer-parsing bug, already covered by the strcpy/sprintf/gets "
        "fs-write-bucketed entries",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="c-cpp",
        reason="no C/C++ standard-library browser-storage concept; browser-"
        "only capability",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="typescript",
        reason="no idiomatic npm packaging-install-hook literal analogous to "
        "setuptools cmdclass; npm lifecycle scripts (preinstall/postinstall) "
        "are declared in package.json data, not source text this scanner "
        "reads -- tracked as a real gap, not silently dropped",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="typescript",
        reason="no single dominant raw-SQL-string-interpolation idiom "
        "shared across node DB clients (pg/mysql2/knex each differ); ORM "
        "query-builder usage is the common path and is not itself dangerous "
        "-- tracked as a gap for a per-client survey",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="typescript",
        reason="JSON.parse is the dominant deserialization primitive and is "
        "not itself unsafe (no code execution on parse, unlike pickle); "
        "prototype-pollution-adjacent merge utilities are a distinct, "
        "narrower gap tracked separately, not this kind",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="rust",
        reason="idiomatic Rust DB clients (sqlx/diesel) are compile-time "
        "parameterized by design; no dominant raw-string-interpolation "
        "idiom exists to pattern",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="rust",
        reason="serde is the dominant (de)serialization crate and is type-"
        "directed, not string-eval-based; unsafe deserialization in Rust is "
        "a `mem::transmute`/unsafe-FFI concern, already patterned under eval/"
        "ffi",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="rust",
        reason="no single dominant Rust templating-crate raw-HTML-injection "
        "idiom surveyed yet (askama/maud/tera each differ); tracked as a "
        "follow-up per-crate survey, not claimed covered",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="rust",
        reason="no Rust standard-library browser-storage concept; browser-"
        "only capability (wasm-bindgen web-sys bindings are a follow-up "
        "survey item, not covered here)",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="rust",
        reason="no Rust packaging-install-hook idiom analogous to setuptools "
        "cmdclass; cargo build.rs is itself already the exec-capability "
        "surface (patterned separately as build.rs -> Command::new)",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="python",
        reason="no Python standard-library browser-storage concept; browser-"
        "only capability",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="rust",
        reason="reqwest::/hyper:: are already patterned under net (fetching a "
        "URL IS the SSRF-relevant surface for those crates); no separate "
        "fetch_url-specific idiom distinct from the net entries exists in "
        "Rust's ecosystem to pattern independently",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="python",
        reason="`fs` is `_effects.py::_KIND_MAP`'s tier-2-normalized alias "
        "of the scanner's `fs-write` kind (net/fs-write/exec are "
        "normalized to net/fs/exec for `may` declarations); every actual "
        "detection pattern lives under `fs-write`, this is the same "
        "cell under its normalized name, not a separate detection surface",
    ),
    # T-0771: the bare `net` kind is fully retired from scanner output --
    # every `_DangerousOperation` that used to carry it now carries the
    # precise `net-connect`/`net-listen` split (this ticket's needle work,
    # mirroring `fs`'s own bare-kind retirement above). `net` stays in
    # `CAPABILITY_KINDS` ONLY because it is still a legal coarse `may
    # "net"` declaration spelling (frob.vet._capability_modes mandate
    # point 2) -- these five excuses are the `net`-language cell's
    # equivalent of the `fs`-language excuses just above, same reasoning.
    _MatrixExcuse(
        capability_kind="net",
        language="python",
        reason="`net` has no scanner detection pattern of its own any "
        "more -- every prior python/net entry was reclassified to the "
        "precise net-connect/net-listen split (T-0771); `net` survives "
        'only as a legal coarse `may "net"` declaration spelling',
    ),
    _MatrixExcuse(
        capability_kind="net",
        language="typescript",
        reason="see the python/net excuse above -- same T-0771 reclassify, "
        "no separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="net",
        language="rust",
        reason="see the python/net excuse above -- same T-0771 reclassify, "
        "no separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="net",
        language="c-cpp",
        reason="see the python/net excuse above -- same T-0771 reclassify, "
        "no separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="net",
        language="kotlin",
        reason="see the python/net excuse above -- same T-0771 reclassify, "
        "no separate detection surface",
    ),
    # T-0771: `net.connect`/`net.listen` (dotted, the tier-2 `_KIND_MAP`-
    # normalized spelling `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES`
    # excuses THREAT005 against) are a DIFFERENT registered kind from the
    # raw scanner's `net-connect`/`net-listen` (hyphenated, patterned
    # above) -- see the `CAPABILITY_KINDS` comment for why both exist.
    # Nothing in `DANGEROUS_OPERATIONS` ever emits the dotted spelling
    # directly (only `_effects.py::_KIND_MAP` produces it, downstream of
    # the scanner), so every language cell for both dotted kinds is
    # excused, not patterned -- there is no needle to write.
    _MatrixExcuse(
        capability_kind="net.connect",
        language="python",
        reason="dotted mode-qualified spelling, never emitted directly by "
        "the scanner (only frob.strata._effects.py::_KIND_MAP produces "
        "it from the raw net-connect scanner kind, already patterned "
        "above) -- registered only so THREAT005's BenignCapability excuse "
        "kind is a known kind, not a separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="net.connect",
        language="typescript",
        reason="see the python/net.connect excuse above",
    ),
    _MatrixExcuse(
        capability_kind="net.connect",
        language="rust",
        reason="see the python/net.connect excuse above",
    ),
    _MatrixExcuse(
        capability_kind="net.connect",
        language="c-cpp",
        reason="see the python/net.connect excuse above",
    ),
    _MatrixExcuse(
        capability_kind="net.connect",
        language="kotlin",
        reason="see the python/net.connect excuse above",
    ),
    _MatrixExcuse(
        capability_kind="net.listen",
        language="python",
        reason="see the python/net.connect excuse above, listen-side",
    ),
    _MatrixExcuse(
        capability_kind="net.listen",
        language="typescript",
        reason="see the python/net.connect excuse above, listen-side",
    ),
    _MatrixExcuse(
        capability_kind="net.listen",
        language="rust",
        reason="see the python/net.connect excuse above, listen-side",
    ),
    _MatrixExcuse(
        capability_kind="net.listen",
        language="c-cpp",
        reason="see the python/net.connect excuse above, listen-side",
    ),
    _MatrixExcuse(
        capability_kind="net.listen",
        language="kotlin",
        reason="see the python/net.connect excuse above, listen-side",
    ),
    # T-0771: bare `env` was fully reclassified to env-read/env-write for
    # every language. T-1439: the last two python entries that still
    # emitted bare `env` (sys.exit/os._exit, signal.signal -- never
    # actually environment-variable access, a pre-existing kind-naming
    # mismatch T-0771's own Done report flagged unfixed) moved to the new
    # `process-control` kind below, so `env` is now excused for EVERY
    # language including python -- it survives only as a legal coarse
    # `may "env"` declaration spelling, discharged by either env-read or
    # env-write per `expand_declared_kind`.
    _MatrixExcuse(
        capability_kind="env",
        language="python",
        reason="the last two bare-env registry entries (sys.exit/os._exit, "
        "signal.signal) were reclassified to `process-control` (T-1439) -- "
        "they were never real environment-variable access; `env` survives "
        'only as a legal coarse `may "env"` declaration spelling',
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="typescript",
        reason="every prior typescript/env entry (process.env) was "
        "reclassified to the precise env-read/env-write split (T-0771); "
        '`env` survives only as a legal coarse `may "env"` declaration '
        "spelling",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="rust",
        reason="see the typescript/env excuse above -- same T-0771 "
        "reclassify, no separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="kotlin",
        reason="no bare-env entry was ever patterned for kotlin; the new "
        "System.getenv() entry (T-0771) is precise env-read from the "
        "start, so this cell was never a reclassification, just never "
        "patterned coarse",
    ),
    # T-1439: `process-control` is a NEW kind -- python patterns it
    # (sys.exit/os._exit, signal.signal, reclassified out of bare env
    # above); no per-language survey of the equivalent idioms (process.
    # exit/kill in TS, std::process::exit/signal crates in rust, exit(3)/
    # signal(2) in C/C++, System.exit/Runtime.exit in kotlin) has been
    # done yet, so every other language cell is excused as a tracked gap
    # rather than guessed at, same shape as the kotlin/env excuse above.
    _MatrixExcuse(
        capability_kind="process-control",
        language="typescript",
        reason="no per-language survey of process.exit/kill-equivalent "
        "idioms has been done yet (T-1439 introduced the kind reclassifying "
        "python-only entries); tracked as a follow-up rather than guessed "
        "at here",
    ),
    _MatrixExcuse(
        capability_kind="process-control",
        language="rust",
        reason="see the typescript/process-control excuse above -- same "
        "un-surveyed gap, std::process::exit/signal-crate idioms",
    ),
    _MatrixExcuse(
        capability_kind="process-control",
        language="c-cpp",
        reason="see the typescript/process-control excuse above -- same "
        "un-surveyed gap, exit(3)/_exit(2)/signal(2) idioms",
    ),
    _MatrixExcuse(
        capability_kind="process-control",
        language="kotlin",
        reason="see the typescript/process-control excuse above -- same "
        "un-surveyed gap, System.exit/Runtime.exit/JVM signal-handling "
        "idioms",
    ),
    # T-1075: `env.read`/`env.write` (dotted, the tier-2 `_KIND_MAP`-
    # normalized spelling `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES`
    # excuses THREAT005 against) are a DIFFERENT registered kind from the
    # raw scanner's `env-read`/`env-write` (hyphenated, patterned above) --
    # same shape as `net.connect`/`net.listen` above. Nothing in
    # `DANGEROUS_OPERATIONS` ever emits the dotted spelling directly (only
    # `_effects.py::_KIND_MAP` produces it, downstream of the scanner), so
    # every language cell for both dotted kinds is excused, not patterned.
    _MatrixExcuse(
        capability_kind="env.read",
        language="python",
        reason="dotted mode-qualified spelling, never emitted directly by "
        "the scanner (only frob.strata._effects.py::_KIND_MAP produces "
        "it from the raw env-read scanner kind, already patterned above) "
        "-- registered only so THREAT005's BenignCapability excuse kind "
        "is a known kind, not a separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="env.read",
        language="typescript",
        reason="see the python/env.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="env.read",
        language="rust",
        reason="see the python/env.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="env.read",
        language="c-cpp",
        reason="see the python/env.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="env.read",
        language="kotlin",
        reason="see the python/env.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="env.write",
        language="python",
        reason="see the python/env.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="env.write",
        language="typescript",
        reason="see the python/env.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="env.write",
        language="rust",
        reason="see the python/env.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="env.write",
        language="c-cpp",
        reason="see the python/env.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="env.write",
        language="kotlin",
        reason="see the python/env.read excuse above, write-side",
    ),
    # T-1252: `fs.read`/`fs.write` (dotted, the tier-2 `_KIND_MAP`-
    # normalized spelling `frob.strata._threat.DEFAULT_BENIGN_CAPABILITIES`
    # excuses THREAT005 against) are a DIFFERENT registered kind from the
    # raw scanner's `fs-read`/`fs-write` (hyphenated, patterned above) --
    # same shape as `net.connect`/`net.listen` and `env.read`/`env.write`
    # above. Nothing in `DANGEROUS_OPERATIONS` ever emits the dotted
    # spelling directly (only `_effects.py::_KIND_MAP` produces it,
    # downstream of the scanner), so every language cell for both dotted
    # kinds is excused, not patterned.
    _MatrixExcuse(
        capability_kind="fs.read",
        language="python",
        reason="dotted mode-qualified spelling, never emitted directly by "
        "the scanner (only frob.strata._effects.py::_KIND_MAP produces "
        "it from the raw fs-read scanner kind, already patterned above) "
        "-- registered only so THREAT005's BenignCapability excuse kind "
        "is a known kind, not a separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs.read",
        language="typescript",
        reason="see the python/fs.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="fs.read",
        language="rust",
        reason="see the python/fs.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="fs.read",
        language="c-cpp",
        reason="see the python/fs.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="fs.read",
        language="kotlin",
        reason="see the python/fs.read excuse above",
    ),
    _MatrixExcuse(
        capability_kind="fs.write",
        language="python",
        reason="see the python/fs.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="fs.write",
        language="typescript",
        reason="see the python/fs.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="fs.write",
        language="rust",
        reason="see the python/fs.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="fs.write",
        language="c-cpp",
        reason="see the python/fs.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="fs.write",
        language="kotlin",
        reason="see the python/fs.read excuse above, write-side",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="typescript",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="rust",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="c-cpp",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    # -- kotlin (T-0170): every cell NOT patterned above, excused honestly --
    _MatrixExcuse(
        capability_kind="eval",
        language="kotlin",
        reason="no idiomatic string-eval/dynamic-code-execution primitive in "
        "common Android/Kotlin use; the closest analog (reflection-based "
        "class loading) is a distinct, narrower ffi-adjacent gap tracked "
        "separately, not surveyed as a dominant idiom here",
    ),
    _MatrixExcuse(
        capability_kind="fs-write",
        language="kotlin",
        reason="Kotlin's filesystem access goes through the same java.io/"
        "java.nio surface as any JVM language, with no single dominant "
        "write idiom distinct enough to needle cheaply without a wider "
        "per-API survey; tracked as a follow-up, not guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="kotlin",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface (and fs-write itself is excused for "
        "kotlin, see above)",
    ),
    _MatrixExcuse(
        capability_kind="fs-read",
        language="kotlin",
        reason="same java.io/java.nio survey gap as fs-write above -- no "
        "single dominant read idiom surveyed yet",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="kotlin",
        reason="System.getenv() is the obvious JVM idiom but was not part of "
        "T-0170's per-cell survey list (net/exec/client_storage only); "
        "tracked as a follow-up rather than guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="ffi",
        language="kotlin",
        reason="JNI (System.loadLibrary/native methods) is the JVM ffi "
        "idiom but was not part of T-0170's per-cell survey list; tracked "
        "as a follow-up rather than guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="kotlin",
        reason="no Kotlin/Android packaging-install-hook idiom analogous to "
        "setuptools cmdclass; Gradle build-script tasks are the closest "
        "analog and are already trusted-author build tooling, not a "
        "runtime dependency capability",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="kotlin",
        reason="Android has no dominant raw-HTML-injection idiom analogous "
        "to a web templating engine; WebView.loadData/loadDataWithBaseURL "
        "is the closest analog and is a distinct, narrower gap not yet "
        "surveyed",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="kotlin",
        reason="Room (already patterned under client_storage) is the "
        "dominant Android SQL surface and is compile-time/annotation "
        "checked by design; raw SQLiteDatabase.rawQuery string "
        "interpolation is a distinct, narrower gap not yet surveyed",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="kotlin",
        reason="OkHttp/HttpURLConnection are already patterned under net "
        "(fetching a URL IS the SSRF-relevant surface for those clients); "
        "no separate fetch_url-specific idiom distinct from the net "
        "entries exists to pattern independently",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="kotlin",
        reason="Gson/Moshi/kotlinx.serialization are the dominant "
        "(de)serialization libraries and are type-directed, not "
        "string-eval-based; a per-library survey is deferred as a "
        "follow-up rather than guessed at here",
    ),
    # T-0244: `embedded_code` is emitted structurally (a tree-sitter STRING
    # node's size + HTML/JS-signal heuristic in `frob.vet._capability`),
    # never from a per-language `DANGEROUS_OPERATIONS` needle -- every
    # language cell is excused the same way, symmetrically, rather than
    # patterned per language.
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="python",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="typescript",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="rust",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="c-cpp",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="kotlin",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
)


# T-0524: frob:doc removed -- capability_matrix (public, below) returns
# this type and already carries the same docs/modules/vet.md#public-api
# anchor (COV007).
class _MatrixCell(BaseModel):
    """One (capability_kind, language) matrix cell's verdict: `patterned`
    (has >=1 `_DangerousOperation`), `excused` (has a `_MatrixExcuse`), or
    neither -- the last case is a gate failure (T-0158)."""

    model_config = ConfigDict(frozen=True)

    capability_kind: str
    language: str
    patterned: bool
    excused: bool
    operation_count: int
    excuse_reason: str | None = None


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
def capability_matrix() -> tuple[_MatrixCell, ...]:
    """The full (kind x language) matrix: every cell is `patterned`,
    `excused`, or -- if neither -- a gate failure the caller must surface.
    Deterministic order: kind-major, then `LANGUAGES` order."""
    excuse_by_key = {
        (e.capability_kind, e.language): e for e in CAPABILITY_MATRIX_EXCUSES
    }
    counts: dict[tuple[str, str], int] = {}
    for entry in DANGEROUS_OPERATIONS:
        key = (entry.capability_kind, entry.language)
        counts[key] = counts.get(key, 0) + 1

    cells: list[_MatrixCell] = []
    for kind in CAPABILITY_KINDS:
        for language in LANGUAGES:
            key = (kind, language)
            operation_count = counts.get(key, 0)
            excuse = excuse_by_key.get(key)
            cells.append(
                _MatrixCell(
                    capability_kind=kind,
                    language=language,
                    patterned=operation_count > 0,
                    excused=excuse is not None,
                    operation_count=operation_count,
                    excuse_reason=excuse.reason if excuse else None,
                )
            )
    return tuple(cells)


# T-0524: frob:doc removed -- calls capability_matrix (public), which
# already carries the same docs/modules/vet.md#public-api anchor (COV007).
# frob:ticket T-0158
# frob:ticket T-0565
# frob:tests tests/test_capability_registry.py::TestMatrixExhaustiveness.test_no_unexcused_empty_cells  # noqa: E501
def _unexcused_empty_cells() -> tuple[_MatrixCell, ...]:
    """Every matrix cell with zero patterns and zero excuse -- the T-0158
    gate failure condition. Empty tuple = the exhaustiveness claim holds."""
    return tuple(c for c in capability_matrix() if not c.patterned and not c.excused)


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="a standalone drift-lock helper with no public wrapper -- \
# called directly by its own tests (T-0524), not through any other public entrypoint \
# in this module, so the private symbol genuinely is the documented contract here"
# frob:ticket T-0158
# frob:ticket T-0565
# frob:tests tests/test_capability_registry.py::TestValidateRegistryKinds.test_known_kinds_pass  # noqa: E501
def _validate_registry_kinds(external_kinds: frozenset[str]) -> tuple[str, ...]:
    """Drift-lock (extends T-0150): every kind `external_kinds` names (e.g.
    every `WeaknessEntry.capability_kind`, every `may` atom kind observed
    in strata design files) must be a member of `CAPABILITY_KINDS`. Returns
    the offending kinds -- empty tuple means clean."""
    known = frozenset(CAPABILITY_KINDS)
    offenders = tuple(sorted(external_kinds - known))
    if offenders:
        _log.error(
            "capability registry: %d kind(s) used but not registered: %s",
            len(offenders),
            offenders,
        )
    return offenders


# frob:doc docs/modules/vet.md#public-api
#: Python stdlib modules explicitly known to have NO effectful (process/fs/
#: net/env/dynamic-code) surface -- listed so "we curated exhaustively" is
#: checkable rather than "we sampled a few and moved on" (T-0158 addendum
#: 2). Not exhaustive over the ENTIRE stdlib (hundreds of modules); this is
#: the common/likely-imported subset a dependency's source is plausible to
#: use, curated alongside the effectful modules above. Extending this list
#: is always safe (adding a no-capability entry never masks a real finding
#: -- the module's actual text is still scanned by `DANGEROUS_OPERATIONS`
#: needles regardless of this list; this is documentation of intent, not a
#: skip-list).

NO_CAPABILITY_MODULES: tuple[str, ...] = (
    "collections",
    "itertools",
    "functools",
    "dataclasses",
    "typing",
    "enum",
    "abc",
    "math",
    "statistics",
    "decimal",
    "fractions",
    "random",
    "string",
    "re",
    "textwrap",
    "unicodedata",
    "difflib",
    "json",
    "csv",
    "datetime",
    "calendar",
    "zoneinfo",
    "copy",
    "pprint",
    "reprlib",
    "numbers",
    "array",
    "heapq",
    "bisect",
    "weakref",
    "types",
    "operator",
    "contextlib",
    "graphlib",
    "warnings",
    "traceback",
    "unittest",
    "doctest",
    "logging",
)
