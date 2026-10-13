//! The PARSE and DSL rules declared here (D32); emitted under the parsing product.

/// A `frob:` directive is malformed: unterminated quote, bad key, missing or invalid argument.
///
/// The scanner never silently drops a directive line it recognises by
/// namespace; if the arguments cannot be read into the verb's declared shape
/// the finding points at the exact offending token. Fix the directive text
/// so it matches `<namespace>:<verb> <args>` with `key=value` or
/// `key="quoted value"` pairs.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "PARSE001",
    slug = "malformed-directive",
    family = "PARSE",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    version = 1
)]
pub struct Parse001;

/// A directive names a verb its namespace does not declare.
///
/// The namespace is honoured but the verb is not registered; the message
/// carries a did-you-mean suggestion when a declared verb is close. Fix the
/// spelling or remove the directive.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "DSL001",
    slug = "unknown-directive-verb",
    family = "DSL",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    version = 1
)]
pub struct Dsl001;

/// A directive carries an abbreviated ticket id instead of a full 26-char ULID.
///
/// Only full ULIDs persist in tracked text (D24). Handles (`~3M8Z4T7`, bare
/// 7-char forms) and v1 `T-0042` forms must be replaced with the full id that
/// `frob ticket show <handle>` prints.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "DSL002",
    slug = "abbreviated-ticket-id",
    family = "DSL",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Deterministic,
    version = 1
)]
pub struct Dsl002;

/// A directive uses a deprecated `frob:` claim spelling that D120 moved or dropped.
///
/// `frob:effects`, `core`, `shell`, `calls`, `pure` and `honest` became `grimble:` verbs;
/// `dispatcher`, `hook`, `trusted` and `idempotent` were dropped in favour of an `accept`
/// exception, inference or a bound test. Old spellings parse for one minor release; apply the
/// attached fix (`grimble:effects none`, or an `accept` exception to complete) to migrate.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "DSL003",
    slug = "deprecated-directive-spelling",
    family = "DSL",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Deterministic,
    version = 1
)]
pub struct Dsl003;

/// The metadata of every rule declared here; calling it keeps this object linked.
///
/// The rule registry is built from `inventory` entries, which a linker drops with the object file
/// that holds them unless something references that object. A non-inlined function defined next to
/// the rules gives binaries that only list directives (the generator) that reference.
#[inline(never)]
pub(crate) fn declared() -> [&'static gob_rules::RuleMeta; 4] {
    [&Parse001::META, &Dsl001::META, &Dsl002::META, &Dsl003::META]
}
