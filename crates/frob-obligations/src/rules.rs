//! The rules declared by this crate; findings are built in the sibling modules.

// frob:ticket 01M4FD3KT1XFB1N1GZYXFRMPT7

use gob_rules::Rule;

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

/// Alias of TEST001; never emitted by this crate.
///
/// A `frob:tests` directive naming a missing test is reported once, as
/// `TEST001`, owned by `frob-tests`. This id is kept declared so references
/// to it resolve, but no finding carries it (the registry has no duplicate
/// finding for one problem). Fix the symref or remove the directive.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "COV003",
    slug = "tests-names-missing-test",
    family = "COV",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pminus,
    version = 1
)]
pub struct Cov003;

/// A comment carries an upper-case work marker with no owning ticket.
///
/// The marker words are the four upper-case words to-do, fix-me, triple-x and
/// hack (see the rule table of `docs/design/rules.md`). A marker is owned when
/// a `frob:todo <ulid>` directive sits on the same or the previous line, or
/// when the marker is written with a full ULID in parentheses right after it.
/// Comments of every scanned language count, YAML and TOML included (see
/// `docs/reference/fidelity.md`). File a ticket and add the directive.
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

/// Hand-written text links to a ticket-branch path instead of the ticket's ULID.
///
/// A ticket file's path (`<epic>/<slug>.md`) changes when the ticket is retitled or reparented, so a link to
/// it rots. This covers a bare path that is a ticket file, a blob or tree URL on the ticket branch, and the
/// old `tickets/<ULID>/ticket.md` form. `frob check --fix` rewrites the link to the ULID. Generated pages
/// (first line carries the generated marker) use relative paths on purpose and are skipped. On a ticket-branch
/// ledger the hand-written files (ticket bodies, `EPIC.md`) are scanned too; those findings name the ledger path
/// and carry no machine fix (edit the ticket so it links the ULID).
// frob:ticket 01M3ZX86MA30ABW915Z943BQYB
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK006",
    slug = "ledger-path-reference",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = File,
    fix = Deterministic,
    polarity = Pplus,
    version = 1
)]
pub struct Tick006;

/// An invariants document has no `frob:invariant` directive in code.
///
/// Each `invariants/<slug>.md` file must be upheld somewhere: a
/// `frob:invariant <slug>` directive (slug is the file stem) in code or tests
/// anchors it. Add the directive where the invariant is enforced, or remove the
/// document.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "INV001",
    slug = "invariant-without-anchor",
    family = "INV",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pminus,
    version = 1
)]
pub struct Inv001;

/// A file imports something the `[invariants]` table forbids.
///
/// An entry of `forbid_imports` (`from`, `to`, `reason`) forbids every file
/// matching `from` from importing a path starting with `to`. The finding names
/// the import and the reason. Remove the import, or accept the finding at file
/// level with a reason if the boundary does not apply. An entry whose glob does
/// not compile is reported as an unresolved finding.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "INV002",
    slug = "forbidden-import",
    family = "INV",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Inv002;

/// An accept or defer directive carries a reason the checker rejects.
///
/// The `because` text failed `gob_rules::check_reason`: too short, a banned
/// phrase, a restated rule id or a repeated word. Name an ADR, a style anchor
/// or a real one-sentence reason. The exception still suppresses its finding
/// so the gate fails on this rule alone.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC001",
    slug = "exception-reason-rejected",
    family = "EXC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc001;

/// A defer directive names a ticket that is done or dropped.
///
/// The debt's ticket reached a terminal category, so the exit condition of the
/// defer is met: pay the debt (remove the directive and fix the finding) or
/// re-point the defer at a live ticket. The deferred finding stays suppressed
/// and listed so the failure is this one finding, not a surprise.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC003",
    slug = "defer-ticket-terminal",
    family = "EXC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc003;

/// An accept directive's bound symbol changed since it was attested.
///
/// `frob.lock` holds the digest recorded when the accept was attested. The
/// bound symbol's body digest differs, or no entry exists (unattested), so the
/// acceptance may no longer describe the code. Re-read it and run `frob ack
/// <symref>` with a reason.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC005",
    slug = "accept-not-attested",
    family = "EXC",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc005;

/// A defer directive names a ticket that does not exist.
///
/// The ticket resolves to nothing in the ledger. Fix the id or file the ticket
/// that will pay the debt. Not evaluated without a ledger.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC007",
    slug = "defer-ticket-missing",
    family = "EXC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc007;

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// A defer directive's `until` date has passed.
///
/// The defer names a calendar day (`until=YYYY-MM-DD`, UTC) that is before
/// today, so the debt is overdue: the deferred finding stands again and this
/// rule names the expiry. A value that is not a date and holds no `:` is
/// reported here too. Metric targets (`until=ticket-closed:...`) are decided
/// by the product that knows the metric, not here. Pay the debt, or replace
/// the directive with a new defer and a fresh date after review.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC014",
    slug = "defer-expired",
    family = "EXC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc014;

/// An accept directive names a rule at a site where the finding is Unresolved.
///
/// An Unresolved finding means the tool could not examine the site. Accepting
/// it would silence the failure without supplying the declaration that fixes
/// it, so the accept does not suppress it and the finding stands. Park it with
/// `frob:defer` and a ticket, or put it in a baseline.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC016",
    slug = "accept-on-unresolved",
    family = "EXC",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc016;

/// A native suppression of a rule bound through a tool stage has no frob exception.
///
/// A `[[check.tool]]` stage maps tool ids to frob rule ids with `id_map`. A
/// native suppression of such an id (`#[allow(..)]`, `#[expect(..)]`,
/// `# zizmor: ignore[..]` or `// eslint-disable ..`) hides a finding from the
/// tool, so frob never sees it. Add a `frob:accept` or `frob:defer` of the
/// mapped rule at the same site so the suppression has a reason and an owner.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "EXC017",
    slug = "native-suppression-without-exception",
    family = "EXC",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
pub struct Exc017;
