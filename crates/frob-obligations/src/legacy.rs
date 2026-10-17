//! The file-scope rules still declared with the legacy derive (the `FileRule` framework has no
//! path or side-input access yet); the other rules of this crate live in `src/rules/`.

use gob_rules::Rule;

/// A comment carries an upper-case work marker with no owning ticket.
///
/// The marker words are the four upper-case words to-do, fix-me, triple-x and
/// hack (see the rule table of `docs/design/rules.md`). A marker is owned when
/// a `frob:todo <ulid>` directive sits on the same or the previous line, or
/// when the marker is written with a full ULID in parentheses right after it.
/// File a ticket and add the directive.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    family = "TODO",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Todo001;

/// A public item has no doc comment.
///
/// A doc comment is `///` or `/** */` directly above the item, or a `#[doc]`
/// attribute. Public items of test files, trait-impl members and file-backed
/// modules are not checked. This complements the compiler lint `missing_docs`
/// for languages without one.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "DOC001",
    slug = "undocumented-public-item",
    family = "DOC",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pminus,
    version = 1
)]
pub struct Doc001;

/// A markdown link points at a missing path or a missing heading.
///
/// Relative `[text](path)` and `[text](path#anchor)` links must name an
/// existing file or directory (relative to the file, or to the repo root with
/// a leading `/`), and an anchor on a markdown target must match a heading
/// slug. External `http(s)` and `mailto` links, and links inside code, are
/// ignored. Fix the path or the anchor.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "DOC002",
    slug = "broken-markdown-link",
    family = "DOC",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Doc002;

/// A `frob:ticket` directive names a ticket that is not in the ledger.
///
/// The full ULID resolves to no ticket. Abbreviated ids never reach this rule:
/// the scanner reports them as DSL002 and keeps no directive. Fix the id or
/// file the ticket. Not evaluated without a ledger.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "REF001",
    slug = "dangling-ticket-ref",
    family = "REF",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    must_measure = true,
    version = 1
)]
pub struct Ref001;

/// A public function or method has no test that reaches it.
///
/// The symbol graph's `public_api` lists the function; a test (a function the
/// `frob-tests` catalog recognises) reaches it when the call graph, or the
/// unique-name call scan of `frob-tests`, links the test to it, or when a
/// `frob:tests` directive names the pair. Trait-impl members and items in test
/// files are not checked. Add a test, or bind an existing one with
/// `frob:tests <test>` above the function.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "COV001",
    slug = "untested-public-function",
    family = "COV",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pminus,
    must_measure = true,
    version = 1
)]
pub struct Cov001;

/// A `frob:todo` directive points at a ticket that is already done or dropped.
///
/// The ticket named by the directive is in the terminal category, so the work
/// it owned is finished (or abandoned) yet the marker remains. Do the work,
/// remove the marker, or re-point it at a live ticket.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TODO002",
    slug = "todo-ticket-terminal",
    family = "TODO",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    must_measure = true,
    version = 1
)]
pub struct Todo002;
