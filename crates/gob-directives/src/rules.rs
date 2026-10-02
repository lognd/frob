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
/// 7-char forms) and v1 `T-0042` forms are rewritten by `frob ticket expand`,
/// which needs the ledger to resolve them.
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
