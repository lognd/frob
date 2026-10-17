//! `REL001`: a product release tag that `frob release cut` did not make.
//!
//! Releases are cut by `frob release cut VERSION`, which tags every shipped binary and records
//! a `cut` event on the milestone (`releases.md` sections 4 and 6a). [`evaluate`] lists the
//! repository's product tags (`frob-v*`, `grimble-v*`, `crunk-v*`), and checks each against
//! the recorded cuts: the tag must be named in a cut with the same tag object and commit, and
//! the workspace version committed at that commit (read through `gob-git`, never the working
//! tree) must equal the tag's version.

use crate::ProductTags;
use frob_pm::event::{CutData, TagRecord};
use gob_git::Repo;
use gob_rules::{Finding, RuleDecl, RuleId, Severity};

use crate::rules::rel001::Rel001;
use toml::Table;

/// What [`evaluate`] found.
#[derive(Debug, Clone, Default)]
pub struct Evaluation {
    /// `REL001` findings: Error per offending tag and reason, Unresolved when git cannot answer.
    pub findings: Vec<Finding>,
    /// Product tags examined.
    pub subjects: usize,
    /// Why the rule does not apply here (no product tags, no cuts), when it does not.
    pub not_applicable: Option<String>,
}

/// Why the rule has nothing to examine in a repository with no product tags and no cuts.
const NOT_APPLICABLE: &str =
    "no product tags (per [release] tag and products) and no recorded release cuts";

fn rule_id() -> RuleId {
    Rel001::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("declaration validates the id: {e}"))
}

fn finding(severity: Severity, tag: &str, kind: &str, message: String) -> Finding {
    Finding::new(rule_id(), severity, None, message, &format!("{tag}:{kind}"))
}

/// The workspace version committed at `commit` (hex), read through git.
fn version_at(repo: &Repo, commit: &str) -> Result<String, String> {
    let bytes = repo
        .read_blob_at(commit, "Cargo.toml")
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "there is no Cargo.toml at that commit".to_owned())?;
    let text = String::from_utf8(bytes).map_err(|e| format!("Cargo.toml is not UTF-8: {e}"))?;
    let table = text.parse::<Table>().map_err(|e| {
        format!(
            "Cargo.toml is not valid TOML: {}",
            e.to_string().replace('\n', " ")
        )
    })?;
    table
        .get("workspace")
        .and_then(toml::Value::as_table)
        .and_then(|w| w.get("package"))
        .and_then(toml::Value::as_table)
        .and_then(|p| p.get("version"))
        .and_then(toml::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| "Cargo.toml declares no [workspace.package] version".to_owned())
}

fn recorded<'a>(cuts: &'a [CutData], tag: &str) -> Option<&'a TagRecord> {
    cuts.iter()
        .flat_map(|c| c.tags.iter())
        .find(|t| t.name == tag)
}

/// Every product tag in `repo`, or the reason git could not list them.
fn product_tags(repo: &Repo, products: &ProductTags) -> Result<Vec<String>, String> {
    Ok(repo
        .list_tags()
        .map_err(|e| e.to_string())?
        .into_iter()
        .filter(|n| products.tag_version(n).is_some())
        .collect())
}

/// The configured products of `repo`'s work tree, or the reason they cannot be resolved.
fn products_of(repo: &Repo) -> Result<ProductTags, String> {
    let root = repo
        .work_dir()
        .ok_or_else(|| "the repository has no work tree".to_owned())?;
    ProductTags::load(root).map_err(|e| e.to_string())
}

/// Why `REL001` does not apply to `repo` given `cuts`, or `None` when it does.
#[must_use]
pub fn not_applicable(repo: &Repo, cuts: &[CutData]) -> Option<String> {
    let Ok(products) = products_of(repo) else {
        return None;
    };
    match product_tags(repo, &products) {
        Ok(tags) if tags.is_empty() && cuts.is_empty() => Some(NOT_APPLICABLE.to_owned()),
        Ok(_) | Err(_) => None,
    }
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// Evaluate `REL001` for `repo` against the recorded `cuts` (every `cut` event of the ledger).
///
/// A repository with no product tags and no cuts is not applicable (`not_applicable` set, no
/// findings, zero subjects). A tag git cannot resolve is Unresolved with the reason.
pub fn evaluate(repo: &Repo, cuts: &[CutData]) -> Evaluation {
    let mut out = Evaluation::default();
    let products = match products_of(repo) {
        Ok(p) => p,
        Err(e) => {
            tracing::warn!(%e, "REL001: release configuration unusable");
            out.subjects = 1;
            out.findings.push(finding(
                Severity::Unresolved,
                "config",
                "config-unresolved",
                format!("REL001: the [release] configuration cannot be resolved: {e}"),
            ));
            return out;
        }
    };
    let tags = match product_tags(repo, &products) {
        Ok(t) => t,
        Err(e) => {
            tracing::warn!(%e, "REL001: tags unreadable");
            out.subjects = 1;
            out.findings.push(finding(
                Severity::Unresolved,
                "tags",
                "unreadable",
                format!("REL001: the repository's tags cannot be listed: {e}"),
            ));
            return out;
        }
    };
    if tags.is_empty() && cuts.is_empty() {
        tracing::info!(why = NOT_APPLICABLE, "REL001 not applicable");
        out.not_applicable = Some(NOT_APPLICABLE.to_owned());
        return out;
    }
    for tag in &tags {
        out.subjects += 1;
        check_tag(repo, &products, cuts, tag, &mut out);
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "REL001 evaluated"
    );
    out
}

fn check_tag(
    repo: &Repo,
    products: &ProductTags,
    cuts: &[CutData],
    tag: &str,
    out: &mut Evaluation,
) {
    let version = products.tag_version(tag).unwrap_or_default();
    let info = match repo.find_tag(tag) {
        Ok(Some(i)) => i,
        Ok(None) => {
            tracing::debug!(tag, "REL001: tag vanished while evaluating");
            return;
        }
        Err(e) => {
            out.findings.push(finding(
                Severity::Unresolved,
                tag,
                "unresolved",
                format!("REL001: tag `{tag}` cannot be resolved: {e}"),
            ));
            return;
        }
    };
    let (object, commit) = (info.object.to_string(), info.commit.to_string());
    match recorded(cuts, tag) {
        None => {
            tracing::debug!(tag, "REL001: no recorded cut");
            out.findings.push(finding(
                Severity::Error,
                tag,
                "no-cut",
                format!(
                    "REL001: tag `{tag}` ({commit}) has no recorded release cut; record it with `frob release adopt {version}` (keeps the tag as it is), or delete the tag and run `frob release cut {version}`, which creates the tags and records the cut"
                ),
            ));
        }
        Some(r) if r.object != object || r.commit != commit => {
            tracing::debug!(tag, recorded = %r.commit, now = %commit, "REL001: tag moved");
            out.findings.push(finding(
                Severity::Error,
                tag,
                "moved",
                format!(
                    "REL001: tag `{tag}` was moved: the cut recorded commit {} (tag object {}) but it now points at commit {commit} (tag object {object}); restore it to the recorded commit",
                    r.commit, r.object
                ),
            ));
        }
        Some(_) => tracing::debug!(tag, "REL001: tag matches its cut"),
    }
    match version_at(repo, &commit) {
        Ok(v) if v == version => {}
        Ok(v) => out.findings.push(finding(
            Severity::Error,
            tag,
            "version",
            format!(
                "REL001: tag `{tag}` is version {version} but the workspace version committed at {commit} is {v}; delete the tag and run `frob release cut {version}` so the tag lands on the release commit"
            ),
        )),
        Err(why) => out.findings.push(finding(
            Severity::Unresolved,
            tag,
            "version-unresolved",
            format!("REL001: the workspace version at {commit} (tag `{tag}`) cannot be read: {why}"),
        )),
    }
}

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
/// The git repository holding `root`, the input of `REL001`; `None` outside a git work tree.
#[must_use]
pub fn repo_of(root: &std::path::Path) -> Option<Repo> {
    match Repo::discover(root) {
        Ok(r) if r.work_dir().is_some() => Some(r),
        Ok(_) | Err(_) => {
            tracing::info!("REL001: no git work tree");
            None
        }
    }
}

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
/// Every `cut` event on every milestone at the ledger tip; an unreadable ledger is an error, never "no cuts".
///
/// # Errors
///
/// The ledger or milestone read failure rendered as text.
pub fn recorded_cuts(ledger: &frob_ledger::Ledger) -> Result<Vec<CutData>, String> {
    use frob_pm::event::PmBody;
    use frob_pm::{ObjectKind, PmStore};
    let Some(tip) = ledger.tip_hex().map_err(|e| e.to_string())? else {
        return Ok(Vec::new());
    };
    let store = PmStore::new(ledger);
    let mut cuts = Vec::new();
    for m in frob_pm::eval::membership::milestones(ledger).map_err(|e| e.to_string())? {
        for e in store
            .read_events_at(&tip, ObjectKind::Milestone, m.id)
            .map_err(|e| e.to_string())?
        {
            if let PmBody::Cut(d) = e.body {
                cuts.push(d);
            }
        }
    }
    Ok(cuts)
}
