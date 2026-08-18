"""Already-produced JUnit XML test-report collection
(`build/test-results/test/TEST-*.xml`), one gradle project directory per
discovered `build.gradle.kts`/`build.gradle` that declares a kotlin plugin
-- the kotlin/JVM-toolchain analogue of `_collect_cpp.py`'s ctest
collector (T-2409). Gradle's own test-listing story requires either a full
build or a running daemon (there is no equivalent of `cargo test --
--list`/`vitest list --json` that enumerates JVM test methods without
compiling and running them) -- too heavy for a collection pass, so this
collector applies `_ctest_build_dir`'s own restraint (`_collect_cpp.py`):
read a report that ALREADY exists, never configure or run a build here.
Split out (T-1074-style) as its own self-contained per-language collector;
`_collect.py` re-imports every name here so `from frob.testing._collect
import ...` call sites keep resolving unchanged."""
# frob:ticket T-2409

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from xml.etree import ElementTree

from typani import Ok
from typani.result import Result

from frob.excludes import load_exclude_globs
from frob.logging import get_logger
from frob.testing._collect_shared import (
    _KOTLIN_CACHE_REL,
    _load_cache,
    _prune_dirnames,
    _store_cache,
)
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError

_log = get_logger(__name__)

_GRADLE_BUILD_FILENAMES = ("build.gradle.kts", "build.gradle")
_GRADLE_REPORT_RELDIR = Path("build") / "test-results" / "test"

# `plugins { kotlin("jvm") ... }` (kts explicit-alias form),
# `id("org.jetbrains.kotlin...")` (kts full-id form), `apply plugin:
# 'kotlin'`/`id 'kotlin'` (groovy short-id form, gradle's own alias for
# `org.jetbrains.kotlin.jvm`), or `id 'org.jetbrains.kotlin...'` (groovy
# full-id form) -- the handful of conventional spellings a gradle build
# file uses to declare the kotlin plugin. A plain substring/regex scan,
# not a groovy/kts interpreter, mirroring `_package_json_uses_vitest`'s
# own "declares the dependency" shape (never a build-tool invocation
# just to answer "is this a kotlin project").
_KOTLIN_PLUGIN_RE = re.compile(
    r"""kotlin\s*\(\s*["']jvm["']"""  # kotlin("jvm")
    r"""|org\.jetbrains\.kotlin"""  # id("org.jetbrains.kotlin...")
    r"""|(?:apply\s+plugin\s*:|\bid\b)\s*['"]kotlin['"]"""  # short-id groovy form
)


def _gradle_build_uses_kotlin(build_path: Path) -> bool:
    """True if `build_path` (a `build.gradle`/`build.gradle.kts`) declares
    the kotlin plugin -- see `_KOTLIN_PLUGIN_RE`."""
    try:
        text = build_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning(
            "_find_kotlin_gradle_projects: could not read %s: %s", build_path, exc
        )
        return False
    return _KOTLIN_PLUGIN_RE.search(text) is not None


def _find_kotlin_gradle_projects(root: Path) -> list[Path]:
    """Directories holding a `build.gradle(.kts)` that declares the kotlin
    plugin, exclusions pruned (mirrors `_collect_rust._find_crates`'s
    Cargo.toml walk)."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    # frob:waive WALK001 reason="needs per-directory exclude pruning the file-only iter_files/walk_pruned API cannot express; already prunes via _prune_dirnames using frob.excludes primitives"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _prune_dirnames(Path(dirpath), root, dirnames, exclude_globs)
        for name in _GRADLE_BUILD_FILENAMES:
            if name in filenames and _gradle_build_uses_kotlin(Path(dirpath) / name):
                found.append(Path(dirpath))
                break
    return sorted(found)


def _junit_report_dir(project_dir: Path) -> Path | None:
    """`project_dir`'s conventional gradle JUnit report directory
    (`build/test-results/test/`) if it already holds at least one
    `TEST-*.xml`, else `None`. Deliberately never runs `gradle`/`./gradlew`
    itself to produce one -- mirrors `_ctest_build_dir`'s "already
    configured/built, never build here" restraint (T-0587's own rule,
    applied to the heavier JVM toolchain)."""
    candidate = project_dir / _GRADLE_REPORT_RELDIR
    if not candidate.is_dir():
        return None
    if not any(candidate.glob("TEST-*.xml")):
        return None
    return candidate


def _find_junit_report_dirs(root: Path) -> list[Path]:
    """Every already-produced gradle JUnit report directory discovered
    under `root`."""
    report_dirs: list[Path] = []
    for project_dir in _find_kotlin_gradle_projects(root):
        report_dir = _junit_report_dir(project_dir)
        if report_dir is not None:
            report_dirs.append(report_dir)
    return sorted(report_dirs)


def _parse_junit_xml(xml_path: Path) -> list[tuple[str, str]]:
    """Every `(classname, name)` pair from one `TEST-*.xml` JUnit report
    (the surefire/gradle-standard `<testsuite><testcase classname=...
    name=.../></testsuite>` shape). Malformed XML is skipped with a
    warning, never fatal -- mirrors `_parse_vitest_json`'s "one bad entry
    does not fail the whole collection" posture."""
    try:
        tree = ElementTree.parse(xml_path)
    except ElementTree.ParseError as exc:
        _log.warning(
            "collect_kotlin_tests: unparseable JUnit report %s: %s", xml_path, exc
        )
        return []
    pairs: list[tuple[str, str]] = []
    for testcase in tree.getroot().iter("testcase"):
        classname = testcase.get("classname")
        name = testcase.get("name")
        if classname and name:
            pairs.append((classname, name))
        else:
            _log.warning(
                "collect_kotlin_tests: skipping malformed <testcase> in %s: %r",
                xml_path,
                testcase.attrib,
            )
    return pairs


def _find_kotlin_source(project_dir: Path, simple_class_name: str) -> Path | None:
    """The single kotlin/java source file under `project_dir`'s
    conventional test source roots (`src/test/kotlin`, `src/test/java`)
    named `<simple_class_name>.{kt,java}`, or `None` if zero or more than
    one candidate exists -- mirrors `_cpp_test_source`'s "unambiguous or
    nothing" posture (a wrong guess is worse than an honest fallback)."""
    candidates: list[Path] = []
    for src_root in ("src/test/kotlin", "src/test/java"):
        base = project_dir / src_root
        if not base.is_dir():
            continue
        candidates.extend(base.rglob(f"{simple_class_name}.kt"))
        candidates.extend(base.rglob(f"{simple_class_name}.java"))
    if len(candidates) != 1:
        return None
    return candidates[0]


def _kotlin_node_id(root: Path, project_dir: Path, classname: str, name: str) -> str:
    """`source::classname.name`, source-mapped where `_find_kotlin_source`
    resolves an unambiguous test source file, loudly report-dir-anchored
    otherwise (T-2409; mirrors `_cpp_node_id`/`_collect_cpp_build_dir`'s
    fallback shape -- `classname` is JUnit's fully-qualified dotted name,
    kept dotted rather than `::`-normalized like `_cpp_node_id` does,
    since a kotlin/JUnit qualname is conventionally read dotted end to
    end, not split at a class/method boundary the way a gtest
    `TestSuite.TestCase` name is)."""
    simple_name = classname.rsplit(".", 1)[-1]
    source = _find_kotlin_source(project_dir, simple_name)
    if source is not None:
        rel = source.relative_to(root).as_posix()
        return f"{rel}::{classname}.{name}"
    rel_project = project_dir.relative_to(root).as_posix()
    return f"{rel_project}::{classname}.{name}"


def _kotlin_content_key(root: Path, report_dirs: list[Path]) -> str:
    """Sha256 over every discovered `TEST-*.xml` report's content -- the
    cache key. A report only changes after a real gradle test run, so this
    naturally invalidates whenever fresher results appear on disk."""
    hasher = hashlib.sha256()
    all_files: list[Path] = []
    for report_dir in report_dirs:
        all_files.extend(report_dir.glob("TEST-*.xml"))
    for path in sorted(set(all_files)):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_kotlin_tests: could not read %s: %s", path, exc)
            continue
        rel = path.relative_to(root).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


# frob:doc docs/modules/testing.md#public-api
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_parses_and_ca\
# ches kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_groovy_plugin\
# _form kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_no_projects_i\
# s_ok_empty kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_unreported_pr\
# oject_is_ok_empty kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_falls_back_wh\
# en_source_unresolvable kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_skips_malform\
# ed_report kind="unit"
# frob:tests \
# tests/test_testing.py::TestCollectKotlinTests.test_collect_kotlin_tests_non_kotlin_gr\
# adle_project_is_ok_empty kind="unit"
def collect_kotlin_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """Every JUnit `(classname, name)` pair from already-produced gradle
    test reports under `root` (T-2409), one project per discovered
    kotlin-plugin `build.gradle(.kts)`. Cached on the discovered reports'
    own content hash. Always `Ok` (never `Err`) -- a repo with no gradle
    project, or one that has never run its tests, degrades to an empty
    result with a debug log, the same "missing toolchain artifact must not
    fail collection for every OTHER language" posture `collect_ts_tests`/
    `collect_cpp_tests` apply to a missing `npx`/`ctest` binary, here
    applied to a missing report instead of a missing binary since this
    collector never spawns gradle at all."""
    report_dirs = _find_junit_report_dirs(root)
    key = _kotlin_content_key(root, report_dirs)
    cache_path = root / _KOTLIN_CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_kotlin_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    node_ids: set[str] = set()
    for report_dir in report_dirs:
        project_dir = report_dir.parents[2]  # build/test-results/test -> project root
        for xml_path in sorted(report_dir.glob("TEST-*.xml")):
            for classname, name in _parse_junit_xml(xml_path):
                node_ids.add(_kotlin_node_id(root, project_dir, classname, name))

    if not report_dirs:
        _log.debug(
            "collect_kotlin_tests: no gradle project with an existing JUnit "
            "report found under %s",
            root,
        )

    frozen = frozenset(node_ids)
    _store_cache(cache_path, key, frozen)
    _log.info("collect_kotlin_tests: collected %d node id(s)", len(frozen))
    return Ok(CollectedTests(node_ids=frozen))


__all__ = [
    "collect_kotlin_tests",
]
