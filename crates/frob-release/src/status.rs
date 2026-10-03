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
    /// The changelog dry-run result.
    pub changelog: ChangelogFacts,
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

/// The readiness report for one release.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Report {
    /// The report as lines, verdict first, for the text view.
    pub at_a_glance: Vec<String>,
    /// Every reason the release is not ready.
    pub blockers: Vec<Blocker>,
    /// The changelog section a cut would write; absent without fragments.
    pub changelog_preview: Option<String>,
    /// Exit criteria with their binding state.
    pub criteria: Vec<CriterionStatus>,
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

/// The items the design lists as owner actions or later checks (`releases.md` 6a), with reasons.
#[must_use]
pub fn unresolved_items() -> Vec<Unresolved> {
    let u = |item: &str, reason: &str| Unresolved {
        item: item.to_owned(),
        reason: reason.to_owned(),
    };
    vec![
        u("CI status on the tip", "not checked yet (~4PT3KZB)"),
        u("forecast", "no history yet"),
        u(
            "registry setup",
            "owner action: trusted publishing on PyPI (frob) and crates.io, reserved crate names confirmed",
        ),
    ]
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
        changelog_preview,
        criteria: input
            .milestone
            .as_ref()
            .map(|m| m.criteria.clone())
            .unwrap_or_default(),
        fragments,
        milestone: input.milestone.as_ref().map(|m| m.handle.clone()),
        open_tickets: group(&input.open_tickets),
        pm034: input
            .milestone
            .as_ref()
            .map(|m| m.pm034.clone())
            .unwrap_or_default(),
        ready,
        unresolved: unresolved_items(),
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
            changelog: ChangelogFacts::Valid {
                fragments: vec!["a.added.md".to_owned()],
                section: Some("## 0.532.0\n".to_owned()),
            },
        }
    }

    #[test]
    fn all_bound_is_ready_with_preview_and_unresolved_lines() {
        // frob:tests crates/frob-release/src/status.rs::assess
        let r = assess(&input(vec![crit(1, true)]));
        assert!(r.ready && r.blockers.is_empty());
        assert_eq!(r.verdict, "READY");
        assert!(r.changelog_preview.is_some());
        assert_eq!(r.unresolved.len(), 3);
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
}
