//! The vetting pass: advisories, unvetted additions and duplicate versions over a lockfile delta.

use std::collections::BTreeSet;

use schemars::JsonSchema;
use semver::Version;
use serde::{Deserialize, Serialize};

use crate::VetError;
use crate::advisory::Snapshot;
use crate::lockfile::{Package, direct_names, versions_by_name};

/// Finding severity; `Error` fails the verb.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    /// Gates (exit 1).
    Error,
    /// Reported only.
    Warning,
    /// Informational.
    Info,
}

/// Vet rule ids.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
pub enum Rule {
    /// A new direct dependency that is not on the allowlist.
    #[serde(rename = "VET001")]
    UnvettedDirect,
    /// A locked version has a `RustSec` advisory.
    #[serde(rename = "VET002")]
    Advisory,
    /// A new transitive dependency that is not on the allowlist.
    #[serde(rename = "VET003")]
    NewTransitive,
    /// Two versions of one crate are locked.
    #[serde(rename = "VET004")]
    Duplicate,
}

/// One vetting finding.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Finding {
    /// Rule id.
    pub rule: Rule,
    /// Severity.
    pub severity: Severity,
    /// Crate name.
    pub package: String,
    /// Locked version (the first for a duplicate).
    pub version: String,
    /// Human message.
    pub message: String,
    /// Advisory id for VET002.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub advisory: Option<String>,
    /// Fixed-version requirements for VET002.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub fixed: Vec<String>,
}

/// The result of one vetting pass.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct VetReport {
    /// Packages examined (the delta when a base was given, else every external package).
    pub examined: usize,
    /// Findings, ordered by package then rule.
    pub findings: Vec<Finding>,
}

impl VetReport {
    /// Number of findings at `Error` severity.
    pub fn errors(&self) -> usize {
        self.findings
            .iter()
            .filter(|f| f.severity == Severity::Error)
            .count()
    }
}

/// Crates a maintainer has vetted: `name` (any version) or `name@version`.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Allowlist {
    /// The entries.
    #[serde(default)]
    pub allow: Vec<String>,
}

impl Allowlist {
    /// Parse the allowlist file (`allow = ["serde", "tokio@1.40.0"]`).
    ///
    /// # Errors
    /// [`VetError::Parse`] on invalid TOML.
    pub fn parse(text: &str) -> Result<Self, VetError> {
        toml::from_str(text).map_err(|e| VetError::Parse {
            what: "vet allowlist".to_owned(),
            message: e.to_string(),
        })
    }

    /// True when `name` at `version` is vetted.
    pub fn allows(&self, name: &str, version: &str) -> bool {
        let pinned = format!("{name}@{version}");
        self.allow.iter().any(|a| a == name || *a == pinned)
    }
}

/// Vet `head`; with `base`, only packages new in `head` are checked for vetting, advisories cover all
/// external packages in the delta (or every one without a base).
pub fn vet(
    head: &[Package],
    base: Option<&[Package]>,
    snapshot: &Snapshot,
    allow: &Allowlist,
) -> VetReport {
    let known: BTreeSet<(&str, &str)> = base
        .unwrap_or_default()
        .iter()
        .map(|p| (p.name.as_str(), p.version.as_str()))
        .collect();
    let direct = direct_names(head);
    let examined: Vec<&Package> = head
        .iter()
        .filter(|p| p.source.is_some())
        .filter(|p| base.is_none() || !known.contains(&(p.name.as_str(), p.version.as_str())))
        .collect();
    let mut findings = Vec::new();
    for p in &examined {
        if let Ok(v) = Version::parse(&p.version) {
            for a in snapshot.affecting(&p.name, &v) {
                findings.push(Finding {
                    rule: Rule::Advisory,
                    severity: Severity::Error,
                    package: p.name.clone(),
                    version: p.version.clone(),
                    message: format!("{}: {} ({} {})", a.id, a.title, p.name, p.version),
                    advisory: Some(a.id.clone()),
                    fixed: a.fixed(),
                });
            }
        }
        if base.is_some() && !allow.allows(&p.name, &p.version) {
            let is_direct = direct.contains(&p.name);
            findings.push(Finding {
                rule: if is_direct {
                    Rule::UnvettedDirect
                } else {
                    Rule::NewTransitive
                },
                severity: if is_direct {
                    Severity::Error
                } else {
                    Severity::Info
                },
                package: p.name.clone(),
                version: p.version.clone(),
                message: format!(
                    "new {} dependency {} {} is not vetted",
                    if is_direct { "direct" } else { "transitive" },
                    p.name,
                    p.version
                ),
                advisory: None,
                fixed: Vec::new(),
            });
        }
    }
    for (name, versions) in versions_by_name(head) {
        if versions.len() > 1 && examined.iter().any(|p| p.name == name) {
            let list: Vec<_> = versions.iter().cloned().collect();
            findings.push(Finding {
                rule: Rule::Duplicate,
                severity: Severity::Warning,
                package: name.clone(),
                version: list[0].clone(),
                message: format!(
                    "{name} is locked at {} versions: {}",
                    list.len(),
                    list.join(", ")
                ),
                advisory: None,
                fixed: Vec::new(),
            });
        }
    }
    findings.sort_by(|a, b| (&a.package, a.rule as u8).cmp(&(&b.package, b.rule as u8)));
    tracing::info!(
        examined = examined.len(),
        findings = findings.len(),
        "vet pass done"
    );
    VetReport {
        examined: examined.len(),
        findings,
    }
}
