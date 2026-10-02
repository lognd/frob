//! Per-file checks and their cached evaluation.
//!
//! A [`FileCheck`] evaluates one file and may emit findings of several
//! rules. Results are cached per (file digest, rule id, rule version,
//! side-input digest) in the `findings` table: the lookups run in parallel,
//! the misses are computed one after another (the ledger handle is not
//! `Sync`) and stored, empty results included.

use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};

use frob_obligations::{ObligationInputs, Todo001, evaluate_file};
use gob_cache::{Cache, FindingsKey};
use gob_rules::{Finding, Rule, RuleMeta};
use gob_text::FileId;
use rayon::prelude::*;

use crate::snapshot::{FileIndex, Snapshot};
use crate::store;

/// Thread-safe facts a check may use to decide applicability and its cache key.
pub struct SharedCtx<'a> {
    /// Repository root.
    pub root: &'a Path,
    pub(crate) index: &'a FileIndex,
    pub(crate) ledger_tip: &'a str,
    pub(crate) obligation_paths: &'a std::collections::BTreeSet<String>,
}

impl SharedCtx<'_> {
    /// The ledger tip commit (hex), or the empty string without a ledger.
    pub fn ledger_tip(&self) -> &str {
        self.ledger_tip
    }

    /// Content digest (hex) of a walked file.
    pub fn digest_of(&self, path: &str) -> Option<&str> {
        self.index.digests.get(path).map(String::as_str)
    }
}

/// Everything a check may read while computing a miss.
pub struct CheckCtx<'a> {
    /// The thread-safe part.
    pub shared: &'a SharedCtx<'a>,
    /// Inputs of `frob-obligations` (graph, directives, lock, ledger).
    pub obligations: ObligationInputs<'a>,
}

/// A unit that checks one file and emits findings of the rules it declares.
pub trait FileCheck: Send + Sync {
    /// Every rule this check can emit; each gets its own cache entry per file.
    fn rules(&self) -> Vec<&'static RuleMeta>;

    /// Whether the check looks at `path` at all.
    fn applies(&self, _ctx: &SharedCtx<'_>, _path: &str) -> bool {
        true
    }

    /// Digest of what `rule` reads besides the file itself (empty when nothing).
    ///
    /// `text` is the file's content. A changed side input must change the digest.
    fn side_input(
        &self,
        _ctx: &SharedCtx<'_>,
        _rule: &RuleMeta,
        _path: &str,
        _text: &str,
    ) -> String {
        String::new()
    }

    /// Whether [`FileCheck::side_input`] reads the file text (the pipeline reads it only then).
    fn side_input_needs_text(&self, _rule: &RuleMeta) -> bool {
        false
    }

    /// Evaluate `path` (id `file`, content `text`).
    fn check(&self, ctx: &CheckCtx<'_>, file: FileId, path: &str, text: &str) -> Vec<Finding>;
}

/// The obligation rules that work on one file: `TODO001`, `DOC001`, `DOC002`, `REF001`.
pub(crate) struct ObligationFileCheck;

/// True for markdown paths.
fn is_markdown(path: &str) -> bool {
    matches!(
        Path::new(path).extension().and_then(|e| e.to_str()),
        Some("md" | "markdown")
    )
}

/// `base_dir` joined with `rel`, normalized; `None` when it escapes the root.
fn normalize(base_dir: &Path, rel: &str) -> Option<PathBuf> {
    let joined = match rel.strip_prefix('/') {
        Some(root_rel) => PathBuf::from(root_rel),
        None => base_dir.join(rel),
    };
    let mut out = PathBuf::new();
    for comp in joined.components() {
        match comp {
            Component::Normal(p) => out.push(p),
            Component::ParentDir if !out.pop() => return None,
            _ => {}
        }
    }
    Some(out)
}

/// Destinations of inline links (`](dest)`) written in `text`, over-approximated.
fn link_destinations(text: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(p) = rest.find("](") {
        rest = &rest[p + 2..];
        let body = rest.strip_prefix('<').unwrap_or(rest);
        let end = body
            .find(|c: char| c == ')' || c == '>' || c.is_whitespace())
            .unwrap_or(body.len());
        if end > 0 {
            out.push(&body[..end]);
        }
    }
    out
}

/// Digest of the state of every file a markdown file links to (`DOC002`'s side input).
///
/// A target contributes its content digest when walked, `dir` when it is a
/// directory of walked files, `disk` or `absent` otherwise (an excluded file
/// can still satisfy a link), `escape` when it leaves the repository.
pub(crate) fn link_target_digest(ctx: &SharedCtx<'_>, path: &str, text: &str) -> String {
    let base_dir = Path::new(path).parent().unwrap_or_else(|| Path::new(""));
    let mut parts: Vec<String> = Vec::new();
    for dest in link_destinations(text) {
        let no_query = dest.split('?').next().unwrap_or(dest);
        let target = no_query.split('#').next().unwrap_or(no_query);
        if target.is_empty() || target.contains("://") || target.starts_with("mailto:") {
            continue;
        }
        let state = match normalize(base_dir, target) {
            None => "escape".to_owned(),
            Some(p) => {
                let rel = p.to_string_lossy().replace('\\', "/");
                if let Some(d) = ctx.index.digests.get(&rel) {
                    format!("file:{d}")
                } else if ctx.index.dirs.contains(&rel) {
                    "dir".to_owned()
                } else if ctx.root.join(&p).exists() {
                    "disk".to_owned()
                } else {
                    "absent".to_owned()
                }
            }
        };
        parts.push(format!("{target}={state}"));
    }
    parts.sort();
    parts.dedup();
    blake3::hash(parts.join("\n").as_bytes())
        .to_hex()
        .to_string()
}

impl FileCheck for ObligationFileCheck {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![
            Todo001.meta(),
            frob_obligations::Doc001.meta(),
            frob_obligations::Doc002.meta(),
            frob_obligations::Ref001.meta(),
        ]
    }

    fn applies(&self, ctx: &SharedCtx<'_>, path: &str) -> bool {
        ctx.obligation_paths.contains(path)
    }

    fn side_input(&self, ctx: &SharedCtx<'_>, rule: &RuleMeta, path: &str, text: &str) -> String {
        match rule.id {
            "REF001" => ctx.ledger_tip.to_owned(),
            "DOC002" if is_markdown(path) => link_target_digest(ctx, path, text),
            _ => String::new(),
        }
    }

    fn side_input_needs_text(&self, rule: &RuleMeta) -> bool {
        rule.id == "DOC002"
    }

    fn check(&self, ctx: &CheckCtx<'_>, file: FileId, path: &str, text: &str) -> Vec<Finding> {
        evaluate_file(&ctx.obligations, file, path, text)
    }
}

/// The checks every run carries before the caller's extras.
pub(crate) fn builtin_checks() -> Vec<std::sync::Arc<dyn FileCheck>> {
    vec![std::sync::Arc::new(ObligationFileCheck)]
}

/// The stored side-input digest: the check's own, with the file path folded in.
///
/// Findings name their file (spans, messages quoting symrefs), so two files
/// with identical content must not share an entry.
fn key_side_input(path: &str, side: &str) -> String {
    let mut h = blake3::Hasher::new();
    h.update(path.as_bytes());
    h.update(b"\0");
    h.update(side.as_bytes());
    h.finalize().to_hex().to_string()
}

/// Outcome of the per-file stage.
pub(crate) struct FileStage {
    /// Raw findings (exceptions not applied).
    pub findings: Vec<Finding>,
    /// Cache hits (one per check and file).
    pub hits: usize,
    /// Computed results.
    pub misses: usize,
}

/// What the parallel lookup found for one (file, check) pair.
struct Lookup {
    check: usize,
    path: String,
    digest: String,
    keys: Vec<FindingsKey>,
    hit: Option<Vec<Finding>>,
}

/// Rule id of `finding` as an owned string.
fn rule_of(f: &Finding) -> String {
    f.rule.to_string()
}

/// Run `checks` over `paths` with the findings cache.
pub(crate) fn run_file_checks(
    snap: &Snapshot,
    cache: &Cache,
    checks: &[std::sync::Arc<dyn FileCheck>],
    paths: &[String],
) -> FileStage {
    let shared = SharedCtx {
        root: &snap.root,
        index: &snap.index,
        ledger_tip: snap.ledger_tip(),
        obligation_paths: &snap.obligation_paths,
    };
    let metas: Vec<Vec<&'static RuleMeta>> = checks.iter().map(|c| c.rules()).collect();
    let (root, index) = (&snap.root, &snap.index);
    let lookups: Vec<Lookup> = paths
        .par_iter()
        .flat_map_iter(|path| {
            let mut out = Vec::new();
            let Some(digest) = index.digests.get(path) else {
                return out;
            };
            for (ci, check) in checks.iter().enumerate() {
                if !check.applies(&shared, path) {
                    continue;
                }
                let needs_text = metas[ci].iter().any(|m| check.side_input_needs_text(m));
                let text = if needs_text {
                    std::fs::read_to_string(root.join(path)).unwrap_or_default()
                } else {
                    String::new()
                };
                let keys: Vec<FindingsKey> = metas[ci]
                    .iter()
                    .map(|m| FindingsKey {
                        file_digest: digest.clone(),
                        rule_id: m.id.to_owned(),
                        rule_version: m.version,
                        side_input_digest: key_side_input(
                            path,
                            &check.side_input(&shared, m, path, &text),
                        ),
                    })
                    .collect();
                let hit = decode_all(cache, &keys, &index.ids);
                out.push(Lookup {
                    check: ci,
                    path: path.clone(),
                    digest: digest.clone(),
                    keys,
                    hit,
                });
            }
            out
        })
        .collect();

    let ctx = CheckCtx {
        shared: &shared,
        obligations: snap.obligations(),
    };
    let mut stage = FileStage {
        findings: Vec::new(),
        hits: 0,
        misses: 0,
    };
    for lookup in lookups {
        if let Some(found) = lookup.hit {
            stage.hits += 1;
            stage.findings.extend(found);
            continue;
        }
        stage.misses += 1;
        let Ok(text) = std::fs::read_to_string(snap.root.join(&lookup.path)) else {
            tracing::warn!(path = %lookup.path, "unreadable file skipped by per-file rules");
            continue;
        };
        let file = snap.index.ids[&lookup.path];
        let found = checks[lookup.check].check(&ctx, file, &lookup.path, &text);
        tracing::debug!(path = %lookup.path, findings = found.len(), digest = %lookup.digest, "per-file check computed");
        let mut by_rule: HashMap<String, Vec<Finding>> = HashMap::new();
        for f in &found {
            by_rule.entry(rule_of(f)).or_default().push(f.clone());
        }
        for key in &lookup.keys {
            let mine = by_rule.remove(&key.rule_id).unwrap_or_default();
            cache.put_findings(key, &store::encode(&mine, &snap.ack.files));
        }
        for (rule, strays) in by_rule {
            tracing::warn!(
                rule,
                count = strays.len(),
                "finding of an undeclared rule is not cached"
            );
        }
        stage.findings.extend(found);
    }
    stage
}

/// All keys hit and decode: the concatenated findings; otherwise `None`.
fn decode_all(
    cache: &Cache,
    keys: &[FindingsKey],
    ids: &HashMap<String, FileId>,
) -> Option<Vec<Finding>> {
    let mut out = Vec::new();
    for key in keys {
        let bytes = cache.get_findings(key)?;
        out.extend(store::decode(&bytes, |p| ids.get(p).copied())?);
    }
    Some(out)
}
