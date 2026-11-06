//! The vet pass as a rule family: lockfile text in, [`Verdict`]s out, for the product pipeline.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

use std::collections::BTreeMap;

use gob_rules::{Severity, UnresolvedReason};
use grimble_verdict::Verdict;

use crate::advisory::Snapshot;
use crate::lockfile::{examined, parse_lockfile};
use crate::meta::{self, Meta};
use crate::vet::{Allowlist, Rule, vet_with_meta};

/// The file every vet finding points into.
pub const LOCKFILE: &str = "Cargo.lock";

/// Every vet rule id.
pub const RULES: [&str; 8] = [
    "VET001", "VET002", "VET003", "VET004", "VET005", "VET006", "VET007", "VET008",
];

/// Inputs of one vet pass; every part is optional because a repo may lack any of them.
#[derive(Debug, Default)]
pub struct VetInput<'a> {
    /// `Cargo.lock` text at head; `None` when the repo has no lockfile.
    pub lock: Option<&'a str>,
    /// `.grimble/vet.toml` text; `None` means an empty allowlist.
    pub allowlist: Option<&'a str>,
    /// The offline advisory snapshot; `None` when no snapshot is present.
    pub snapshot: Option<&'a Snapshot>,
    /// `Cargo.lock` text at the base ref; `None` when the run has no base.
    pub base: Option<&'a str>,
    /// `.grimble/vet-meta.toml` text; `None` when no registry metadata was exported.
    pub meta: Option<&'a str>,
}

/// What the vet pass found and examined.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct VetPassReport {
    /// Findings, in the order the vet engine reports them.
    pub findings: Vec<Verdict>,
    /// Packages examined per applicable rule.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Rules whose inputs are absent here (rule id to the reason), so zero subjects is not a gap.
    pub not_applicable: BTreeMap<&'static str, String>,
}

/// The static id of a vet rule.
fn id_of(rule: Rule) -> &'static str {
    match rule {
        Rule::UnvettedDirect => RULES[0],
        Rule::Advisory => RULES[1],
        Rule::NewTransitive => RULES[2],
        Rule::Duplicate => RULES[3],
        Rule::Licence => RULES[4],
        Rule::Yanked => RULES[5],
        Rule::Maintenance => RULES[6],
        Rule::Typosquat => RULES[7],
    }
}

/// Mark every rule not applicable for `why`.
fn all_not_applicable(report: &mut VetPassReport, why: &str) {
    for id in RULES {
        report.not_applicable.insert(id, why.to_owned());
    }
}

/// An unresolved verdict for an input that does not parse.
fn unreadable(what: &str, message: &str) -> Verdict {
    Verdict::unresolved(
        RULES[1],
        UnresolvedReason::ParseFailed,
        (LOCKFILE, (0, 0)),
        format!("cannot read {what}: {message}"),
        format!("unreadable:{what}"),
    )
}

/// Run the vet rules over `input`.
#[allow(clippy::too_many_lines)]
pub fn analyze(input: &VetInput<'_>) -> VetPassReport {
    let mut report = VetPassReport::default();
    let Some(lock) = input.lock else {
        tracing::debug!("no Cargo.lock in the walk; VET rules do not apply");
        all_not_applicable(&mut report, "no Cargo.lock in the walk");
        return report;
    };
    let head = match parse_lockfile(lock) {
        Ok(p) => p,
        Err(err) => {
            tracing::warn!(%err, "Cargo.lock does not parse; VET is unresolved");
            report.findings.push(unreadable(LOCKFILE, &err.to_string()));
            return report;
        }
    };
    let allow = match input.allowlist.map(Allowlist::parse).transpose() {
        Ok(a) => a.unwrap_or_default(),
        Err(err) => {
            tracing::warn!(%err, "vet allowlist does not parse; VET is unresolved");
            report
                .findings
                .push(unreadable("vet allowlist", &err.to_string()));
            return report;
        }
    };
    let base = match input.base.map(parse_lockfile).transpose() {
        Ok(b) => b,
        Err(err) => {
            tracing::warn!(%err, "base Cargo.lock does not parse; VET is unresolved");
            report
                .findings
                .push(unreadable("base Cargo.lock", &err.to_string()));
            return report;
        }
    };
    let meta = match input.meta.map(Meta::parse).transpose() {
        Ok(m) => m,
        Err(err) => {
            tracing::warn!(%err, "vet metadata does not parse; VET is unresolved");
            report
                .findings
                .push(unreadable("vet metadata", &err.to_string()));
            return report;
        }
    };
    let empty = Snapshot::default();
    let snapshot = input.snapshot.unwrap_or(&empty);
    if base.is_none() {
        let why = "needs a base ref to tell new dependencies from old";
        for id in [RULES[0], RULES[2]] {
            report.not_applicable.insert(id, why.to_owned());
        }
    }
    if input.snapshot.is_none() {
        report.not_applicable.insert(
            RULES[1],
            "no advisory snapshot (.grimble/advisory-db)".to_owned(),
        );
    }
    let vetted = vet_with_meta(&head, base.as_deref(), snapshot, &allow, meta.as_ref());
    let no_meta = "no registry metadata (.grimble/vet-meta.toml)";
    match &meta {
        None => {
            for id in [RULES[4], RULES[5], RULES[6]] {
                report.not_applicable.insert(id, no_meta.to_owned());
            }
        }
        Some(m) => {
            if !m.checks_licences() {
                report.not_applicable.insert(
                    RULES[4],
                    "vet-meta.toml has no policy.allowed_licenses".to_owned(),
                );
            }
            if !m.checks_maintenance() {
                report
                    .not_applicable
                    .insert(RULES[6], "vet-meta.toml has no valid as_of date".to_owned());
            }
        }
    }
    tracing::debug!(
        examined = vetted.examined,
        findings = vetted.findings.len(),
        has_base = base.is_some(),
        "vet pass done"
    );
    if base.is_some() && vetted.examined == 0 {
        let why = "no new dependencies relative to the base ref";
        for id in [
            RULES[0], RULES[1], RULES[2], RULES[4], RULES[5], RULES[6], RULES[7],
        ] {
            report
                .not_applicable
                .entry(id)
                .or_insert_with(|| why.to_owned());
        }
    }
    for id in RULES {
        if !report.not_applicable.contains_key(id) {
            let n = if id == RULES[3] {
                head.len()
            } else {
                vetted.examined
            };
            report.subjects.insert(id, n);
        }
    }
    report.findings = vetted
        .findings
        .iter()
        .map(|f| {
            Verdict::fire(
                id_of(f.rule),
                Severity::Error,
                (LOCKFILE, (0, 0)),
                f.message.clone(),
                format!("{}:{}@{}", id_of(f.rule), f.package, f.version),
            )
        })
        .collect();
    report
}
