## Done report

-- T-4030

**Changed**
- tests/test_policy.py
  - `TestDangerousInnerHtmlJsonStringify`: 2 new tests plus a shared
    `_write_rule` fixture helper.
    - `test_fires_on_direct_json_stringify` (positive control): a
      `.tsx` source file with
      `dangerouslySetInnerHTML={{__html: JSON.stringify(data)}}`
      configured via a real `[[policy.pattern]]` entry (`language =
      "tsx"`, a `.scm` query file) fires `POL-danger-html-json-
      stringify`.
    - `test_stays_quiet_on_sanitized_value` (near-miss control): the
      SAME attribute shape but calling `sanitize(data)` instead of
      `JSON.stringify(...)` does not fire on that file (a sibling file
      with a real hit keeps the overall match count nonzero so T-3986's
      POL000 -- a separate concern -- does not also fire here).
  - No production code changes: `frob.policy`'s existing `pattern` rule
    kind already handles this fully as-is -- `language = "tsx"` resolves
    via `tree_sitter_language_pack.get_language("tsx")`/`get_parser`
    (verified working), and `tree_sitter.QueryCursor.captures` already
    evaluates the query's own `#eq?` predicates before returning
    captures, so a structural query with predicates over `JSON`/
    `stringify`/`dangerouslySetInnerHTML` needs no engine change.

**WHY**
Per the consumer's own framing (Item 3, "the most shippable item"): a
JSX `dangerouslySetInnerHTML` attribute whose value is a direct
`JSON.stringify(...)` call expression is unescaped HTML built from a
serialization that does not escape `</script>`-breaking sequences -- a
well-known XSS vector, distinct from ordinary unescaped-HTML injection,
and purely structural (no taint/data-flow analysis needed). This ticket
proves the query and ships it as a concrete, tested example against the
real `tsx` grammar.

**The query (`policy/queries/POL-danger-html-json-stringify.scm` in**
the test fixture)
```
(jsx_attribute
  (property_identifier) @_attr
  (jsx_expression
    (object
      (pair
        value: (call_expression
          function: (member_expression
            object: (identifier) @_json
            property: (property_identifier) @_stringify))))) @danger
  (#eq? @_attr "dangerouslySetInnerHTML")
  (#eq? @_json "JSON")
  (#eq? @_stringify "stringify"))
```
`@danger` is the reported capture (not underscore-prefixed, per
T-3986's convention); `@_attr`/`@_json`/`@_stringify` are anchor-only
captures used purely by the `#eq?` predicates.

**Acceptance criteria proof**
- [1] (fires on a direct JSON.stringify value): proven by
  `tests/test_policy.py::TestDangerousInnerHtmlJsonStringify::test_fires_on_direct_json_stringify`.
  The near-miss control
  (`test_stays_quiet_on_sanitized_value`) additionally proves the query
  is structural on the exact call shape, not on the attribute name
  alone.
- [2] (lands after T-4013, not before): enforced at the ticket-graph
  level (`blocked_by=['T-4013']`, already `[done]` on `dev` before this
  ticket started -- confirmed via `frob ticket show T-4013`) rather than
  a pytest node id; left UNBOUND (a sequencing constraint has no test
  evidence to bind).

**Test node ids (all passing, `pytest tests/test_policy.py -q`: 19**
passed, 0 failed)
- tests/test_policy.py::TestDangerousInnerHtmlJsonStringify::test_fires_on_direct_json_stringify
- tests/test_policy.py::TestDangerousInnerHtmlJsonStringify::test_stays_quiet_on_sanitized_value

**Evidence bound**
- acceptance[1] <- both node ids above (`frob ticket evidence T-4030 ...
  --base-ref dev`, run after the final commit)

**Commit**
39bbc83ff test(policy): prove dangerouslySetInnerHTML+JSON.stringify pattern
(worktree /home/logan/projects/frob/.claude/worktrees/t-3986-policy,
branch t-3986, stacked on T-3986's own commit 11e917673)

**Gates run**
- ruff check / ruff format --check: clean.
- `frob check --only coverage --files src/frob/policy/__init__.py
  --files tests/test_policy.py --base dev`: grep over the full unscoped
  output shows zero findings naming either touched file (the new test
  class/methods carry `# frob:ticket T-4030` directives).
- Did not re-run `--only sys` for this ticket alone (no new production
  symbol; T-3986's own GATERULE001 finding, already reported in its own
  Done report, is the only cross-cutting item touching this file).

**Filed**
- None new for this ticket (T-3986's T-draft-58a07e89 already covers
  the one outstanding cross-cutting gap on this file).

**Scope note**
- No production code change was needed or made; this ticket's
  deliverable is the proven query plus tests, per its own "writable
  today" framing. If a future consumer wants this shipped as a
  default/bundled rule (rather than something each `frob.toml` must
  configure itself), that is out of this ticket's scope as written and
  not something this ticket's acceptance criteria asked for.

### Changed
(no changed files detected)

### Evidence
- `tests/test_policy.py::TestDangerousInnerHtmlJsonStringify::test_fires_on_direct_json_stringify` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestDangerousInnerHtmlJsonStringify::test_stays_quiet_on_sanitized_value` (pytest node id, verified passing when recorded)
