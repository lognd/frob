//! `frob release status`: the readiness verdict for one release, assembled from gathered facts.
//!
//! Design: `releases.md` sections 3, 4 and 6a. [`assess`] is pure: the caller (the CLI) reads the
//! milestone, the ledger and the changelog dry-run and hands the facts in as [`Input`]; the result
//! is a typed [`Report`] with a list of typed [`Blocker`]s, the items that are not checkable yet
//! as [`Unresolved`] lines (never blockers, never assumed green), and a one-line verdict. Nothing
//! here can fail: a report that finds problems is still a report.

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
use schemars::JsonSchema;
use serde::Serialize;

use crate::ci::{CiFacts, CiState};

/// Why a release is not ready; one per problem, so the count in the verdict is honest.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum BlockerKind {
    /// No milestone object exists for the version.
    NoMilestone,
    /// The milestone is released or dropped, not open.
    MilestoneNotOpen,
    /// An exit criterion has no passing evidence bound to it.
    UnboundCriterion,
    /// A ticket in the milestone's epics (or labelled `release:VERSION`) is not done.
    OpenTicket,
    /// A `PM034` finding for the milestone.
    Pm034,
    /// A `changelog.d` fragment is invalid.
    InvalidFragment,
    /// The changelog cannot be compiled for another reason (version present, edited section).
    Changelog,
    /// A check on the base-branch tip failed, was cancelled or timed out.
    CiRed,
    /// Checks on the base-branch tip are still running.
    CiPending,
    /// CI could not be read and `[release] require_ci` is true.
    CiUnknown,
}

/// One reason the release is not ready.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Blocker {
    /// What kind of problem this is.
    pub kind: BlockerKind,
    /// What it is about: a criterion position, a ticket handle, a file name, the version.
    pub subject: String,
    /// One line saying what is wrong, with the remedy where there is one.
    pub detail: String,
}

/// A passing evidence record that binds an exit criterion.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct EvidenceRef {
    /// The provider that measured it.
    pub provider: String,
    /// What was measured.
    pub reference: String,
    /// `[attested by X: "statement"]` (escaped) when a person attested rather than a tool measured.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub label: Option<String>,
}

/// One exit criterion as the report shows it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CriterionStatus {
    /// 1-based position, the number `--accepts` uses.
    pub position: usize,
    /// The criterion text.
    pub text: String,
    /// `bound` or `unbound`.
    pub state: String,
    /// The binding evidence (empty when unbound).
    pub evidence: Vec<EvidenceRef>,
}

/// An open ticket that belongs to the release.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct OpenTicket {
    /// Handle with `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Workflow category (`triage`, `todo`, `in-progress`).
    pub category: String,
}

/// A ticket of the release that shipped without a changelog note, with the audited reason.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ExemptTicket {
    /// Handle with `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Who recorded the exemption.
    pub actor: String,
    /// Why no changelog note was written.
    pub reason: String,
}

/// Open tickets of one category, in the order they were gathered.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CategoryGroup {
    /// Workflow category.
    pub category: String,
    /// The tickets in it.
    pub tickets: Vec<OpenTicket>,
}

/// The facts about the milestone object, when there is one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MilestoneFacts {
    /// Handle with `~`.
    pub handle: String,
    /// One-line goal.
    pub goal: String,
    /// `open`, `released` or `dropped`.
    pub state: String,
    /// Member epics as `~handle title` lines.
    pub epics: Vec<String>,
    /// Exit criteria with their binding evidence.
    pub criteria: Vec<CriterionStatus>,
    /// Messages of the `PM034` findings for this milestone.
    pub pm034: Vec<String>,
}

/// What the changelog dry-run said.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ChangelogFacts {
    /// Fragments compile; the rendered section, absent when there are no fragments.
    Valid {
        /// Fragment file names.
        fragments: Vec<String>,
        /// The rendered section preview.
        section: Option<String>,
    },
    /// One or more fragments are invalid; each error names its file.
    InvalidFragments(Vec<(String, String)>),
    /// The compile refused for another reason; the message teaches the remedy.
    Refused(String),
}

/// Everything [`assess`] needs, already gathered.
#[derive(Debug, Clone)]
pub struct Input {
    /// The version being assessed.
    pub version: String,
    /// The milestone, absent when none exists for the version.
    pub milestone: Option<MilestoneFacts>,
    /// Open tickets of the member epics and those labelled `release:VERSION`.
    pub open_tickets: Vec<OpenTicket>,
    /// Tickets of the release closed with `--no-changelog`.
    pub exempt_tickets: Vec<ExemptTicket>,
    /// The changelog dry-run result.
    pub changelog: ChangelogFacts,
    /// What CI said about the base-branch tip.
    pub ci: CiFacts,
}

/// Fragment validity as the report shows it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FragmentsStatus {
    /// `valid`, `invalid` or `refused`.
    pub state: String,
    /// Fragment file names that compile (or would).
    pub fragments: Vec<String>,
    /// One message per problem, each naming its file; empty when valid.
    pub errors: Vec<String>,
}

/// An item that cannot be checked yet, with the reason; never a blocker, never assumed fine.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Unresolved {
    /// What is unresolved.
    pub item: String,
    /// Why, in one line.
    pub reason: String,
}

/// CI on the commit a cut would release, as the report shows it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CiReport {
    /// The base-branch tip inspected; absent when the branch did not resolve.
    pub sha: Option<String>,
    /// `green`, `red`, `pending` or `unknown`.
    pub state: String,
    /// One line: what was found, with the failing names and links, or the reason and the remedy.
    pub detail: String,
    /// `[release] require_ci`: whether unknown blocks.
    pub required: bool,
}

/// The readiness report for one release.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Report {
    /// The report as lines, verdict first, for the text view.
    pub at_a_glance: Vec<String>,
    /// Every reason the release is not ready.
    pub blockers: Vec<Blocker>,
    /// CI on the tip commit a cut would release.
    pub ci: CiReport,
    /// The changelog section a cut would write; absent without fragments.
    pub changelog_preview: Option<String>,
    /// Exit criteria with their binding state.
    pub criteria: Vec<CriterionStatus>,
    /// Tickets of the release that carry a changelog exemption instead of a fragment.
    pub changelog_exempt: Vec<ExemptTicket>,
    /// Fragment validity.
    pub fragments: FragmentsStatus,
    /// The milestone handle, absent when there is no milestone object.
    pub milestone: Option<String>,
    /// Open tickets of the release grouped by category.
    pub open_tickets: Vec<CategoryGroup>,
    /// The `PM034` findings for the milestone.
    pub pm034: Vec<String>,
    /// True when there are no blockers.
    pub ready: bool,
    /// Items not checkable yet, with their reasons.
    pub unresolved: Vec<Unresolved>,
    /// `READY` or `NOT READY: N blocker(s)`.
    pub verdict: String,
    /// The version assessed.
    pub version: String,
}

/// Categories in workflow order; groups are emitted in this order.
const CATEGORY_ORDER: [&str; 3] = ["triage", "todo", "in-progress"];

/// Repository-relative path and anchor of the guide's one-time setup section (the registry setup runbook).
const REGISTRY_SETUP_GUIDE: &str = "docs/guides/release.md#one-time-setup";

/// The fixed items the design lists as owner actions or later checks (`releases.md` 6a), with reasons; CI is added per report.
#[must_use]
pub fn unresolved_items() -> Vec<Unresolved> {
    let u = |item: &str, reason: &str| Unresolved {
        item: item.to_owned(),
        reason: reason.to_owned(),
    };
    vec![
        u("forecast", "no history yet"),
        u(
            "registry setup",
            &format!(
                "owner action: trusted publishing on PyPI (frob) and crates.io, reserved crate names confirmed; see {REGISTRY_SETUP_GUIDE}"
            ),
        ),
    ]
}

/// The fixed items plus, when CI could not be read, its line with the exact reason and remedy.
fn unresolved_of(input: &Input) -> Vec<Unresolved> {
    let mut items = Vec::new();
    if let CiState::Unknown(u) = &input.ci.state {
        items.push(Unresolved {
            item: format!("CI status on {}", short(input.ci.sha.as_deref())),
            reason: format!("{}; {}", u.reason, u.remedy),
        });
    }
    items.extend(unresolved_items());
    items
}

fn group(tickets: &[OpenTicket]) -> Vec<CategoryGroup> {
    let mut cats: Vec<&str> = CATEGORY_ORDER.to_vec();
    for t in tickets {
        if !cats.contains(&t.category.as_str()) {
            cats.push(&t.category);
        }
    }
    cats.into_iter()
        .filter_map(|c| {
            let ts: Vec<OpenTicket> = tickets
                .iter()
                .filter(|t| t.category == c)
                .cloned()
                .collect();
            (!ts.is_empty()).then(|| CategoryGroup {
                category: c.to_owned(),
                tickets: ts,
            })
        })
        .collect()
}

fn blocker(kind: BlockerKind, subject: impl Into<String>, detail: impl Into<String>) -> Blocker {
    Blocker {
        kind,
        subject: subject.into(),
        detail: detail.into(),
    }
}

fn blockers_of(input: &Input) -> Vec<Blocker> {
    let mut out = Vec::new();
    match &input.milestone {
        None => out.push(blocker(
            BlockerKind::NoMilestone,
            &input.version,
            format!(
                "no milestone for {}; create it with `frob milestone new {} --goal <text>`",
                input.version, input.version
            ),
        )),
        Some(m) => {
            if m.state != "open" {
                out.push(blocker(
                    BlockerKind::MilestoneNotOpen,
                    &m.handle,
                    format!("milestone {} is {}, not open", input.version, m.state),
                ));
            }
            for c in m.criteria.iter().filter(|c| c.state != "bound") {
                out.push(blocker(
                    BlockerKind::UnboundCriterion,
                    c.position.to_string(),
                    format!(
                        "criterion {} has no passing evidence: {}; `frob milestone evidence add {} --provider <p> --ref <r> --accepts {}`",
                        c.position, c.text, input.version, c.position
                    ),
                ));
            }
            for f in &m.pm034 {
                out.push(blocker(BlockerKind::Pm034, &input.version, f.clone()));
            }
        }
    }
    for t in &input.open_tickets {
        out.push(blocker(
            BlockerKind::OpenTicket,
            &t.handle,
            format!("{} is {}: {}", t.handle, t.category, t.title),
        ));
    }
    out.extend(ci_blocker(&input.ci));
    match &input.changelog {
        ChangelogFacts::Valid { .. } => {}
        ChangelogFacts::InvalidFragments(errs) => {
            for (file, msg) in errs {
                out.push(blocker(BlockerKind::InvalidFragment, file, msg.clone()));
            }
        }
        ChangelogFacts::Refused(msg) => {
            out.push(blocker(BlockerKind::Changelog, "CHANGELOG.md", msg.clone()));
        }
    }
    out
}

/// `abc1234` for a sha, `the base branch tip` when it did not resolve.
fn short(sha: Option<&str>) -> String {
    sha.map_or_else(
        || "the base branch tip".to_owned(),
        |s| format!("commit {}", &s[..s.len().min(12)]),
    )
}

/// Red and pending always block; unknown blocks only under `require_ci`; green adds nothing.
fn ci_blocker(ci: &CiFacts) -> Option<Blocker> {
    let at = short(ci.sha.as_deref());
    let subject = ci.sha.clone().unwrap_or_else(|| "base".to_owned());
    match &ci.state {
        CiState::Green { .. } => None,
        CiState::Red { failures } => {
            let list: Vec<String> = failures
                .iter()
                .map(|f| match &f.url {
                    Some(u) => format!("{} ({}) {u}", f.name, f.conclusion),
                    None => format!("{} ({})", f.name, f.conclusion),
                })
                .collect();
            Some(blocker(
                BlockerKind::CiRed,
                subject,
                format!(
                    "CI is red on {at}: {}; fix it and push, then rerun",
                    list.join("; ")
                ),
            ))
        }
        CiState::Pending { running } => Some(blocker(
            BlockerKind::CiPending,
            subject,
            format!(
                "CI still running on {at}: {}; rerun when it finishes",
                running.join(", ")
            ),
        )),
        CiState::Unknown(u) => ci.require.then(|| {
            blocker(
                BlockerKind::CiUnknown,
                subject,
                format!("CI status of {at} is unknown: {}; {}", u.reason, u.remedy),
            )
        }),
    }
}

/// The CI part of the report.
fn ci_report(ci: &CiFacts) -> CiReport {
    let at = short(ci.sha.as_deref());
    let (state, detail) = match &ci.state {
        CiState::Green { checks } => (
            "green",
            format!("all {checks} check(s) on {at} succeeded or were skipped"),
        ),
        CiState::Red { .. } => ("red", ci_blocker(ci).map(|b| b.detail).unwrap_or_default()),
        CiState::Pending { .. } => (
            "pending",
            ci_blocker(ci).map(|b| b.detail).unwrap_or_default(),
        ),
        CiState::Unknown(u) => ("unknown", format!("{}; {}", u.reason, u.remedy)),
    };
    CiReport {
        sha: ci.sha.clone(),
        state: state.to_owned(),
        detail,
        required: ci.require,
    }
}

fn fragments_of(c: &ChangelogFacts) -> (FragmentsStatus, Option<String>) {
    match c {
        ChangelogFacts::Valid { fragments, section } => (
            FragmentsStatus {
                state: "valid".to_owned(),
                fragments: fragments.clone(),
                errors: Vec::new(),
            },
            section.clone(),
        ),
        ChangelogFacts::InvalidFragments(errs) => (
            FragmentsStatus {
                state: "invalid".to_owned(),
                fragments: Vec::new(),
                errors: errs.iter().map(|(_, m)| m.clone()).collect(),
            },
            None,
        ),
        ChangelogFacts::Refused(m) => (
            FragmentsStatus {
                state: "refused".to_owned(),
                fragments: Vec::new(),
                errors: vec![m.clone()],
            },
            None,
        ),
    }
}

/// Plural-aware `N blocker(s)`.
fn count_blockers(n: usize) -> String {
    format!("{n} blocker{}", if n == 1 { "" } else { "s" })
}

fn glance(r: &Report, input: &Input) -> Vec<String> {
    let mut l = vec![format!("{}: {}", r.version, r.verdict)];
    if let Some(m) = &input.milestone {
        l.push(format!("milestone {} ({}): {}", m.handle, m.state, m.goal));
        for e in &m.epics {
            l.push(format!("  epic {e}"));
        }
    }
    l.push(format!("exit criteria ({}):", r.criteria.len()));
    for c in &r.criteria {
        let by: Vec<String> = c
            .evidence
            .iter()
            .map(|e| {
                e.label
                    .clone()
                    .unwrap_or_else(|| format!("{}:{}", e.provider, e.reference))
            })
            .collect();
        let tail = if by.is_empty() {
            String::new()
        } else {
            format!(" [{}]", by.join(", "))
        };
        l.push(format!("  {}. {} {}{tail}", c.position, c.state, c.text));
    }
    let open: usize = r.open_tickets.iter().map(|g| g.tickets.len()).sum();
    l.push(format!("open tickets ({open}):"));
    for g in &r.open_tickets {
        l.push(format!("  {}:", g.category));
        for t in &g.tickets {
            l.push(format!("    {} {}", t.handle, t.title));
        }
    }
    l.push(format!("PM034 findings ({}):", r.pm034.len()));
    for f in &r.pm034 {
        l.push(format!("  {f}"));
    }
    l.push(format!("CI: {} ({})", r.ci.state, r.ci.detail));
    l.push(format!("fragments: {}", r.fragments.state));
    for e in &r.fragments.errors {
        l.push(format!("  {e}"));
    }
    match (&r.changelog_preview, r.fragments.state.as_str()) {
        (Some(_), _) => l.push(format!(
            "changelog preview: {} fragment(s), shown in changelog_preview",
            r.fragments.fragments.len()
        )),
        (None, "valid") => l.push("changelog preview: no fragments yet".to_owned()),
        _ => {}
    }
    l.push(format!(
        "shipped without a changelog note ({}):",
        r.changelog_exempt.len()
    ));
    for t in &r.changelog_exempt {
        l.push(format!(
            "  {} {} (by {}: {})",
            t.handle, t.title, t.actor, t.reason
        ));
    }
    l.push("unresolved:".to_owned());
    for u in &r.unresolved {
        l.push(format!("  {}: {}", u.item, u.reason));
    }
    l
}

/// Assess readiness: collect blockers from the facts, add the unresolved items, state the verdict.
#[must_use]
pub fn assess(input: &Input) -> Report {
    let blockers = blockers_of(input);
    let ready = blockers.is_empty();
    let verdict = if ready {
        "READY".to_owned()
    } else {
        format!("NOT READY: {}", count_blockers(blockers.len()))
    };
    let (fragments, changelog_preview) = fragments_of(&input.changelog);
    let mut report = Report {
        at_a_glance: Vec::new(),
        blockers,
        ci: ci_report(&input.ci),
        changelog_preview,
        criteria: input
            .milestone
            .as_ref()
            .map(|m| m.criteria.clone())
            .unwrap_or_default(),
        changelog_exempt: input.exempt_tickets.clone(),
        fragments,
        milestone: input.milestone.as_ref().map(|m| m.handle.clone()),
        open_tickets: group(&input.open_tickets),
        pm034: input
            .milestone
            .as_ref()
            .map(|m| m.pm034.clone())
            .unwrap_or_default(),
        ready,
        unresolved: unresolved_of(input),
        verdict,
        version: input.version.clone(),
    };
    report.at_a_glance = glance(&report, input);
    tracing::info!(version = %report.version, ready, blockers = report.blockers.len(), "release status assessed");
    report
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ci::{CiFailure, CiUnknown};

    // frob:ticket 01M41EBQN0HT7956KPP0ZJET37
    #[test]
    fn registry_setup_names_an_existing_guide_section() {
        let item = unresolved_items()
            .into_iter()
            .find(|i| i.item == "registry setup")
            .expect("registry setup item");
        let (path, anchor) = REGISTRY_SETUP_GUIDE.split_once('#').expect("anchor");
        assert!(
            item.reason.contains(REGISTRY_SETUP_GUIDE),
            "{}",
            item.reason
        );
        let file = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .join(path);
        let text = std::fs::read_to_string(&file).expect("guide exists");
        assert!(
            text.lines().any(|l| l.starts_with('#')
                && l.trim_start_matches('#')
                    .trim()
                    .to_lowercase()
                    .replace(' ', "-")
                    == anchor),
            "no heading for anchor {anchor}"
        );
    }

    fn crit(n: usize, bound: bool) -> CriterionStatus {
        CriterionStatus {
            position: n,
            text: format!("c{n}"),
            state: if bound { "bound" } else { "unbound" }.to_owned(),
            evidence: if bound {
                vec![EvidenceRef {
                    provider: "cargo-test".to_owned(),
                    reference: "ws".to_owned(),
                    label: None,
                }]
            } else {
                Vec::new()
            },
        }
    }

    fn ci(state: CiState, require: bool) -> CiFacts {
        CiFacts {
            sha: Some("0123456789abcdef".to_owned()),
            state,
            require,
        }
    }

    fn unknown() -> CiState {
        CiState::Unknown(CiUnknown {
            reason: "gh is not installed".to_owned(),
            remedy: "install gh".to_owned(),
        })
    }

    fn input(criteria: Vec<CriterionStatus>) -> Input {
        Input {
            version: "0.532.0".to_owned(),
            milestone: Some(MilestoneFacts {
                handle: "~M".to_owned(),
                goal: "g".to_owned(),
                state: "open".to_owned(),
                epics: Vec::new(),
                criteria,
                pm034: Vec::new(),
            }),
            open_tickets: Vec::new(),
            exempt_tickets: Vec::new(),
            changelog: ChangelogFacts::Valid {
                fragments: vec!["a.added.md".to_owned()],
                section: Some("## 0.532.0\n".to_owned()),
            },
            ci: ci(CiState::Green { checks: 3 }, true),
        }
    }

    #[test]
    fn all_bound_is_ready_with_preview_and_unresolved_lines() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let r = assess(&input(vec![crit(1, true)]));
        assert!(r.ready && r.blockers.is_empty());
        assert_eq!(r.verdict, "READY");
        assert!(r.changelog_preview.is_some());
        assert_eq!(r.unresolved.len(), 2, "green CI adds no unresolved line");
        assert_eq!(r.ci.state, "green");
        assert!(r.at_a_glance[0].ends_with("READY"));
    }

    #[test]
    fn an_unbound_criterion_is_one_typed_blocker() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let r = assess(&input(vec![crit(1, true), crit(2, false)]));
        assert_eq!(r.verdict, "NOT READY: 1 blocker");
        assert_eq!(r.blockers[0].kind, BlockerKind::UnboundCriterion);
        assert_eq!(r.blockers[0].subject, "2");
    }

    #[test]
    fn exempt_tickets_are_listed_in_the_report_and_never_block() {
        // frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
        // frob:tests crates/frob-release/src/status.rs::assess
        let mut i = input(vec![crit(1, true)]);
        i.exempt_tickets = vec![ExemptTicket {
            handle: "~DOC1".to_owned(),
            title: "Design doc".to_owned(),
            actor: "lognd".to_owned(),
            reason: "design only".to_owned(),
        }];
        let r = assess(&i);
        assert!(r.ready, "an exemption is not a blocker");
        assert_eq!(r.changelog_exempt[0].handle, "~DOC1");
        assert!(
            r.at_a_glance
                .iter()
                .any(|l| l.contains("~DOC1") && l.contains("design only"))
        );
    }

    #[test]
    fn open_tickets_group_by_category_in_workflow_order() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let t = |h: &str, c: &str| OpenTicket {
            handle: h.to_owned(),
            title: "x".to_owned(),
            category: c.to_owned(),
        };
        let mut i = input(Vec::new());
        i.open_tickets = vec![t("~A", "in-progress"), t("~B", "todo"), t("~C", "todo")];
        let r = assess(&i);
        let cats: Vec<&str> = r.open_tickets.iter().map(|g| g.category.as_str()).collect();
        assert_eq!(cats, ["todo", "in-progress"]);
        assert_eq!(r.verdict, "NOT READY: 3 blockers");
    }

    #[test]
    fn missing_milestone_and_bad_fragments_are_blockers_not_failures() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let mut i = input(Vec::new());
        i.milestone = None;
        i.changelog =
            ChangelogFacts::InvalidFragments(vec![("bad.md".to_owned(), "bad".to_owned())]);
        let r = assess(&i);
        let kinds: Vec<BlockerKind> = r.blockers.iter().map(|b| b.kind).collect();
        assert_eq!(
            kinds,
            [BlockerKind::NoMilestone, BlockerKind::InvalidFragment]
        );
        assert_eq!(r.fragments.state, "invalid");
        assert!(r.changelog_preview.is_none());
    }

    #[test]
    fn red_ci_is_one_blocker_naming_checks_and_links() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let mut i = input(vec![crit(1, true)]);
        i.ci = ci(
            CiState::Red {
                failures: vec![CiFailure {
                    name: "lint".to_owned(),
                    conclusion: "failure".to_owned(),
                    url: Some("https://x/1".to_owned()),
                }],
            },
            false,
        );
        let r = assess(&i);
        assert_eq!(r.verdict, "NOT READY: 1 blocker");
        assert_eq!(r.blockers[0].kind, BlockerKind::CiRed);
        assert!(r.blockers[0].detail.contains("lint (failure) https://x/1"));
        assert!(r.blockers[0].detail.contains("0123456789ab"));
        assert_eq!(r.ci.state, "red");
    }

    #[test]
    fn pending_ci_blocks_even_when_not_required() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let mut i = input(vec![crit(1, true)]);
        i.ci = ci(
            CiState::Pending {
                running: vec!["test".to_owned()],
            },
            false,
        );
        let r = assess(&i);
        assert_eq!(r.blockers[0].kind, BlockerKind::CiPending);
        assert!(r.blockers[0].detail.contains("CI still running"));
    }

    #[test]
    fn unknown_ci_blocks_when_required_and_only_warns_when_not() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let mut i = input(vec![crit(1, true)]);
        i.ci = ci(unknown(), true);
        let r = assess(&i);
        assert_eq!(r.blockers[0].kind, BlockerKind::CiUnknown);
        assert!(
            r.unresolved[0]
                .reason
                .contains("gh is not installed; install gh")
        );
        assert!(
            r.unresolved[0]
                .item
                .starts_with("CI status on commit 0123456789ab")
        );

        i.ci = ci(unknown(), false);
        let r = assess(&i);
        assert!(
            r.ready,
            "unknown is a warning only when require_ci is false"
        );
        assert_eq!(r.ci.state, "unknown");
        assert!(
            r.unresolved[0].reason.contains("install gh"),
            "still Unresolved"
        );
    }
}
