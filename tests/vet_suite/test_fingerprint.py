from pathlib import Path
from unittest import mock

from frob.vet._models import Dependency
from tests.conftest import _make_fake_frob_repo_root  # noqa: F401 -- T-3596


# frob:ticket T-0910
# frob:ticket T-1636
class TestFingerprintScan:
    """T-0153: `_scan_file_fingerprints` -- the CVE-fingerprint sibling of
    `_scan_file_operations`, joined to `frob.strata.CVE_FINGERPRINTS`."""

    def test_matches_a_known_fingerprint(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("data = yaml.load(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    # frob:ticket T-1636
    def test_yaml_load_with_explicit_loader_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_scan.py::_yaml_load_call_lacks_explicit_loader \
        # kind="integration"
        # T-1636: `_yaml_load_call_lacks_explicit_loader` is invoked only via
        # `_capability_scan.py`'s _FINGERPRINT_REFINEMENTS dispatch table (a function
        # reference stored by name, looked up and called indirectly), never a
        # literal call token a static call-graph can see -- same class as COV006's
        # own documented argparse-dispatch-table rescue.
        # frob:ticket T-1329
        # An explicit Loader= is FP-DESERIALIZE-YAML-001's own prescribed
        # remediation (CVE-2017-18342 is the loader-LESS default) -- the
        # substring needle alone fired on frob's own remediated
        # tickets/_store.py calls after T-1206.
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "data = yaml.load(raw_bytes, Loader=yaml.CSafeLoader)\n"
            "more = yaml.load(\n"
            "    fence.group(1),\n"
            "    Loader=_yaml_loader(),\n"
            ")\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    # frob:ticket T-1636
    def test_one_bare_yaml_load_among_remediated_calls_still_flags(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_scan.py::_yaml_load_call_lacks_explicit_loader \
        # kind="integration"
        # T-1636: `_yaml_load_call_lacks_explicit_loader` is invoked only via
        # `_capability_scan.py`'s _FINGERPRINT_REFINEMENTS dispatch table (a function
        # reference stored by name, looked up and called indirectly), never a
        # literal call token a static call-graph can see -- same class as COV006's
        # own documented argparse-dispatch-table rescue.
        # frob:ticket T-1329
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "safe = yaml.load(raw, Loader=yaml.SafeLoader)\n"
            "unsafe = yaml.load(other_bytes)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    def test_no_match_on_clean_source(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("def add(a, b):\n    return a + b\n")
        assert _scan_file_fingerprints(pkg) == ()

    def test_whitespace_reformatted_needle_still_matches(self, tmp_path: Path) -> None:
        # T-0400 audit finding #3: `shell=True` reformatted with spaces
        # around the `=` used to evade FP-EXEC-SHELL-001 (raw substring
        # search only); the fingerprint scan is now whitespace-tolerant.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    def test_whitespace_tolerant_match_still_respects_comment_spans(
        self, tmp_path: Path
    ) -> None:
        # The whitespace-tolerant matcher must still exclude comment-only
        # occurrences (T-0209), same as the exact-match path.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("# example: subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    def test_matches_the_xxe_fingerprint_positive(self, tmp_path: Path) -> None:
        # T-0189 litmus positive: an lxml parser explicitly left resolving
        # external entities matches FP-XXE-PARSE-001.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=True)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-XXE-PARSE-001" for m in matches)

    def test_does_not_match_the_xxe_fingerprint_negative(self, tmp_path: Path) -> None:
        # T-0189 litmus negative: the hardened lxml configuration (entity
        # resolution explicitly disabled) must not fire.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=False, "
            "no_network=True, load_dtd=False)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-XXE-PARSE-001" for m in matches)

    def test_no_language_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        assert _scan_file_fingerprints(tmp_path / "foo.unknownext") == ()

    def test_unreadable_file_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        missing = tmp_path / "gone.py"
        assert _scan_file_fingerprints(missing) == ()

    def test_language_mismatch_does_not_match(self, tmp_path: Path) -> None:
        # a typescript-only fingerprint's needle appearing in a .py file
        # must never match -- the language gate is enforced independently
        # of the needle text.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("x = 'new Function(\"return 1\")'\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-CODEEVAL-TEMPLATE-001" for m in matches)

    def test_matches_tls_verify_false_python(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-001 -- requests/httpx/aiohttp verify=False.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=False)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    def test_no_match_on_verified_tls_python(self, tmp_path: Path) -> None:
        # negative sibling: verify=True never fires FP-TLS-VERIFY-001.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    def test_matches_tls_reject_unauthorized_false_node(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-002 -- Node https/tls rejectUnauthorized: false.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: false };\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    def test_no_match_on_reject_unauthorized_true_node(self, tmp_path: Path) -> None:
        # negative sibling: rejectUnauthorized: true never fires
        # FP-TLS-VERIFY-002.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: true };\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    def test_matches_tls_danger_accept_invalid_certs_rust(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-003 -- Rust reqwest danger_accept_invalid_certs.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "let client = Client::builder()"
            ".danger_accept_invalid_certs(true).build()?;\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-003" for m in matches)

    def test_no_match_on_default_reqwest_builder_rust(self, tmp_path: Path) -> None:
        # negative sibling: a builder with no danger_accept_invalid_certs
        # call never fires FP-TLS-VERIFY-003.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.rs"
        pkg.write_text("let client = Client::builder().build()?;\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-003" for m in matches)

    def test_own_catalog_file_excluded_from_directory_aggregation(self) -> None:
        # T-0153 self-match note (docs/strata/threat.md#cve-fingerprints-
        # code-level-pattern-catalog-t-0153): _cve_fingerprint.py stores
        # every needle as literal data, so it must be excluded from
        # _scan_directory_capabilities the same way _capability_registry.py
        # already is.
        # frob:tests src/frob/vet/_capability_scan.py::_is_self_path kind="unit"
        from frob.vet._capability_scan import _FINGERPRINT_CATALOG_PATH, _is_self_path

        repo_root = Path(__file__).resolve().parents[2]
        assert _is_self_path(_FINGERPRINT_CATALOG_PATH, repo_root)

    def test_self_pattern_exclusion_covers_every_needle_table_module(self) -> None:
        # T-0201 drift-lock: a registry-of-pattern-files check. Any module
        # under src/frob/ that DEFINES a literal needle table (a
        # `needles=(...)` catalog-entry call, or a `needles: tuple[str, ...]`
        # pydantic field on a catalog model -- the two literal shapes
        # `_capability_registry.py::DANGEROUS_OPERATIONS` and
        # `_cve_fingerprint.py::CVE_FINGERPRINTS` actually use) is the T-0151
        # self-match class this ticket's root cause traces to: scanning that
        # module's own file "observes" every capability its table stores as
        # data, regardless of what the module's code does. This test fails
        # loudly (a future catalog file must widen `is_self_pattern_path`'s
        # exclusion set, not silently produce fresh SYS100/vet noise like
        # T-0201 did for _cve_fingerprint.py) rather than let a new
        # pattern-table file slip past both join paths unexcluded again.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        import re

        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[2]
        src_root = repo_root / "src" / "frob"
        needle_table_marker = re.compile(r"needles\s*=\s*\(|needles\s*:\s*tuple\[")
        offenders: list[Path] = []
        matched: list[Path] = []
        for path in src_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if not needle_table_marker.search(text):
                continue
            matched.append(path)
            if not is_self_pattern_path(path, repo_root):
                offenders.append(path)

        assert offenders == [], (
            f"module(s) define a literal needle table but are not covered by "
            f"is_self_pattern_path: {offenders} -- widen the exclusion set "
            f"in frob.vet._capability"
        )
        # sanity: the marker itself actually matched something -- not
        # accidentally empty (which would make the `offenders == []`
        # assertion above vacuously true). T-1420 split
        # `_capability_registry.py` into a package, so this no longer
        # names a fixed count/set of files (that would re-hardcode the
        # exact thing this drift-lock exists to keep loose) -- it only
        # confirms every catalog/scanner module `_capability.py`,
        # `_cve_fingerprint.py`, and the `_capability_registry/` package's
        # table submodules are still present and still matched.
        assert len(matched) >= 3, matched
        # T-1420 (tail split): the `needles=(...)`/`needles: tuple[...]`
        # prose that used to live in `_capability.py`'s own
        # `_SELF_PATTERN_SUFFIXES` comment block moved verbatim to
        # `_capability_scan.py` along with that constant -- it is the file
        # that matches the marker now, not `_capability.py` itself.
        assert repo_root / "src/frob/vet/_capability_scan.py" in matched
        assert repo_root / "src/frob/strata/_cve_fingerprint.py" in matched
        assert any(p.parent.name == "_capability_registry" for p in matched), matched

    def test_self_pattern_exclusion_survives_a_foreign_install_copy(
        self, tmp_path: Path
    ) -> None:
        # T-0253 round 0: is_self_pattern_path used to compare the SCANNED
        # path's resolved identity against the RUNNING package's own
        # resolved file paths (_SELF_PATH/_REGISTRY_PATH/
        # _FINGERPRINT_CATALOG_PATH). That only matches when the scanned
        # tree and the running package are literally the same checkout (an
        # editable install run via `uv run frob ...`). Under a non-editable
        # global binary (`uv tool install frob`), the running package's
        # files resolve into a site-packages copy, so scanning frob's OWN
        # repo checkout with that binary self-matched every pattern-catalog
        # needle again (36 false SYS100s).
        #
        # Simulate that split here: build a full fake frob repo root (see
        # `_make_fake_frob_repo_root`) at an unrelated tmp path -- standing
        # in for "the tree being scanned is a frob checkout that is not
        # where the running package lives" -- and confirm the three known
        # pattern files are still recognized/excluded THROUGH the T-0253
        # round-2 discriminator (`root` correctly identifies as frob's own
        # repo because it carries the pyproject-name + crate-dir markers,
        # not because of file identity or suffix alone).
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import (
            _aggregate_capabilities,
            is_self_pattern_path,
        )

        fake_repo = _make_fake_frob_repo_root(tmp_path / "foreign-install")
        foreign_frob_src = fake_repo / "src" / "frob"

        foreign_capability = foreign_frob_src / "vet" / "_capability.py"
        # T-1420: _capability_registry.py split into a package -- use one
        # representative table submodule (suffix matching is per-file, not
        # per-directory, so any one of the package's listed suffixes proves
        # the same thing the old single-file path used to).
        foreign_registry = (
            foreign_frob_src
            / "vet"
            / "_capability_registry"
            / "_dangerous_ops_python.py"
        )
        foreign_fingerprint = foreign_frob_src / "strata" / "_cve_fingerprint.py"
        # the discriminator checks the exact scan root passed in (no
        # ancestor search, see `_make_fake_frob_repo_root`'s docstring), so
        # `root` here must be `fake_repo` itself, the directory that
        # actually carries the pyproject-name + crate-dir markers.
        assert is_self_pattern_path(foreign_capability, fake_repo)
        assert is_self_pattern_path(foreign_registry, fake_repo)
        assert is_self_pattern_path(foreign_fingerprint, fake_repo)

        # end-to-end: scanning starting AT the fake repo root (the scan
        # root the discriminator actually recognizes) must skip all three
        # catalog/scanner files while still walking into src/frob/vet.
        _capabilities, _hit, scanned = _aggregate_capabilities(
            fake_repo, max_files=2000
        )
        scanned_paths = {
            p
            for ext in (".py",)
            for p in fake_repo.rglob(f"*{ext}")
            if not is_self_pattern_path(p, fake_repo)
        }
        assert scanned == len(scanned_paths)
        assert foreign_capability not in scanned_paths
        assert foreign_registry not in scanned_paths

    def test_self_pattern_exclusion_does_not_match_unrelated_same_name_file(
        self, tmp_path: Path
    ) -> None:
        # Narrowness check (T-0253): a third-party dependency that happens
        # to ship its own unrelated `_capability.py` at a DIFFERENT package
        # path must not be excluded just because the filename matches --
        # the suffix match requires all three path components
        # (`frob/vet/_capability.py`), not just the final filename. `root`
        # here is not a frob repo either, so both the discriminator AND the
        # suffix check independently refuse this path.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        unrelated_root = tmp_path / "some_other_pkg"
        unrelated = unrelated_root / "utils" / "_capability.py"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("# not frob's file\n")
        assert not is_self_pattern_path(unrelated, unrelated_root)

    def test_self_pattern_exclusion_default_root_is_false(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # `root=None` (the default) short-circuits to False before any
        # path resolution at all -- the caller passed no scan-root
        # identity, so nothing can be confirmed as frob's own repo.
        from frob.vet._capability import is_self_pattern_path

        assert not is_self_pattern_path(tmp_path / "anything.py")

    def test_self_pattern_exclusion_resolve_oserror_is_false(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # A `path.resolve()` failure (e.g. a filesystem-level symlink
        # loop) degrades to "cannot confirm", never a crash.
        from pathlib import Path as _Path

        from frob.vet._capability import is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "repo")
        target = fake_repo / "src" / "frob" / "vet" / "_capability.py"
        real_resolve = _Path.resolve

        def _raising_resolve(self, *args, **kwargs):
            if self == target:
                raise OSError("simulated: resolve failure")
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(_Path, "resolve", _raising_resolve)
        assert not is_self_pattern_path(target, fake_repo)

    def test_self_pattern_exclusion_surprising_parts_shape_is_false(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # A resolved path whose `.parts` is some non-standard shape the
        # suffix-slice comparison cannot safely index into (simulated via
        # a resolve() stub returning a plain object with no real `.parts`)
        # degrades to "cannot confirm", not a crash -- covers both the
        # (KeyError, TypeError) branch and the bare-Exception fallback.
        from pathlib import Path as _Path

        from frob.vet._capability import is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "repo")
        target = fake_repo / "src" / "frob" / "vet" / "_capability.py"
        real_resolve = _Path.resolve

        class _BrokenParts:
            @property
            def parts(self):
                raise TypeError("simulated: surprising parts shape")

        def _raising_resolve(self, *args, **kwargs):
            if self == target:
                return _BrokenParts()
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(_Path, "resolve", _raising_resolve)
        assert not is_self_pattern_path(target, fake_repo)

    # frob:ticket T-0910
    def test_self_pattern_exclusion_covers_logging_checks_needle_tuples(
        self,
    ) -> None:
        # T-0910: `frob.arch._logging_checks`'s `_BOUNDARY_CALLEE_MARKERS`
        # tuple stores the same class of bare-text needle literal
        # (`subprocess.`, `requests.`, `httpx.`, `socket.`, ...) as
        # `_srp.py`'s `_IO_MODULE_PREFIXES` (T-0729) -- a classifier table
        # this module's `_is_boundary_call` compares a parsed callee STRING
        # against, not code that itself execs/opens a socket/fetches a URL.
        # Scanning the file without this exclusion misreports those
        # needles as live net/exec/fetch_url capability USE on the
        # `graphlang` design node (SELFAUDIT001/SYS100). Regression for
        # exactly that false-positive class recurring here.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[2]
        logging_checks_path = repo_root / "src" / "frob" / "arch" / "_logging_checks.py"
        assert logging_checks_path.is_file()
        assert is_self_pattern_path(logging_checks_path, repo_root)

    # frob:ticket T-0910
    def test_line_effects_reports_no_capability_on_logging_checks_module(
        self,
    ) -> None:
        # T-0910: end-to-end companion to the exclusion-membership check
        # above -- `frob.strata._effects._line_effects` (the SYS100/
        # SELFAUDIT001 tier-2 effect scanner) must observe ZERO net/fs/exec
        # effects on `_logging_checks.py` now that it is excluded, not just
        # that `is_self_pattern_path` returns True in isolation.
        # frob:tests src/frob/strata/_effects.py::_line_effects kind="unit"
        from frob.strata._effects import _line_effects

        repo_root = Path(__file__).resolve().parents[2]
        logging_checks_path = repo_root / "src" / "frob" / "arch" / "_logging_checks.py"
        assert _line_effects(logging_checks_path, repo_root) == []

    # frob:ticket T-0915
    def test_self_pattern_exclusion_covers_async_hazards_needle_tuples(
        self,
    ) -> None:
        # T-0915: `frob.arch._async_hazards`'s curated blocking-call-name
        # tables (`subprocess.`, `requests.`, `socket.`, ...) are the same
        # bare-text needle-literal class as `_srp.py` (T-0729) and
        # `_logging_checks.py` (T-0910) -- classifier data compared against
        # parsed callee strings, not live I/O. Without the exclusion the
        # SYS100 scanner misreports them as net/exec capability USE on the
        # `graphlang` node (SELFAUDIT001). Regression for the third
        # recurrence of this false-positive class.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[2]
        async_hazards_path = repo_root / "src" / "frob" / "arch" / "_async_hazards.py"
        assert async_hazards_path.is_file()
        assert is_self_pattern_path(async_hazards_path, repo_root)

    # frob:ticket T-0915
    def test_line_effects_reports_no_capability_on_async_hazards_module(
        self,
    ) -> None:
        # T-0915: end-to-end companion -- the SYS100/SELFAUDIT001 tier-2
        # effect scanner must observe ZERO net/fs/exec effects on
        # `_async_hazards.py` now that it is excluded, not just that
        # `is_self_pattern_path` returns True in isolation.
        # frob:tests src/frob/strata/_effects.py::_line_effects kind="unit"
        from frob.strata._effects import _line_effects

        repo_root = Path(__file__).resolve().parents[2]
        async_hazards_path = repo_root / "src" / "frob" / "arch" / "_async_hazards.py"
        assert _line_effects(async_hazards_path, repo_root) == []

    def test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency(
        self, tmp_path: Path
    ) -> None:
        # T-0253 REJECT-round adversarial test (required by review): a
        # malicious dependency that deliberately reproduces the exact
        # 3-segment suffix (`frob/vet/_capability.py`) under a DIFFERENT,
        # non-frob root must be SCANNED -- not silently excluded -- when
        # `frob vet` scans it as a dependency. The dependency's own root is
        # NOT frob's repo (no pyproject.toml name=="frob", no frob-core/
        # strata-core dirs), so `_is_frob_repo_root` must refuse and the
        # suffix match must never be reached, regardless of how closely the
        # nested path mimics frob's own layout.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability import scan_file_capabilities
        from frob.vet._capability_scan import (
            _aggregate_capabilities,
            is_self_pattern_path,
        )

        evil_root = tmp_path / "evil-pkg"
        evil_capability = evil_root / "frob" / "vet" / "_capability.py"
        evil_capability.parent.mkdir(parents=True)
        evil_capability.write_text('import os\nos.system("evil")\n')

        # the file itself really does carry a live capability...
        assert "exec" in scan_file_capabilities(evil_capability)
        # ...and the discriminator must refuse the exclusion for this root,
        # even though the path suffix is an exact match for frob's own
        # `_capability.py` layout.
        assert not is_self_pattern_path(evil_capability, evil_root)

        # end-to-end: frob vet's own directory-aggregation entrypoint must
        # actually observe the capability, not silently skip the file.
        capabilities, _hit, scanned = _aggregate_capabilities(evil_root, max_files=500)
        assert scanned == 1
        assert "exec" in capabilities

    def test_scan_directory_fingerprints_aggregates_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_fingerprints

        (tmp_path / "a.py").write_text("data = yaml.load(raw_bytes)\n")
        (tmp_path / "b.py").write_text("def add(a, b):\n    return a + b\n")
        matched = _scan_directory_fingerprints(tmp_path)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matched)

    def test_scan_directory_fingerprints_excludes_the_catalog_itself(
        self, tmp_path: Path
    ) -> None:
        # scanning frob's own src tree must not self-match every fingerprint
        # via _cve_fingerprint.py's own needle literals (self-match note,
        # docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153).
        # T-0253: the exclusion only fires when the scan root itself
        # identifies as frob's own repo (see the sibling capability-scan
        # test above for why); scan from a fake repo root instead of the
        # bare `src/frob/strata` subdirectory.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_fingerprints

        fake_repo = _make_fake_frob_repo_root(tmp_path / "self-scan")
        matched = _scan_directory_fingerprints(fake_repo, max_files=2000)
        assert not any(m.id == "FP-DESERIALIZE-YAML-001" for m in matched)


# frob:ticket T-0380
class TestFingerprintBindingResolution:
    """T-0380: `_scan_file_fingerprints` reuses the SAME binding tables
    capability scanning built (T-0328/T-0377/T-0378/T-0379) so an aliased
    import that would evade a lexical needle match is still caught --
    adversarial test per language."""

    def test_python_aliased_pickle_loads_still_matches(self, tmp_path: Path) -> None:
        # `import pickle as p; p.loads(...)` never contains the literal
        # text "pickle.loads(" the lexical scan needs -- a real fingerprint
        # (FP-DESERIALIZE-PICKLE-001) resolved through the alias table.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import pickle as p\ndata = p.loads(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-PICKLE-001" for m in matches)

    def test_python_unaliased_control_still_matches_lexically(
        self, tmp_path: Path
    ) -> None:
        # Control: the un-aliased form still matches via the pre-existing
        # lexical path (this ticket adds recall, never removes it).
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import pickle\ndata = pickle.loads(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-PICKLE-001" for m in matches)

    def test_typescript_aliased_require_still_matches(self, tmp_path: Path) -> None:
        # `const ax = require('axios'); ax.get(url)` resolves to
        # "axios.get" through _ts_resolved_candidates -- a synthetic
        # axios-shaped fingerprint proves _binding_fingerprints' TS path
        # independent of whether the real CVE_FINGERPRINTS catalog happens
        # to carry a module.member-shaped typescript needle today.
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-AXIOS-001",
            title="test-only axios.get() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-918",
            language="typescript",
            needles=("axios.get(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax.get(url);\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-AXIOS-001" for m in matches)

    def test_typescript_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-AXIOS-001",
            title="test-only axios.get() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-918",
            language="typescript",
            needles=("axios.get(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const x = 1 + 2;\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-AXIOS-001" for m in matches)

    def test_rust_aliased_use_still_matches(self, tmp_path: Path) -> None:
        # `use std::process::Command as C; C::new("sh")` never contains the
        # literal text "Command::new(" -- resolved via the rust `use`
        # binding table (T-0378) to "std::process::Command::new".
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-COMMAND-001",
            title="test-only Command::new() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="rust",
            needles=("Command::new(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-COMMAND-001" for m in matches)

    def test_rust_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-COMMAND-001",
            title="test-only Command::new() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="rust",
            needles=("Command::new(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.rs"
        pkg.write_text("fn add(a: i32, b: i32) -> i32 { a + b }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-COMMAND-001" for m in matches)

    def test_c_aliased_macro_still_matches(self, tmp_path: Path) -> None:
        # `#define SYS system; SYS(cmd)` never contains the literal text
        # "system(" -- resolved via the C macro-alias table (T-0379).
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-SYSTEM-001",
            title="test-only system() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="c-cpp",
            needles=("system(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.c"
        pkg.write_text("#define SYS system\nvoid f(char *cmd) { SYS(cmd); }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-SYSTEM-001" for m in matches)

    def test_c_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-SYSTEM-001",
            title="test-only system() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="c-cpp",
            needles=("system(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.c"
        pkg.write_text("int add(int a, int b) { return a + b; }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-SYSTEM-001" for m in matches)


class TestObfuscationEnsemble:
    # invariant spec: [INV-025](invariants/INV-025.md)
    def test_high_entropy_string_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_text_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_text_obfuscation

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        assert "high-entropy-string" in _scan_text_obfuscation(text)

    def test_plain_string_not_flagged(self) -> None:
        from frob.vet._obfuscation import _scan_text_obfuscation

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert "high-entropy-string" not in _scan_text_obfuscation(text)

    def test_bidi_override_is_fatal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_invisible_text_signal kind="unit"
        from frob.vet._obfuscation import _invisible_text_signal

        text = "x = 1" + chr(0x202E) + "y = 2"
        assert _invisible_text_signal(text) is True

    def test_clean_text_no_bidi(self) -> None:
        from frob.vet._obfuscation import _invisible_text_signal

        assert _invisible_text_signal("x = 1\ny = 2\n") is False

    def test_hex_identifier_ratio_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_hex_identifier_ratio_signal \
        # kind="unit"
        from frob.vet._obfuscation import _hex_identifier_ratio_signal

        idents = " ".join(f"_0x{i:04x}" for i in range(30))
        assert _hex_identifier_ratio_signal(idents) is True

    def test_normal_identifiers_not_flagged(self) -> None:
        from frob.vet._obfuscation import _hex_identifier_ratio_signal

        idents = " ".join(f"variable_name_{i}" for i in range(30))
        assert _hex_identifier_ratio_signal(idents) is False

    def test_high_entropy_strings_returns_the_literal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_high_entropy_strings kind="unit"
        from frob.vet._obfuscation import _high_entropy_strings

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        hits = _high_entropy_strings(text)
        assert len(hits) == 1
        assert hits[0].startswith("aGVsbG8")

    def test_high_entropy_strings_empty_for_plain_text(self) -> None:
        from frob.vet._obfuscation import _high_entropy_strings

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert _high_entropy_strings(text) == ()

    def test_scan_directory_obfuscation_finds_signal_in_one_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        (tmp_path / "clean.py").write_text("x = 1\n")
        (tmp_path / "evil.py").write_text(
            'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        )
        signals = _scan_directory_obfuscation(tmp_path)
        assert "high-entropy-string" in signals

    def test_bidi_override_detected_in_c_file(self, tmp_path: Path) -> None:
        # T-0400 audit finding #5: C/C++/Kotlin were entirely excluded from
        # `_SCANNABLE_SUFFIXES`, so the deterministic Trojan-Source bidi
        # scan (CVE-2021-42574, demonstrated in C/C++) never ran on a
        # dependency's .c files at all.
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        rlo = chr(0x202E)
        # T-3510: explicit encoding="utf-8" -- the U+202E RIGHT-TO-LEFT
        # OVERRIDE character this test plants is exactly the kind of
        # obfuscation payload the scanner exists to catch, so it must
        # reach disk unmangled; Windows' platform-default 'charmap'/cp1252
        # codec cannot encode it at all (UnicodeEncodeError), unlike
        # POSIX where UTF-8 is normally the default.
        (tmp_path / "evil.c").write_text(
            f"// {rlo}nommoc si sti\nint main() {{}}\n", encoding="utf-8"
        )
        signals = _scan_directory_obfuscation(tmp_path)
        assert "invisible-text" in signals

    def test_bidi_override_detected_in_kotlin_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        rlo = chr(0x202E)
        # T-3510: explicit encoding="utf-8", same rationale as the sibling
        # C-file test above.
        (tmp_path / "Evil.kt").write_text(
            f"// {rlo}nommoc si sti\nfun main() {{}}\n", encoding="utf-8"
        )
        signals = _scan_directory_obfuscation(tmp_path)
        assert "invisible-text" in signals

    def test_split_string_payload_still_not_detected(self, tmp_path: Path) -> None:
        # Honest documented limitation (T-0400 audit finding #5, NOT
        # closed by this ticket): `_MIN_STRING_LEN` (24) is a PER-LITERAL
        # floor, so a base64 payload split into concatenated pieces each
        # shorter than 24 chars (`"aGVsb" + "G8gd" + ...`) never fires --
        # no single literal is ever long enough to be scored. Closing this
        # needs a real string-concatenation-aware rewrite, out of scope
        # for this pass.
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        pieces = [
            "aGVsb",
            "G8gd2",
            "9ybGQ",
            "sIHRo",
            "aXMgaX",
            "MgYSB0",
            "ZXN0IH",
            "BheWxv",
            "YWQ",
        ]
        joined = " + ".join(f'"{p}"' for p in pieces)
        (tmp_path / "evil.py").write_text(f"x = {joined}\n")
        signals = _scan_directory_obfuscation(tmp_path)
        assert "high-entropy-string" not in signals


class TestVerdictCache:
    def test_store_and_retrieve_latest(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_cache.py::_store_verdict kind="unit"
        # frob:tests src/frob/vet/_cache.py::_latest_verdict kind="unit"
        from frob.vet import _cache
        from frob.vet._models import PackageVerdict

        db_path = tmp_path / ".frob" / "vet.db"
        v1 = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            artifact_hash="hash1",
            capabilities=frozenset({"net"}),
        )
        _cache._store_verdict(db_path, v1)
        latest = _cache._latest_verdict(db_path, "pypi", "foo")
        assert latest is not None
        assert latest.artifact_hash == "hash1"
        assert latest.capabilities == frozenset({"net"})

    def test_missing_cache_returns_none(self, tmp_path: Path) -> None:
        from frob.vet import _cache

        assert (
            _cache._latest_verdict(tmp_path / ".frob" / "vet.db", "pypi", "nope")
            is None
        )


class TestCapabilityDiff:
    def test_added_capability_detected(self) -> None:
        # frob:tests src/frob/vet/_models.py::capability_diff kind="unit"
        from frob.vet._models import PackageVerdict, capability_diff

        prev = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        cur = PackageVerdict(
            name="foo",
            version="1.1.0",
            ecosystem="pypi",
            capabilities=frozenset({"net", "exec"}),
        )
        assert capability_diff(prev, cur) == ("exec",)

    def test_no_diff_when_unchanged(self) -> None:
        from frob.vet._models import PackageVerdict, capability_diff

        prev = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        cur = PackageVerdict(
            name="foo",
            version="1.1.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        assert capability_diff(prev, cur) == ()


class TestEcosystemRules:
    def test_python_setup_py_cmdclass_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_python_rules kind="unit"
        from frob.findings import Severity
        from frob.vet import _ecosystem

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\nsetup(cmdclass={'install': Foo})\n"
        )
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem._python_rules(dep, tmp_path, "uv.lock")
        rules = {v.rule for v in violations}
        assert "VET-PY001" in rules
        assert any(
            v.severity is Severity.ERROR for v in violations if v.rule == "VET-PY001"
        )

    def test_python_pth_file_flagged(self, tmp_path: Path) -> None:
        from frob.vet import _ecosystem

        (tmp_path / "evil.pth").write_text("import os; os.system('echo hi')\n")
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem._python_rules(dep, tmp_path, "uv.lock")
        assert any(v.rule == "VET-PY002" for v in violations)

    def test_rust_build_rs_capability_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_rust_rules kind="unit"
        from frob.vet import _ecosystem

        (tmp_path / "build.rs").write_text(
            'fn main() { std::process::Command::new("curl"); }\n'
        )
        dep = Dependency(ecosystem="cargo", name="evilcrate", version="1.0.0")
        violations = _ecosystem._rust_rules(dep, tmp_path, "Cargo.lock")
        assert any(v.rule == "VET-RS001" for v in violations)

    def test_npm_non_registry_source_flagged(self) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_npm_non_registry_rule kind="unit"
        from frob.vet import _ecosystem

        dep = Dependency(
            ecosystem="npm",
            name="evilpkg",
            version="1.0.0",
            resolved="git+https://example.com/evil/evilpkg.git",
        )
        violation = _ecosystem._npm_non_registry_rule(dep, "package-lock.json")
        assert violation is not None
        assert violation.rule == "VET-JS004"

    def test_npm_registry_source_not_flagged(self) -> None:
        from frob.vet import _ecosystem

        dep = Dependency(
            ecosystem="npm",
            name="lodash",
            version="4.17.21",
            resolved="https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        )
        violation = _ecosystem._npm_non_registry_rule(dep, "package-lock.json")
        assert violation is None
