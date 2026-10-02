//! frob's per-file checks: the obligation rules and the link-target side input of `DOC002`.

use std::path::{Component, Path, PathBuf};
use std::sync::Arc;

use frob_obligations::{Todo001, evaluate_file};
use gob_check::{CheckCtx, FileCheck, SharedCtx};
use gob_rules::{Finding, Rule, RuleMeta};
use gob_text::FileId;

use crate::product::Frob;

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
pub(crate) fn link_target_digest(ctx: &SharedCtx<'_, Frob>, path: &str, text: &str) -> String {
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
                if let Some(d) = ctx.digest_of(&rel) {
                    format!("file:{d}")
                } else if ctx.has_dir(&rel) {
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

impl FileCheck<Frob> for ObligationFileCheck {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![
            Todo001.meta(),
            frob_obligations::Doc001.meta(),
            frob_obligations::Doc002.meta(),
            frob_obligations::Ref001.meta(),
        ]
    }

    fn applies(&self, ctx: &SharedCtx<'_, Frob>, path: &str) -> bool {
        ctx.product.obligation_paths.contains(path)
    }

    fn examines(&self, ctx: &SharedCtx<'_, Frob>, rule: &RuleMeta, _path: &str) -> bool {
        // REF001 resolves ticket references against the ledger; without one it examines nothing.
        rule.id != "REF001" || ctx.product.has_ledger
    }

    fn side_input(
        &self,
        ctx: &SharedCtx<'_, Frob>,
        rule: &RuleMeta,
        path: &str,
        text: &str,
    ) -> String {
        match rule.id {
            "REF001" => ctx.product.ledger_tip.clone(),
            "DOC002" if is_markdown(path) => link_target_digest(ctx, path, text),
            _ => String::new(),
        }
    }

    fn side_input_needs_text(&self, rule: &RuleMeta) -> bool {
        rule.id == "DOC002"
    }

    fn check(
        &self,
        ctx: &CheckCtx<'_, Frob>,
        file: FileId,
        path: &str,
        text: &str,
    ) -> Vec<Finding> {
        evaluate_file(&ctx.inputs.obligations(), file, path, text)
    }
}

/// The checks every run carries before the caller's extras.
pub(crate) fn builtin_checks() -> Vec<Arc<dyn FileCheck<Frob>>> {
    vec![Arc::new(ObligationFileCheck)]
}
