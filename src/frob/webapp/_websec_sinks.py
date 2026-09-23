"""WEBSEC101-106: XSS/output-encoding sink registry (T-5307, extends the
SEC005 taint substrate -- docs/modules/webapp-websec-injection.md).

`frob.gates._taint_gate.taint_gate` is SEC005's own repo-writable-state ->
subprocess-argv taint pass over every tracked `.py` file (T-0781). T-5141
(the WEBSEC injection/output-encoding leaf of the T-5140 web-app epic)
extends that SAME gate wiring with a second, framework-scoped source/sink
family -- not a parallel taint engine -- covering the classic DOM/template
XSS sink shapes ASVS 5.0 V1.1.2/V1.2.1 (CWE-79) names: a value that
reaches an HTML-interpreter sink with no encoding/sanitizer hop in
between. `taint_gate` calls `websec_sink_findings` alongside its own
SEC005 scan and folds the results into the same `Violation` tuple it
already returns.

FRAMEWORK GATING (T-5302): `frob.webapp._detect.detect_frameworks` is the
one entry point this module consults to decide whether `root` is a web
surface at all -- an empty `detect_frameworks(root)` short-circuits to no
scan, the same posture every other WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule
family takes. This module never re-implements framework sniffing.

SIX SINK KINDS (T-5307's declared scope, matching the T-5141 corpus items
2-7 the reserved `WEBSEC101`-`WEBSEC106` rule-id block already names in
`frob.gates._waive._KNOWN_GATE_RULES`):

- WEBSEC101: JS/TS/JSX assignment to `.innerHTML`/`.outerHTML`, or a call
  to `document.write(...)`/`.insertAdjacentHTML(...)`, with a non-literal,
  unsanitized right-hand side/argument -- read via `frob.lang.raw_tree`'s
  tree-sitter AST (T-5300's JS/TS/JSX walkers wire `.js`/`.jsx`/`.ts`/
  `.tsx` into `frob.lang.parse_file`; this module reads the same grammar
  through the `raw_tree` escape hatch those walkers' own docstrings name).
- WEBSEC102: JSX `dangerouslySetInnerHTML={{__html: X}}` where `X` is not
  a sanitizer call.
- WEBSEC103: Vue SFC `v-html="expr"` inside a `.vue` file's
  `template_element` block (T-5300's `_walk_vue.py` docstring names this
  exact detector as its own future `raw_tree` consumer), where `expr` is
  not a literal or a sanitizer call.
- WEBSEC104: Jinja2 `{{ x|safe }}` in a template file, or
  `Environment(...)`/`Flask(...)` constructed with `autoescape=False` in a
  Python source file -- TEXT-REGEX (T-5307's declared scope: Jinja's
  autoescape config is not a tree-sitter-parseable shape frob has a
  grammar for).
- WEBSEC105: Django `django.utils.safestring.mark_safe(x)` with a
  non-literal `x`, or a template `{% autoescape off %}` block -- TEXT-
  REGEX.
- WEBSEC106: Rails `.html_safe` called on a non-literal receiver, or a
  `raw(...)` helper call with a non-literal argument -- TEXT-REGEX.

Each is WARN-tier at first turn-on (same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate` already follow for a brand-new structural
rule): a real fix-or-waive pass over the first measured hit set decides
whether ERROR is safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node

from frob.gitio import run_argv
from frob.lang import raw_tree
from frob.lang._nodes import child_by_field, node_text
from frob.logging import get_logger
from frob.webapp._detect import detect_frameworks

_log = get_logger(__name__)

__all__ = ["WebsecSinkFinding", "websec_sink_findings"]

#: Call/receiver names this module treats as "the value has already been
#: escaped/sanitized", clearing an otherwise-tainted sink argument --
#: DOMPurify (JS ecosystem convention) plus the generic
#: `escape`/`sanitize`/`htmlspecialchars`-shaped name family `frob.vet.
#: _taint._VALIDATOR_NAME_RE` already uses for the SEC005 substrate this
#: gate extends.
_SANITIZER_NAME_RE = re.compile(
    r"(DOMPurify|sanitize|escape|htmlspecialchars|clean)", re.IGNORECASE
)

#: JS/TS/JSX member-expression sink properties: an assignment
#: `<expr>.innerHTML = X` / `<expr>.outerHTML = X`.
_JS_ASSIGNMENT_SINK_PROPERTIES = frozenset({"innerHTML", "outerHTML"})

#: JS/TS/JSX call sinks: `document.write(X)` / `<expr>.insertAdjacentHTML(...)`.
_JS_CALL_SINK_NAMES = frozenset({"write", "insertAdjacentHTML"})


# frob:doc docs/modules/webapp-websec-injection.md#public-api
@dataclass(frozen=True)
class WebsecSinkFinding:
    """One WEBSEC101-106 finding: an unsanitized value reaching an
    HTML-interpreter sink (CWE-79).

    frob:ticket T-5307
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- same tracked-file-scan shape
    `frob.gates._taint_gate._tracked_python_files` already uses.

    frob:ticket T-5307
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_sinks: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_sinks: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _is_sanitized(text: str) -> bool:
    """True if `text` (an unparsed RHS/argument expression) already names
    a recognized sanitizer call -- the same "textual proxy, not resolved
    flow" posture `frob.vet._taint._looks_like_repo_state_read` documents
    for SEC005.

    frob:ticket T-5307
    """
    return bool(_SANITIZER_NAME_RE.search(text))


def _is_literal(node: Node | None) -> bool:
    """True if `node` is a plain string/template literal with no
    interpolation -- a hardcoded HTML fragment is not a sink finding, only
    a value that could carry attacker-controlled content is.

    frob:ticket T-5307
    """
    if node is None:
        return True
    if node.type == "string":
        return True
    if node.type == "template_string":
        return not any(c.type == "template_substitution" for c in node.children)
    return False


def _js_assignment_findings(root_node: Node, rel_path: str) -> list[WebsecSinkFinding]:
    """WEBSEC101 findings: `.innerHTML`/`.outerHTML` assignments with a
    non-literal, unsanitized right-hand side.

    frob:ticket T-5307
    """
    findings: list[WebsecSinkFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "assignment_expression":
            continue
        left = child_by_field(node, "left")
        right = child_by_field(node, "right")
        if left is None or left.type != "member_expression":
            continue
        prop = child_by_field(left, "property")
        prop_name = node_text(prop)
        if prop_name not in _JS_ASSIGNMENT_SINK_PROPERTIES:
            continue
        if _is_literal(right):
            continue
        right_text = node_text(right)
        if _is_sanitized(right_text):
            continue
        findings.append(
            WebsecSinkFinding(
                rule="WEBSEC101",
                file=rel_path,
                line=node.start_point[0] + 1,
                message=(
                    f"WEBSEC101: {rel_path}:{node.start_point[0] + 1} "
                    f".{prop_name} assigned an unsanitized, non-literal "
                    f"value ({right_text!r}) -- DOM XSS sink (ASVS 5.0 "
                    f"V1.1.2/V1.2.1, CWE-79). Pass the value through a "
                    f"DOMPurify/sanitize call first, or `frob:waive "
                    f'WEBSEC101 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _js_call_findings(root_node: Node, rel_path: str) -> list[WebsecSinkFinding]:
    """WEBSEC101 findings: `document.write(...)`/`.insertAdjacentHTML(...)`
    calls with a non-literal, unsanitized argument.

    frob:ticket T-5307
    """
    findings: list[WebsecSinkFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "call_expression":
            continue
        func = child_by_field(node, "function")
        if func is None:
            continue
        name = func.type == "member_expression" and node_text(
            child_by_field(func, "property")
        )
        if name not in _JS_CALL_SINK_NAMES:
            continue
        args_node = child_by_field(node, "arguments")
        if args_node is None:
            continue
        # `insertAdjacentHTML(position, html)`'s sink argument is the
        # second positional; `document.write(html)`'s is the first --
        # both cases the LAST argument is the HTML-interpreted one.
        arg_nodes = [c for c in args_node.named_children]
        if not arg_nodes:
            continue
        sink_arg = arg_nodes[-1]
        if _is_literal(sink_arg):
            continue
        arg_text = node_text(sink_arg)
        if _is_sanitized(arg_text):
            continue
        findings.append(
            WebsecSinkFinding(
                rule="WEBSEC101",
                file=rel_path,
                line=node.start_point[0] + 1,
                message=(
                    f"WEBSEC101: {rel_path}:{node.start_point[0] + 1} "
                    f"{name}(...) received an unsanitized, non-literal "
                    f"argument ({arg_text!r}) -- DOM XSS sink (ASVS 5.0 "
                    f"V1.1.2/V1.2.1, CWE-79). Pass the value through a "
                    f"DOMPurify/sanitize call first, or `frob:waive "
                    f'WEBSEC101 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _jsx_dangerous_findings(root_node: Node, rel_path: str) -> list[WebsecSinkFinding]:
    """WEBSEC102 findings: `dangerouslySetInnerHTML={{__html: X}}` where
    `X` is not a sanitizer call.

    frob:ticket T-5307
    """
    findings: list[WebsecSinkFinding] = []
    for node in _iter_nodes(root_node):
        if node.type != "jsx_attribute":
            continue
        name_node = node.named_children[0] if node.named_children else None
        if node_text(name_node) != "dangerouslySetInnerHTML":
            continue
        value_text = node_text(node)
        if _is_sanitized(value_text):
            continue
        findings.append(
            WebsecSinkFinding(
                rule="WEBSEC102",
                file=rel_path,
                line=node.start_point[0] + 1,
                message=(
                    f"WEBSEC102: {rel_path}:{node.start_point[0] + 1} "
                    f"dangerouslySetInnerHTML bypasses React's default "
                    f"escaping (ASVS 5.0 V1.1.2/V1.2.1, CWE-79) -- pass "
                    f"the __html value through a sanitizer first, or "
                    f'`frob:waive WEBSEC102 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _iter_nodes(node: Node):  # noqa: ANN201 -- Iterator[Node], tree-sitter's own Node has no public generic alias
    """Every node in `node`'s subtree, depth-first (including `node` itself).

    frob:ticket T-5307
    """
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _js_findings(path: Path, root: Path) -> list[WebsecSinkFinding]:
    """WEBSEC101/WEBSEC102 findings for one `.js`/`.jsx`/`.ts`/`.tsx` file.

    frob:ticket T-5307
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "websec_sinks: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return []
    tree, _source, _language = parsed.danger_ok
    findings = _js_assignment_findings(tree.root_node, rel_path)
    findings.extend(_js_call_findings(tree.root_node, rel_path))
    if path.suffix in (".jsx", ".tsx"):
        findings.extend(_jsx_dangerous_findings(tree.root_node, rel_path))
    return findings


_VUE_VHTML_RE = re.compile(r'v-html\s*=\s*"([^"]*)"')


def _vue_findings(path: Path, root: Path) -> list[WebsecSinkFinding]:
    """WEBSEC103 findings: `v-html="expr"` inside a `.vue` file's
    `<template>` block, TEXT-REGEX over the raw `template_element` source
    span (T-5300's `_walk_vue.py` docstring: this exact detector queries
    the raw subtree, not the SFC-shell symbol walk).

    frob:ticket T-5307
    """
    rel_path = path.relative_to(root).as_posix()
    parsed = raw_tree(path, expect_heterogeneous=True)
    if parsed.is_err:
        _log.debug(
            "websec_sinks: skipping unparseable %s: %s", rel_path, parsed.danger_err
        )
        return []
    tree, source, _language = parsed.danger_ok
    findings: list[WebsecSinkFinding] = []
    for node in tree.root_node.children:
        if node.type != "template_element":
            continue
        block_text = source[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        )
        base_line = node.start_point[0]
        for match in _VUE_VHTML_RE.finditer(block_text):
            expr = match.group(1)
            if not expr or _is_sanitized(expr):
                continue
            line = base_line + block_text.count("\n", 0, match.start()) + 1
            findings.append(
                WebsecSinkFinding(
                    rule="WEBSEC103",
                    file=rel_path,
                    line=line,
                    message=(
                        f"WEBSEC103: {rel_path}:{line} v-html={expr!r} "
                        f"bypasses Vue's default template escaping (ASVS "
                        f"5.0 V1.1.2/V1.2.1, CWE-79) -- pass the bound "
                        f"value through a sanitizer first, or `frob:waive "
                        f'WEBSEC103 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    return findings


_JINJA_SAFE_RE = re.compile(r"\{\{\s*([^}|]+?)\s*\|\s*safe\s*\}\}")
_JINJA_AUTOESCAPE_FALSE_RE = re.compile(r"autoescape\s*=\s*False")

_DJANGO_MARK_SAFE_RE = re.compile(r"mark_safe\(\s*([^)]*)\)")
_DJANGO_AUTOESCAPE_OFF_RE = re.compile(r"\{%\s*autoescape\s+off\s*%\}")

_RAILS_HTML_SAFE_RE = re.compile(r"([A-Za-z_][\w.\[\]]*)\s*\.\s*html_safe\b")
_RAILS_RAW_RE = re.compile(r"\braw\(\s*([^)]*)\)")

#: A bare string/interpolation-only literal argument -- not a sink finding.
_TEXT_LITERAL_RE = re.compile(r'^\s*["\'].*["\']\s*$')


def _text_regex_findings(
    text: str,
    rel_path: str,
    *,
    rule: str,
    pattern: re.Pattern[str],
    capture_is_receiver: bool,
    reason: str,
) -> list[WebsecSinkFinding]:
    """Every `pattern` match in `text` whose captured expression is
    non-literal and unsanitized -- the shared TEXT-REGEX shape
    WEBSEC104/105/106 all use (Jinja/Django/Rails autoescape-bypass
    sinks are not tree-sitter-parseable shapes frob has a grammar for,
    T-5307's declared scope).

    frob:ticket T-5307
    """
    findings: list[WebsecSinkFinding] = []
    for match in pattern.finditer(text):
        expr = match.group(1).strip() if match.lastindex else ""
        if capture_is_receiver and not expr:
            continue
        if expr and (_TEXT_LITERAL_RE.match(expr) or _is_sanitized(expr)):
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecSinkFinding(
                rule=rule,
                file=rel_path,
                line=line,
                message=(
                    f"{rule}: {rel_path}:{line} {reason} (ASVS 5.0 "
                    f"V1.1.2/V1.2.1, CWE-79) -- encode the value or "
                    f"confirm it cannot carry attacker input, or `frob"
                    f':waive {rule} reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _jinja_findings(path: Path, root: Path) -> list[WebsecSinkFinding]:
    """WEBSEC104 findings: `{{ x|safe }}` in a template file, or
    `autoescape=False` in a Python source file.

    frob:ticket T-5307
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    if path.suffix == ".py":
        findings: list[WebsecSinkFinding] = []
        for match in _JINJA_AUTOESCAPE_FALSE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                WebsecSinkFinding(
                    rule="WEBSEC104",
                    file=rel_path,
                    line=line,
                    message=(
                        f"WEBSEC104: {rel_path}:{line} autoescape=False "
                        f"disables Jinja2's default context-aware "
                        f"escaping (ASVS 5.0 V1.1.2/V1.2.1, CWE-79) -- "
                        f"enable autoescaping, or `frob:waive WEBSEC104 "
                        f'reason="..."` with a real justification'
                    ),
                )
            )
        return findings
    return _text_regex_findings(
        text,
        rel_path,
        rule="WEBSEC104",
        pattern=_JINJA_SAFE_RE,
        capture_is_receiver=False,
        reason="{{ ... | safe }} bypasses Jinja2's default escaping",
    )


def _django_findings(path: Path, root: Path) -> list[WebsecSinkFinding]:
    """WEBSEC105 findings: `mark_safe(x)` with a non-literal `x`, or a
    `{% autoescape off %}` template block.

    frob:ticket T-5307
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    if path.suffix == ".py":
        if "mark_safe" not in text:
            return []
        return _text_regex_findings(
            text,
            rel_path,
            rule="WEBSEC105",
            pattern=_DJANGO_MARK_SAFE_RE,
            capture_is_receiver=False,
            reason="mark_safe(...) bypasses Django's default escaping",
        )
    if "autoescape" not in text:
        return []
    return _text_regex_findings(
        text,
        rel_path,
        rule="WEBSEC105",
        pattern=_DJANGO_AUTOESCAPE_OFF_RE,
        capture_is_receiver=False,
        reason="{% autoescape off %} disables Django's default escaping",
    )


def _rails_findings(path: Path, root: Path) -> list[WebsecSinkFinding]:
    """WEBSEC106 findings: `.html_safe` on a non-literal receiver, or a
    `raw(...)` call with a non-literal argument.

    frob:ticket T-5307
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings = _text_regex_findings(
        text,
        rel_path,
        rule="WEBSEC106",
        pattern=_RAILS_HTML_SAFE_RE,
        capture_is_receiver=True,
        reason=".html_safe bypasses Rails' automatic ERB escaping",
    )
    findings.extend(
        _text_regex_findings(
            text,
            rel_path,
            rule="WEBSEC106",
            pattern=_RAILS_RAW_RE,
            capture_is_receiver=False,
            reason="raw(...) bypasses Rails' automatic ERB escaping",
        )
    )
    return findings


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5307
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# frob:doc docs/modules/webapp-websec-injection.md#public-api
# frob:ticket T-5307
def websec_sink_findings(root: Path) -> tuple[WebsecSinkFinding, ...]:
    """WEBSEC101-106: every unsanitized DOM/template XSS sink under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract) -- this scan
    is expensive (tree-sitter parses plus a regex pass) and irrelevant for
    a plain Python CLI repo.

    frob:ticket T-5307
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_sinks: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecSinkFinding] = []

    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        findings.extend(_js_findings(root / rel, root))
    for rel in _tracked_files(root, ".vue"):
        findings.extend(_vue_findings(root / rel, root))
    for rel in _tracked_files(root, ".html", ".htm", ".jinja", ".jinja2", ".j2"):
        findings.extend(_jinja_findings(root / rel, root))
        findings.extend(_django_findings(root / rel, root))
    for rel in _tracked_files(root, ".py"):
        findings.extend(_jinja_findings(root / rel, root))
        findings.extend(_django_findings(root / rel, root))
    for rel in _tracked_files(root, ".rb", ".erb"):
        findings.extend(_rails_findings(root / rel, root))

    _log.info("websec_sinks: %d finding(s) under %s", len(findings), root)
    return tuple(findings)
