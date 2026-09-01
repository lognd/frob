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

#: Curated builtin-raiser table (T-0685/T-0686): bare callee name -> the
#: exception type(s) that call is known to be capable of raising, per the
#: parent ticket's own examples (`int()`/`float()` casts -> `ValueError`,
#: `getattr` reflection -> `AttributeError`, `open`/file IO -> `OSError`,
#: `next` on an exhausted iterator -> `StopIteration`). A call whose bare
#: name matches a row here is treated as RESOLVED (contributes exactly
#: these types, does not also fall through to the unresolved-callee
#: `UNKNOWN` path) even though this resolver has no `NormalizedFunction`
#: body for it to recurse into -- deliberately narrow (see
#: `frob.arch._mayraise`'s module docstring): every callee name NOT in
#: this table and NOT a same-module function is fail-closed to `UNKNOWN`,
#: not silently assumed safe.
# frob:ticket T-0686
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

#: Curated stdlib C-EXTENSION raiser table (T-0689), keyed on the call's
#: FULL dotted callee text (`"json.loads"`, not the bare `"loads"`) --
#: deliberately a SEPARATE, more specific table from `_BUILTIN_RAISERS`
#: (which matches on bare name): a bare-name match here would risk
#: shadowing an unrelated same-module function that happens to share a
#: name with one of these (`def pack(...)` in the caller's own module,
#: say) the same way `_BUILTIN_RAISERS` already narrowly accepts for true
#: builtins with no realistic same-module collision. Qualified stdlib
#: C-extension calls (json's `_json` accelerator, sqlite3's `_sqlite3`,
#: struct's `_struct`) resolve to their documented raised type instead of
#: falling through to the opaque-boundary `UNKNOWN` default (this ticket's
#: user mandate) -- extend as more curated stdlib C-extension surface is
#: identified; anything NOT listed here (including ctypes/cffi calls,
#: which have no fixed per-call raised type at all -- see
#: `frob.arch._mayraise`'s module docstring) stays `UNKNOWN`, fail-closed,
#: unless covered by a `frob:callee-raises` declaration
#: (`NormalizedCall.declared_raises`).
# frob:ticket T-0689
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
