//! `REL001`: a product release tag that `frob release cut` did not make.
//!
//! Releases are cut by `frob release cut VERSION`, which tags every shipped binary and records
//! a `cut` event on the milestone (`releases.md` sections 4 and 6a). [`evaluate`] lists the
//! repository's product tags (`frob-v*`, `grimble-v*`, `crunk-v*`), and checks each against
//! the recorded cuts: the tag must be named in a cut with the same tag object and commit, and
//! the workspace version committed at that commit (read through `gob-git`, never the working
//! tree) must equal the tag's version.

use frob_pm::event::{CutData, TagRecord};
use gob_git::Repo;
use gob_rules::{Finding, Rule, RuleId, Severity};
use toml::Table;

/// Tag name prefixes of the shipped products; a tag matches when the rest is a semver version.
pub const PRODUCT_TAG_PREFIXES: [&str; 3] = ["frob-v", "grimble-v", "crunk-v"];

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// A product release tag that `frob release cut` did not create, or that no longer matches its cut.
///
/// The v1 meaning of this rule (refuse a release while any debt is open) was retired: v2
/// replaced it with `defer` exceptions and the EXC rules (`exceptions.md` section 6), and the
/// id now guards the integrity of release tags instead.
///
/// A product tag is `frob-v*`, `grimble-v*` or `crunk-v*` whose remainder is a version. The
/// rule fires for each such tag when no recorded `cut` event names the tag with the same tag
/// object and commit (a tag made by plain `git tag`), when the tag now points at a different
/// commit than the one the cut recorded (a moved tag), or when the workspace version in the
/// `Cargo.toml` committed at the tagged commit differs from the tag's version. Tags before the
/// first cut are not special-cased. Tags that match no product prefix are ignored, for example
/// the v1 release tag `v0.531.0`. A repository with no product tags and no recorded cuts is
/// not applicable.
///
/// ## Remedy
///
/// For a stray tag, delete it and run `frob release cut VERSION`, which bumps, commits, tags
/// and records the release in one step. For a moved tag, restore it to the commit the cut
/// recorded (the finding names it). For a version mismatch, the tag is on the wrong commit:
/// delete it and cut the release again.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "REL001",
    slug = "release-without-cut",
    family = "REL",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Rel001;

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
    "no product tags (frob-v*, grimble-v*, crunk-v*) and no recorded release cuts";

fn rule_id() -> RuleId {
    Rel001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The version of a product tag name, or `None` when the name matches no product prefix.
#[must_use]
pub fn product_tag_version(name: &str) -> Option<&str> {
    PRODUCT_TAG_PREFIXES
        .iter()
        .find_map(|p| name.strip_prefix(p))
        .filter(|v| semver::Version::parse(v).is_ok())
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
fn product_tags(repo: &Repo) -> Result<Vec<String>, String> {
    Ok(repo
        .list_tags()
        .map_err(|e| e.to_string())?
        .into_iter()
        .filter(|n| product_tag_version(n).is_some())
        .collect())
}

/// Why `REL001` does not apply to `repo` given `cuts`, or `None` when it does.
#[must_use]
pub fn not_applicable(repo: &Repo, cuts: &[CutData]) -> Option<String> {
    match product_tags(repo) {
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
    let tags = match product_tags(repo) {
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
        check_tag(repo, cuts, tag, &mut out);
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "REL001 evaluated"
    );
    out
}

fn check_tag(repo: &Repo, cuts: &[CutData], tag: &str, out: &mut Evaluation) {
    let version = product_tag_version(tag).unwrap_or_default();
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
                    "REL001: tag `{tag}` ({commit}) has no recorded release cut; delete the tag and run `frob release cut {version}`, which creates the tags and records the cut"
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
