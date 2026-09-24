"""frob.sql._sqlfluff_plugin -- sqlfluff plugin hosting frob's own SQL
performance rules (T-5335, T-5148-1's owner directive).

One sentence: this module registers into sqlfluff's `sqlfluff` entry-point
plugin group (`pyproject.toml`'s `[project.entry-points.sqlfluff]`) via the
`hookimpl` functions sqlfluff's own plugin host calls (`get_rules`,
`load_default_config`, `get_configs_info`), the same shape sqlfluff's own
built-in rules use (`sqlfluff.core.plugin.lib`), and it is only importable
when the `sql` extra (`sqlfluff` itself) is installed --
`frob.doctor.ToolCategory.REQUIRED_FOR_FAMILY`'s absence-is-measured
posture covers the case where it is not (see that enum member's own
docstring).

## Scope cut (T-5335 own contingency clause)

T-5335's own ticket body names fourteen candidate performance rules and
says: "If more than ~half of these don't fit sqlfluff's plugin rule-class
cleanly, split the session/config-level ones ... into a follow-up ticket
rather than forcing the fit." More than half of the named checks need
either cross-statement session state (missing statement_timeout,
long-running transaction), whole-corpus schema knowledge (non-sargable
predicate needs an index catalog this AST-only plugin does not have,
COUNT(*)-vs-EXISTS needs the same), or a resolved query-plan shape
(correlated-subquery-where-join-fits) this leaf's declared scope
(`src/frob/sql/_sqlfluff_plugin.py`, `src/frob/doctor.py`,
`pyproject.toml` only) cannot reach. This leaf ships the four rules that
fit a single-statement AST walk cleanly (`Frob_L001`-`Frob_L004` below);
the rest are filed as a follow-up ticket per this ticket's own
contingency clause rather than forced to fit -- see that filed ticket's
id in T-5335's own Done report.

## Rule id shape

sqlfluff's `RuleMetaclass` requires a plugin rule class named
`Rule_<PluginName>_<LLNN>` (`Rule_Frob_L001`), which sqlfluff composes
into the reported code `Frob_L001` -- not one of frob's own gate rule ids
(`_KNOWN_GATE_RULES`), since these findings surface through sqlfluff's
own CLI/API, not `frob check`.
"""

from __future__ import annotations

from typing import Any

from sqlfluff.core.config import load_config_resource
from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.rules import BaseRule, ConfigInfo, LintResult, RuleContext
from sqlfluff.core.rules.crawlers import SegmentSeekerCrawler


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
class Rule_Frob_L001(BaseRule):
    """Query uses ``SELECT *`` instead of naming the columns it needs.

    ``SELECT *`` pulls every column across the wire (and defeats
    covering-index reads) even when the caller only needs a handful --
    name the columns instead.
    """

    groups = ("all", "frob")
    crawl_behaviour = SegmentSeekerCrawler({"select_clause"})

    def _eval(self, context: RuleContext) -> LintResult | None:
        """Flag a `select_clause` that contains a bare `wildcard_expression`
        (`SELECT *`, not `SELECT t.*`... note: `t.*` also parses as a
        `wildcard_expression` and is flagged too -- an explicitly
        qualified star is still "every column of this table", the same
        performance/coupling concern named in T-5335's own rule list)."""
        if context.segment.get_child("wildcard_expression") is not None:
            return LintResult(
                anchor=context.segment,
                description="SELECT * fetches every column; name the columns "
                "this query actually needs.",
            )
        for element in context.segment.get_children("select_clause_element"):
            if element.get_child("wildcard_expression") is not None:
                return LintResult(
                    anchor=element,
                    description="SELECT * fetches every column; name the "
                    "columns this query actually needs.",
                )
        return None


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
class Rule_Frob_L002(BaseRule):
    """``UPDATE``/``DELETE`` statement with no ``WHERE`` clause.

    An unqualified ``UPDATE``/``DELETE`` touches every row in the table --
    almost always a mistake, and a full-table write when only a subset
    was intended.
    """

    groups = ("all", "frob")
    crawl_behaviour = SegmentSeekerCrawler({"update_statement", "delete_statement"})

    def _eval(self, context: RuleContext) -> LintResult | None:
        """Flag an `update_statement`/`delete_statement` with no
        `where_clause` child -- a statement-scoped structural check, no
        cross-statement session state needed (the "config/session-level"
        rules this ticket split off DO need that, per this module's own
        docstring)."""
        if context.segment.get_child("where_clause") is None:
            kind = context.segment.type.removesuffix("_statement").upper()
            return LintResult(
                anchor=context.segment,
                description=f"{kind} with no WHERE clause touches every row "
                "in the table.",
            )
        return None


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
class Rule_Frob_L003(BaseRule):
    """``HAVING`` used where a ``WHERE`` predicate would do.

    A ``HAVING`` clause whose condition references no aggregate function
    is filtering pre-aggregation rows after the fact -- the same filter
    written as ``WHERE`` lets the engine discard non-matching rows before
    grouping, instead of aggregating everything and discarding after.
    """

    groups = ("all", "frob")
    crawl_behaviour = SegmentSeekerCrawler({"having_clause"})

    def _eval(self, context: RuleContext) -> LintResult | None:
        """Flag a `having_clause` whose condition expression contains no
        `function` segment named as one of the standard aggregate
        functions -- a textual-proxy check (function name only, no
        resolved-schema knowledge of which identifiers are aggregates),
        the same posture this leaf's own docstring discloses for every
        rule here."""
        aggregate_names = {
            "count",
            "sum",
            "avg",
            "min",
            "max",
            "array_agg",
            "string_agg",
        }
        for func in context.segment.recursive_crawl("function"):
            name_segment = func.get_child("function_name")
            if name_segment is not None and name_segment.raw.lower() in (
                aggregate_names
            ):
                return None
        return LintResult(
            anchor=context.segment,
            description="HAVING with no aggregate function filters rows "
            "that a WHERE clause could discard before grouping.",
        )


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
class Rule_Frob_L004(BaseRule):
    """``OFFSET``-based pagination on a ``SELECT``.

    ``LIMIT ... OFFSET N`` re-scans and discards the first ``N`` rows on
    every page -- keyset/cursor pagination (``WHERE id > :last_seen_id
    ORDER BY id LIMIT ...``) stays O(page size) at any offset instead of
    O(offset + page size).
    """

    groups = ("all", "frob")
    crawl_behaviour = SegmentSeekerCrawler({"limit_clause"})

    def _eval(self, context: RuleContext) -> LintResult | None:
        """Flag a `limit_clause` containing an `OFFSET` keyword -- a
        purely syntactic check (the clause either has the keyword or it
        does not), no resolved query-plan needed."""
        for kw in context.segment.get_children("keyword"):
            if kw.raw.upper() == "OFFSET":
                return LintResult(
                    anchor=context.segment,
                    description="OFFSET-based pagination re-scans and "
                    "discards every prior page's rows; prefer keyset/cursor "
                    "pagination.",
                )
        return None


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
@hookimpl  # ty: ignore[invalid-argument-type] -- pluggy's `HookimplMarker.
# __call__` overloads (sqlfluff.core.plugin.hookimpl's own runtime type)
# are not resolvable by ty's inference the way pytest.hookimpl's own stub
# is (T-5335's own measured finding: `ty check` flags the decorator, not
# this function's body); sqlfluff's own `core` plugin
# (sqlfluff/core/plugin/lib.py) decorates its hookimpls identically, so
# this is a stub-resolution gap in a third-party dependency, not a real
# type error in frob's own code.
def get_rules() -> list[type[BaseRule]]:
    """T-5335: frob's own plugin rule set (`Frob_L001`-`Frob_L004` above)
    -- sqlfluff's plugin host calls this once per lint run to collect
    every registered plugin's rules alongside its own built-ins."""
    return [Rule_Frob_L001, Rule_Frob_L002, Rule_Frob_L003, Rule_Frob_L004]


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
@hookimpl  # ty: ignore[invalid-argument-type] -- same pluggy
# `HookimplMarker` stub gap as `get_rules` above.
def load_default_config() -> dict[str, Any]:
    """T-5335: this plugin's default config block (none of `Frob_L001`-
    `Frob_L004` take config keywords yet, so this is the minimal empty
    `rules`/`Frob` section sqlfluff's config loader expects to find --
    the same `load_config_resource` sqlfluff's own `core` plugin uses,
    pointed at this package's `default_config.cfg` instead)."""
    return load_config_resource(
        package="frob.sql",
        file_name="sqlfluff_default_config.cfg",
    )


# frob:doc docs/modules/sql.md#sqlfluff-plugin-t-5335
@hookimpl  # ty: ignore[invalid-argument-type] -- same pluggy
# `HookimplMarker` stub gap as `get_rules` above.
def get_configs_info() -> dict[str, ConfigInfo]:
    """T-5335: no `Frob_L001`-`Frob_L004` rule takes a config keyword yet,
    so there is nothing to validate here -- an empty dict is sqlfluff's
    own documented "no plugin-specific config" answer, not an omission."""
    return {}
