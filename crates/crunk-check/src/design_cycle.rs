//! UX001 and UX002: the design-cycle pack's first two rules, wired into `crunk check`. Opt-in
//! through `[packs] design_cycle = true` (docs/design/crunk/crunk.md section 8); the judgement is
//! [`crunk_rules::ux`], so this module only gathers the project's facts and turns the findings
//! into rule findings.
//!
//! - UX001 `route-has-screen`: a `design/ia/sitemap.toml` route no screen serves.
//! - UX002 `flow-dead-end`: a `design/flows/*.flow.toml` state with no way out. A state whose
//!   name (the part after `:`) is `done`, `end`, `exit`, `complete`, `completed` or `success`
//!   ends the flow on purpose and is not a dead end.

// frob:ticket 01M4CXSFVWX6H3PNV29ZTQ7YT9

use std::collections::{BTreeMap, BTreeSet};

use crunk_rules::ux::flows::{FlowFinding, FlowIssue, FlowNotes, check_flow_rules};
use crunk_rules::ux::ia::{IaFacts, IaFinding, IaIssue, ScreenRoute, check_ia};
use gob_check::{RepoGroup, Snapshot};
use gob_rules::{Finding, Rule, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};

use crate::Crunk;

/// A sitemap route has no screen.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "UX001",
    slug = "route-has-screen",
    family = "UX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Ux001;

/// A flow state has no way out.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "UX002",
    slug = "flow-dead-end",
    family = "UX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Ux002;

/// State names that end a flow on purpose.
const TERMINAL_STATES: [&str; 6] = ["done", "end", "exit", "complete", "completed", "success"];

/// True when the pack is switched on for this project.
fn enabled(snap: &Snapshot<Crunk>) -> bool {
    snap.inputs
        .spec
        .as_ref()
        .is_some_and(|s| s.packs.design_cycle)
}

/// Bytes that change when the sitemap changes; empty when the pack is off. (Flows are already in
/// the repo digest.)
pub fn fingerprint(snap: &Snapshot<Crunk>) -> Vec<u8> {
    let Some(spec) = snap.inputs.spec.as_ref().filter(|s| s.packs.design_cycle) else {
        return Vec::new();
    };
    let facts = IaFacts::load(spec);
    format!("design-cycle/1/{:?}", facts.source).into_bytes()
}

/// The byte offset where one-based `line` of `text` starts.
fn line_start(text: &str, line: usize) -> u32 {
    let offset: usize = text
        .split_inclusive('\n')
        .take(line.saturating_sub(1))
        .map(str::len)
        .sum();
    u32::try_from(offset).unwrap_or(0)
}

/// The flow annotations the pack derives from state names: the terminal states.
fn notes_of(snap: &Snapshot<Crunk>) -> BTreeMap<String, FlowNotes> {
    let Some(flows) = &snap.inputs.flows else {
        return BTreeMap::new();
    };
    flows
        .files
        .iter()
        .map(|(path, flow)| {
            let terminal: BTreeSet<String> = flow
                .nodes
                .iter()
                .filter(|n| {
                    let state = n.split_once(':').map_or(n.as_str(), |(_, s)| s);
                    TERMINAL_STATES.contains(&state.to_lowercase().as_str())
                })
                .cloned()
                .collect();
            (
                path.clone(),
                FlowNotes {
                    terminal,
                    ..FlowNotes::default()
                },
            )
        })
        .collect()
}

/// UX001 findings: sitemap routes without a screen.
fn ia_findings(snap: &Snapshot<Crunk>, files: &mut FileInterner) -> Vec<Finding> {
    let Some(spec) = &snap.inputs.spec else {
        return Vec::new();
    };
    let screens: Vec<ScreenRoute> = spec
        .screens
        .values()
        .map(|s| ScreenRoute {
            id: s.id.clone(),
            entry: s.entry.clone(),
        })
        .collect();
    let facts = IaFacts::load(spec);
    let found: Vec<IaFinding> = check_ia(&facts, &screens, Some(&[]))
        .into_iter()
        .filter(|f| matches!(f.issue, IaIssue::RouteWithoutScreen | IaIssue::Schema))
        .collect();
    let Ok(id) = Ux001.meta().rule_id() else {
        return Vec::new();
    };
    let text = facts
        .source
        .as_ref()
        .map(|(_, t)| t.as_str())
        .unwrap_or_default();
    found
        .into_iter()
        .map(|f| {
            let at = TextSize::from(f.line.map_or(0, |l| line_start(text, l)));
            let span = Span::new(files.intern(&f.path), TextRange::at(at, TextSize::from(0)));
            tracing::debug!(path = %f.path, message = %f.message, "UX001 fires");
            if f.issue == IaIssue::Schema {
                let message = format!(
                    "the sitemap cannot be read, so route/screen agreement is undecided: {}",
                    f.message
                );
                return Finding::new(
                    id.clone(),
                    Severity::Unresolved,
                    Some(span),
                    message,
                    &f.path,
                )
                .with_reason(UnresolvedReason::from_code("sitemap-invalid"));
            }
            Finding::new(id.clone(), Severity::Error, Some(span), f.message, &f.path)
        })
        .collect()
}

/// UX002 findings: flow states that are dead ends.
fn flow_findings(snap: &Snapshot<Crunk>, files: &mut FileInterner) -> Vec<Finding> {
    let Some(flows) = &snap.inputs.flows else {
        return Vec::new();
    };
    let Ok(id) = Ux002.meta().rule_id() else {
        return Vec::new();
    };
    let found: Vec<FlowFinding> = check_flow_rules(flows, &notes_of(snap), &[])
        .into_iter()
        .filter(|f| f.issue == FlowIssue::DeadEnd)
        .collect();
    let mut out: Vec<Finding> = flows
        .problems
        .iter()
        .map(|p| {
            let span = Span::new(
                files.intern(&p.path),
                TextRange::at(TextSize::from(0), TextSize::from(0)),
            );
            let message = format!(
                "the flow file cannot be read, so its dead ends are undecided: {}",
                p.message
            );
            Finding::new(
                id.clone(),
                Severity::Unresolved,
                Some(span),
                message,
                &p.path,
            )
            .with_reason(UnresolvedReason::from_code("flow-file-invalid"))
        })
        .collect();
    out.extend(found.into_iter().map(|f| {
        let span = Span::new(
            files.intern(&f.path),
            TextRange::at(TextSize::from(0), TextSize::from(0)),
        );
        tracing::debug!(path = %f.path, subject = %f.subject, "UX002 fires");
        Finding::new(id.clone(), Severity::Error, Some(span), f.message, &f.path)
    }));
    out
}

/// The repo group that emits UX001 and UX002; silent unless `[packs] design_cycle` is on.
pub fn group() -> RepoGroup<Crunk> {
    RepoGroup::new(
        "repo:design-cycle",
        vec![Ux001.meta(), Ux002.meta()],
        |snap: &Snapshot<Crunk>, files: &mut FileInterner| {
            if !enabled(snap) {
                return Vec::new();
            }
            let mut out = ia_findings(snap, files);
            out.extend(flow_findings(snap, files));
            out
        },
    )
}
