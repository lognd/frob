//! Offline package metadata (`.grimble/vet-meta.toml`): licence, yanked and maintenance checks.
//!
//! `Cargo.lock` carries none of this, so the maintainer exports it from the registry once and
//! commits it; the vet pass then stays pure over text, like the advisory snapshot.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

use serde::Deserialize;

use crate::VetError;
use crate::lockfile::Package;
use crate::vet::{Allowlist, Finding, Rule, Severity};

/// Default maintenance horizon: a release older than this many days is stale.
pub const DEFAULT_MAX_AGE_DAYS: i64 = 730;

/// The metadata file: a policy and one record per crate version.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Meta {
    /// The date the metadata was exported (`YYYY-MM-DD`); maintenance is measured against it.
    #[serde(default)]
    pub as_of: Option<String>,
    /// Policy knobs.
    #[serde(default)]
    pub policy: Policy,
    /// Per-version records.
    #[serde(default)]
    pub package: Vec<Record>,
}

/// Policy knobs of the metadata file.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Policy {
    /// SPDX identifiers a dependency may be licensed under; absent disables VET005.
    #[serde(default)]
    pub allowed_licenses: Option<Vec<String>>,
    /// Days since the last release after which a crate counts as unmaintained.
    #[serde(default)]
    pub max_age_days: Option<i64>,
}

/// What the registry says about one crate version.
#[derive(Debug, Clone, Deserialize)]
pub struct Record {
    /// Crate name.
    pub name: String,
    /// Version the record describes.
    pub version: String,
    /// SPDX licence expression as published; absent when the crate declares none.
    #[serde(default)]
    pub license: Option<String>,
    /// True when the version was yanked from the registry.
    #[serde(default)]
    pub yanked: bool,
    /// Date of the crate's most recent release (`YYYY-MM-DD`).
    #[serde(default)]
    pub last_release: Option<String>,
}

impl Meta {
    /// Parse the metadata file text.
    ///
    /// # Errors
    /// [`VetError::Parse`] on invalid TOML.
    pub fn parse(text: &str) -> Result<Self, VetError> {
        toml::from_str(text).map_err(|e| VetError::Parse {
            what: "vet metadata".to_owned(),
            message: e.to_string(),
        })
    }

    /// The record for `name` at `version`, if exported.
    pub fn record(&self, name: &str, version: &str) -> Option<&Record> {
        self.package
            .iter()
            .find(|r| r.name == name && r.version == version)
    }

    /// True when the policy lists allowed licences (VET005 applies).
    pub fn checks_licences(&self) -> bool {
        self.policy.allowed_licenses.is_some()
    }

    /// True when the export date is known and parses (VET007 applies).
    pub fn checks_maintenance(&self) -> bool {
        self.as_of.as_deref().and_then(parse_date).is_some()
    }
}

/// Days since 1970-01-01 of the civil date `y-m-d` (proleptic Gregorian).
fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (m + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

/// Parse `YYYY-MM-DD` into days since the epoch; `None` when malformed.
pub fn parse_date(text: &str) -> Option<i64> {
    let mut parts = text.trim().splitn(3, '-');
    let y: i64 = parts.next()?.parse().ok()?;
    let m: i64 = parts.next()?.parse().ok()?;
    let d: i64 = parts.next()?.get(..2)?.parse().ok()?;
    ((1..=12).contains(&m) && (1..=31).contains(&d)).then(|| days_from_civil(y, m, d))
}

/// Tokens of an SPDX expression, with the legacy `/` separator read as `OR`.
fn tokens(expr: &str) -> Vec<String> {
    expr.replace('/', " OR ")
        .replace('(', " ( ")
        .replace(')', " ) ")
        .split_whitespace()
        .map(str::to_owned)
        .collect()
}

/// A cursor over SPDX tokens evaluating `OR`/`AND`/`WITH` against an allowed set.
struct Spdx<'a> {
    toks: Vec<String>,
    pos: usize,
    allowed: &'a [String],
}

impl Spdx<'_> {
    /// The next token without consuming it.
    fn peek(&self) -> Option<&str> {
        self.toks.get(self.pos).map(String::as_str)
    }

    /// `and ("OR" and)*`: satisfied when any alternative is.
    fn expr(&mut self) -> bool {
        let mut ok = self.and();
        while self.peek() == Some("OR") {
            self.pos += 1;
            let rhs = self.and();
            ok = ok || rhs;
        }
        ok
    }

    /// `atom ("AND" atom)*`: satisfied when every term is.
    fn and(&mut self) -> bool {
        let mut ok = self.atom();
        while self.peek() == Some("AND") {
            self.pos += 1;
            let rhs = self.atom();
            ok = ok && rhs;
        }
        ok
    }

    /// A parenthesised expression or a licence id with optional `+` and `WITH exception`.
    fn atom(&mut self) -> bool {
        match self.peek() {
            Some("(") => {
                self.pos += 1;
                let ok = self.expr();
                if self.peek() == Some(")") {
                    self.pos += 1;
                }
                ok
            }
            Some(id) => {
                let id = id.trim_end_matches('+').to_owned();
                self.pos += 1;
                if self.peek() == Some("WITH") {
                    self.pos += 2;
                }
                self.allowed.iter().any(|a| *a == id)
            }
            None => false,
        }
    }
}

/// True when the SPDX `expr` can be satisfied using only `allowed` licences.
pub fn licence_allowed(expr: &str, allowed: &[String]) -> bool {
    let mut spdx = Spdx {
        toks: tokens(expr),
        pos: 0,
        allowed,
    };
    spdx.expr()
}

/// Build a finding of `rule` for `p`.
fn finding(rule: Rule, p: &Package, message: String) -> Finding {
    Finding {
        rule,
        severity: Severity::Error,
        package: p.name.clone(),
        version: p.version.clone(),
        message,
        advisory: None,
        fixed: Vec::new(),
    }
}

/// Licence, yanked and maintenance findings for the `examined` packages.
///
/// Packages without a record in `meta` are skipped: nothing is known about them.
pub fn check(examined: &[&Package], meta: &Meta, allow: &Allowlist) -> Vec<Finding> {
    let mut out = Vec::new();
    let as_of = meta.as_of.as_deref().and_then(parse_date);
    let max_age = meta.policy.max_age_days.unwrap_or(DEFAULT_MAX_AGE_DAYS);
    for p in examined {
        let Some(rec) = meta.record(&p.name, &p.version) else {
            tracing::debug!(package = %p.name, version = %p.version, "no metadata record; skipped");
            continue;
        };
        if let Some(allowed) = &meta.policy.allowed_licenses
            && !allow.allows(&p.name, &p.version)
        {
            match rec.license.as_deref() {
                None => out.push(finding(
                    Rule::Licence,
                    p,
                    format!("{} {} declares no licence", p.name, p.version),
                )),
                Some(expr) if !licence_allowed(expr, allowed) => out.push(finding(
                    Rule::Licence,
                    p,
                    format!(
                        "{} {} is licensed {expr}, which the policy does not allow",
                        p.name, p.version
                    ),
                )),
                Some(_) => {}
            }
        }
        if rec.yanked {
            out.push(finding(
                Rule::Yanked,
                p,
                format!("{} {} was yanked from the registry", p.name, p.version),
            ));
        }
        if let (Some(now), Some(last)) = (as_of, rec.last_release.as_deref().and_then(parse_date))
            && now - last > max_age
            && !allow.allows(&p.name, &p.version)
        {
            out.push(finding(
                Rule::Maintenance,
                p,
                format!(
                    "{} has had no release for {} days (limit {max_age})",
                    p.name,
                    now - last
                ),
            ));
        }
    }
    tracing::info!(findings = out.len(), "metadata checks done");
    out
}
