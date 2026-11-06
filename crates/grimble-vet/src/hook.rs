//! `grimble vet --hook`: vet one install-shaped shell command before it runs.
//!
//! Not a tree scan. The command (`cargo add serde`, `cargo install ripgrep@14.0.0`) is parsed into
//! the crates it would pull in, and each is checked against the allowlist and the offline advisory
//! snapshot before any lockfile exists. Pure over text, like the rest of the crate.

// frob:ticket 01M5A63SWXWW1XVF33Q1AB6CHH

use semver::Version;

use crate::advisory::Snapshot;
use crate::typosquat::lookalike;
use crate::vet::{Allowlist, Finding, Rule, Severity, VetReport};

/// One crate an install-shaped command would fetch from a registry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallRequest {
    /// Crate name.
    pub name: String,
    /// Pinned version (`name@1.2.3` or `--version 1.2.3`); `None` means "latest".
    pub version: Option<String>,
}

/// Flags of `cargo add` / `cargo install` that consume the next token as their value.
const VALUE_FLAGS: [&str; 17] = [
    "-F",
    "--features",
    "--git",
    "--path",
    "--registry",
    "--rename",
    "--root",
    "--bin",
    "--example",
    "--branch",
    "--tag",
    "--rev",
    "--target",
    "--manifest-path",
    "-p",
    "--package",
    "--index",
];

/// Split a shell line into simple commands at `&&`, `||`, `;`, `|`, `&` and newlines.
fn simple_commands(line: &str) -> Vec<&str> {
    line.split(['&', '|', ';', '\n'])
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect()
}

/// The registry crates one simple command installs; empty when it is not `cargo add|install`.
fn parse_simple(cmd: &str) -> Vec<InstallRequest> {
    let mut tokens = cmd.split_whitespace().map(|t| t.trim_matches(['"', '\'']));
    if tokens.next() != Some("cargo") {
        return Vec::new();
    }
    let mut tokens = tokens.skip_while(|t| t.starts_with('+')); // toolchain override
    if !matches!(tokens.next(), Some("add" | "install")) {
        return Vec::new();
    }
    let mut out = Vec::new();
    let mut version_flag: Option<String> = None;
    let mut non_registry = false;
    while let Some(tok) = tokens.next() {
        if tok == "--version" || tok == "--vers" {
            version_flag = tokens.next().map(str::to_owned);
        } else if let Some(v) = tok.strip_prefix("--version=") {
            version_flag = Some(v.to_owned());
        } else if tok == "--git" || tok == "--path" {
            non_registry = true;
            tokens.next();
        } else if VALUE_FLAGS.contains(&tok) {
            tokens.next();
        } else if tok.starts_with('-') || tok.contains('=') {
            // boolean flag, or `--flag=value`
        } else {
            let (name, version) = match tok.split_once('@') {
                Some((n, v)) => (n, Some(v.to_owned())),
                None => (tok, None),
            };
            out.push(InstallRequest {
                name: name.to_owned(),
                version,
            });
        }
    }
    if non_registry {
        tracing::debug!(cmd, "git/path install has no registry crate to vet");
        return Vec::new();
    }
    if let [only] = out.as_mut_slice() {
        only.version = only.version.take().or(version_flag);
    }
    out
}

/// Parse `command` into the registry crates it would install (empty for any other command).
pub fn parse_install(command: &str) -> Vec<InstallRequest> {
    let out: Vec<_> = simple_commands(command)
        .into_iter()
        .flat_map(parse_simple)
        .collect();
    tracing::debug!(requests = out.len(), "hook command parsed");
    out
}

/// True when any allowlist entry vets `name` at some version (an unpinned install).
fn allows_any_version(allow: &Allowlist, name: &str) -> bool {
    let prefix = format!("{name}@");
    allow
        .allow
        .iter()
        .any(|a| a == name || a.starts_with(&prefix))
}

/// Vet the crates `command` would install; the command may run when the report has no errors.
///
/// A crate off the allowlist is VET001; a pinned version with an advisory is VET002, and an
/// unpinned crate is VET002 only when an advisory against it has no fix. A name one edit from a
/// well-known crate is VET008.
pub fn vet_command(command: &str, allow: &Allowlist, snapshot: &Snapshot) -> VetReport {
    let requests = parse_install(command);
    let mut findings = Vec::new();
    for r in &requests {
        let shown = r.version.clone().unwrap_or_else(|| "*".to_owned());
        let vetted = match &r.version {
            Some(v) => allow.allows(&r.name, v),
            None => allows_any_version(allow, &r.name),
        };
        if !vetted {
            findings.push(Finding {
                rule: Rule::UnvettedDirect,
                severity: Severity::Error,
                package: r.name.clone(),
                version: shown.clone(),
                message: format!("{} {shown} is not vetted; add it to the allowlist", r.name),
                advisory: None,
                fixed: Vec::new(),
            });
        }
        let trusted: Vec<String> = allow.names().collect();
        if let Some(real) = lookalike(&r.name, &trusted) {
            findings.push(Finding {
                rule: Rule::Typosquat,
                severity: Severity::Error,
                package: r.name.clone(),
                version: shown.clone(),
                message: format!("{} is one edit from the well-known crate {real}", r.name),
                advisory: None,
                fixed: Vec::new(),
            });
        }
        let advisories = match r.version.as_deref().map(Version::parse) {
            Some(Ok(v)) => snapshot.affecting(&r.name, &v),
            Some(Err(_)) => Vec::new(),
            None => snapshot.unfixed(&r.name),
        };
        for a in advisories {
            findings.push(Finding {
                rule: Rule::Advisory,
                severity: Severity::Error,
                package: r.name.clone(),
                version: shown.clone(),
                message: format!("{}: {} ({} {shown})", a.id, a.title, r.name),
                advisory: Some(a.id.clone()),
                fixed: a.fixed(),
            });
        }
    }
    findings.sort_by(|a, b| (&a.package, a.rule as u8).cmp(&(&b.package, b.rule as u8)));
    tracing::info!(
        examined = requests.len(),
        findings = findings.len(),
        "hook vet done"
    );
    VetReport {
        examined: requests.len(),
        findings,
    }
}
