"""Curated may-raise rule tables (T-3627, split out of `frob.arch._mayraise`
along the rule/table boundary that module's own docstring already
describes): every "known raiser" constant and lookup table the may-raise
resolver's fixpoint logic consults, with none of the resolution logic
itself -- `_mayraise.py` imports these names rather than redefining them,
so this module's own docstring, not that one's, is the CANONICAL home for
"what does row X mean and why is it here" going forward.

MODULE-LIMIT DISCLOSURE (T-0686/T-0689): every note here about a table's
disclosed scope carve-out (what it deliberately does NOT cover, and why)
originates in the parent `_mayraise.py` module docstring and this ticket's
predecessors (T-0685 umbrella, T-0689 FFI boundary curation, T-2552/T-2568
false-positive fixes) -- this split changes WHERE the tables live, never
their content or the resolution behavior built on top of them."""

from __future__ import annotations

#: Sentinel raised-type name (T-0686) meaning "this function may raise
#: something this resolver could not statically determine" -- the
#: fail-closed contribution of any unresolved callee or unresolvable bare
#: `raise`. Kept as a plain string (not a distinct type) since every other
#: raised-type name in this module is already a bare exception-name string
#: and `FunctionMayRaise.raises` is one homogeneous `frozenset[str]`.
#: `frob:doc` points at the dedicated may-raise-resolver anchor (T-0916).
# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
UNKNOWN = "Unknown"

#: Exception types (T-0685) tracked as an always-possible tier SEPARATE
#: from a function's own computed may-raise set -- async/asynchronous-
#: delivery exceptions no static analysis of a function's own body can
#: rule out. Exhaustiveness never demands these be enumerated per
#: function; only a boundary catch-all (bare `except:`) discharges them
#: (see `frob.arch._mayraise`'s module docstring).
# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
UBIQUITOUS_TIER: frozenset[str] = frozenset(
    {"MemoryError", "KeyboardInterrupt", "SystemExit"}
)

#: Minimal Python exception-hierarchy parent map (T-0686) -- just enough
#: of `BaseException`'s tree for `_mayraise._catches`'s subtype check to
#: know that `except Exception` discharges a raised `ValueError`, `except
#: LookupError` discharges a raised `KeyError`, etc. Not exhaustive
#: against the full `builtins` hierarchy (no existing check in this
#: package needs more, and the curated `_BUILTIN_RAISERS` table below
#: only ever contributes types already listed here) -- extend as new
#: builtin-raiser rows need a new leaf.
# frob:ticket T-0686
_EXCEPTION_PARENT: dict[str, str | None] = {
    "BaseException": None,
    "SystemExit": "BaseException",
    "KeyboardInterrupt": "BaseException",
    "Exception": "BaseException",
    "StopIteration": "Exception",
    "ValueError": "Exception",
    "TypeError": "Exception",
    "AttributeError": "Exception",
    "NameError": "Exception",
    "UnboundLocalError": "NameError",
    "LookupError": "Exception",
    "KeyError": "LookupError",
    "IndexError": "LookupError",
    "ArithmeticError": "Exception",
    "ZeroDivisionError": "ArithmeticError",
    "OSError": "Exception",
    "FileNotFoundError": "OSError",
    "PermissionError": "OSError",
    "IsADirectoryError": "OSError",
    "RuntimeError": "Exception",
    "NotImplementedError": "RuntimeError",
    "RecursionError": "RuntimeError",
    "AssertionError": "Exception",
    "ImportError": "Exception",
    "ModuleNotFoundError": "ImportError",
    "MemoryError": "Exception",
    # T-0689: parent links for the curated stdlib C-extension raiser table
    # below -- `JSONDecodeError` really is a `ValueError` subclass
    # (`json.JSONDecodeError(ValueError)`); `sqlite3.Error`/`struct.error`
    # are their own hierarchy roots directly under `Exception`.
    "JSONDecodeError": "ValueError",
    "sqlite3.Error": "Exception",
    "struct.error": "Exception",
}

# see T-0685 for the history behind this
_BUILTIN_RAISERS: dict[str, frozenset[str]] = {
    # T-2552: `TypeError` deliberately ABSENT from both. `int(x)`/`float(x)`
    # raise it only when `x` is not string/number-shaped at all -- a static
    # type error, owned by the `ty` gate (measured: `ty` reports
    # `int(str | None)` and `int(dict)` at ERROR severity inside `frob
    # check`, and correctly stays silent once the `None` is narrowed away,
    # which this resolver structurally cannot do). Attributing it here made
    # EXHAUST002 demand a handler for an impossible path at 26 of 74 sites
    # while every one of them already handled the possible one
    # (`ValueError`), and the only cheap way to satisfy it is the blanket
    # `except Exception:` this gate family exists to prevent.
    "int": frozenset({"ValueError"}),
    "float": frozenset({"ValueError"}),
    "open": frozenset({"OSError"}),
    "getattr": frozenset({"AttributeError"}),
    "next": frozenset({"StopIteration"}),
}

# see T-0689 for the history behind this
_STDLIB_QUALIFIED_RAISERS: dict[str, frozenset[str]] = {
    "json.loads": frozenset({"JSONDecodeError"}),
    "json.load": frozenset({"JSONDecodeError"}),
    "sqlite3.connect": frozenset({"sqlite3.Error"}),
    "sqlite3.execute": frozenset({"sqlite3.Error"}),
    "struct.pack": frozenset({"struct.error"}),
    "struct.unpack": frozenset({"struct.error"}),
}

#: Raised-type name a bare (dict-shaped default, see `frob.arch._mayraise`'s
#: module docstring) `NormalizedSubscript` event contributes.
# frob:ticket T-0686
_SUBSCRIPT_RAISE = "LookupError"
