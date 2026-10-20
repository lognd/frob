//! The GitHub Actions adapter (fidelity F2): workflow jobs plus `uses:` and `needs:` edges.
//!
//! # Mapping (rho)
//!
//! - Structure comes from the YAML fold: `jobs.build` is a `unit(key, impl)`.
//! - `uses:` (a step action or a reusable workflow) is an instantiate reference
//!   from the enclosing job: Must when pinned to a commit SHA or digest, May for a
//!   tag or branch, Unknown when unpinned (`cicd.md` section 4). Local `./` actions
//!   are not external and are skipped.
//! - `needs:` (scalar, flow list or block list) is a dependency reference from the
//!   job to each named sibling job.
//! - Steps, `${{ }}` expression regions and `run:` shell regions are not yet
//!   modelled, so the adapter claims F2, not F3.

// frob:ticket 01M3Z71542Y6NZG3G8A83EFRF2

use std::sync::Arc;

use gob_languages::{Language, ParseLimits, UnresolvedReason, grammar_identity};

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::model::{FileSymbols, RefKind, RefSite};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::yaml::fold_text;

/// True for a path under `.github/workflows/` with a YAML extension.
#[must_use]
pub fn is_workflow_path(path: &str) -> bool {
    let p = path.replace('\\', "/");
    let Some((dir, file)) = p.rsplit_once('/') else {
        return false;
    };
    let yaml = std::path::Path::new(file)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("yml") || e.eq_ignore_ascii_case("yaml"));
    (dir == ".github/workflows" || dir.ends_with("/.github/workflows")) && yaml
}

/// The GitHub Actions workflow adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct ActionsAdapter;

impl Adapter for ActionsAdapter {
    fn language(&self) -> &'static str {
        "github-actions"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/actions/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Yaml)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F2
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::GithubActions)
    }

    fn parse(&self, text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Source(Arc::from(text))
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        let ConcreteTree::Source(text) = tree else {
            return crate::fold::failed_file(input, "yaml", UnresolvedReason::GrammarUnavailable);
        };
        let mut folded = fold_text(text, input)?;
        folded.file.fidelity = Fidelity::F2;
        let before = folded.file.refs.len();
        scan_refs(text, &mut folded.file);
        tracing::debug!(
            path = input.path,
            refs = folded.file.refs.len() - before,
            "workflow references extracted"
        );
        Ok(folded)
    }
}

/// The job (`jobs.<name>`) of `file` containing byte `offset`, else the file itself.
fn owner_of(file: &FileSymbols, offset: usize) -> Symref {
    let at = u32::try_from(offset).unwrap_or(u32::MAX).into();
    file.symbols
        .iter()
        .find(|s| {
            let segs = s.symref.segments();
            segs.len() == 2 && segs[0] == "jobs" && s.span.contains(at)
        })
        .map_or_else(|| Symref::file(&file.path), |s| s.symref.clone())
}

/// `value` without a trailing comment and surrounding quotes.
fn scalar(value: &str) -> &str {
    let v = value.split(" #").next().unwrap_or(value).trim();
    v.trim_matches(|c| c == '"' || c == '\'')
}

/// The sibling job symref named `job` next to `from` (a job symbol).
fn sibling(from: &Symref, job: &str) -> Symref {
    let mut segs = from.segments().to_vec();
    if let Some(last) = segs.last_mut() {
        job.clone_into(last);
    }
    Symref::symbol(from.path(), segs)
}

/// Pushes the `uses:` and `needs:` references of `text` onto `file.refs`.
fn scan_refs(text: &str, file: &mut FileSymbols) {
    let mut offset = 0;
    let mut scalar_indent: Option<usize> = None;
    let mut needs_block: Option<(usize, usize)> = None;
    for raw in text.split_inclusive('\n') {
        let start = offset;
        offset += raw.len();
        let line = raw.trim_end_matches(['\n', '\r']);
        let content = line.trim_start();
        let indent = line.len() - content.len();
        if content.is_empty() {
            continue;
        }
        if let Some(s) = scalar_indent {
            if indent > s {
                continue;
            }
            scalar_indent = None;
        }
        if content.starts_with('#') {
            continue;
        }
        if let Some((job_at, n)) = needs_block {
            if let Some(item) = content.strip_prefix("- ").filter(|_| indent >= n) {
                push_needs(file, job_at, scalar(item));
                continue;
            }
            needs_block = None;
        }
        let mut body = content;
        while let Some(rest) = body.strip_prefix("- ") {
            body = rest.trim_start();
        }
        let at = start + indent;
        if let Some(v) = body.strip_prefix("uses:") {
            let reference = scalar(v);
            if !reference.is_empty() && !reference.starts_with('.') {
                let reference = reference.strip_prefix("docker://").unwrap_or(reference);
                file.refs.push(RefSite {
                    from: owner_of(file, at),
                    name: reference.to_owned(),
                    qualifier: None,
                    kind: RefKind::Instantiate,
                });
            }
        } else if let Some(v) = body.strip_prefix("needs:") {
            let v = v.split(" #").next().unwrap_or(v).trim();
            if v.is_empty() {
                needs_block = Some((at, indent));
            } else if let Some(list) = v.strip_prefix('[') {
                for item in list.trim_end_matches(']').split(',') {
                    push_needs(file, at, scalar(item));
                }
            } else {
                push_needs(file, at, scalar(v));
            }
        } else if body
            .split_once(':')
            .is_some_and(|(_, v)| v.trim_start().starts_with(['|', '>']))
        {
            scalar_indent = Some(indent);
        }
    }
}

/// Pushes a `Depends` reference from the job holding byte `at` to sibling job `name`.
fn push_needs(file: &mut FileSymbols, at: usize, name: &str) {
    if name.is_empty() {
        return;
    }
    let from = owner_of(file, at);
    if from.segments().is_empty() {
        return;
    }
    let to = sibling(&from, name);
    file.refs.push(RefSite {
        from,
        name: to.to_string(),
        qualifier: None,
        kind: RefKind::Depends,
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests is_workflow_path
    #[test]
    fn recognises_workflow_paths() {
        assert!(is_workflow_path(".github/workflows/ci.yml"));
        assert!(is_workflow_path("sub/.github/workflows/ci.yaml"));
        assert!(!is_workflow_path(".github/dependabot.yml"));
        assert!(!is_workflow_path("workflows/ci.yml"));
    }
}
