//! The Dockerfile adapter (fidelity F2): build stages, `FROM` and `COPY --from` edges.
//!
//! # Mapping (rho)
//!
//! - The document is `unit(file, impl)`; each `FROM` opens a `unit(stage, impl)`
//!   named by its `AS` name (dots become `_`) or `stage-N` (zero based). The symref
//!   is `path::stage`. A stage spans its `FROM` to its last instruction; its Sig
//!   facet is the base image text and its Body facet the exact span text.
//! - `FROM image` is an instantiate reference from the stage: Must for a digest, May
//!   for a tag, Unknown for no tag or `latest` (`cicd.md` section 4). `FROM stage`
//!   naming an earlier stage, and `COPY --from=stage|index`, are dependency
//!   references; `COPY --from=image` is an instantiate reference. `scratch` is skipped.
//! - Instruction bodies (`RUN` shell regions, `USER`, `EXPOSE`) are not modelled, so
//!   the adapter claims F2, not F3.

// frob:ticket 01M3Z71542Y6NZG3G8A83EFRF2

use std::sync::Arc;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, TermError, reserved};
use gob_languages::{Language, ParseLimits, UnresolvedReason, grammar_identity};

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
    ParseStatus,
};
use crate::fold::{Cx, base_file, file_root_spec};
use crate::model::{RefKind, RefSite};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{self, Naming};

/// True for `Dockerfile`, `Dockerfile.*` and `*.dockerfile` (any directory).
#[must_use]
pub fn is_dockerfile_path(path: &str) -> bool {
    let name = path.rsplit(['/', '\\']).next().unwrap_or(path);
    let lower = name.to_ascii_lowercase();
    lower == "dockerfile" || lower.starts_with("dockerfile.") || lower.ends_with(".dockerfile")
}

/// The Dockerfile adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct DockerfileAdapter;

impl Adapter for DockerfileAdapter {
    fn language(&self) -> &'static str {
        "dockerfile"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/dockerfile/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Yaml)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F2
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Dockerfile)
    }

    fn parse(&self, text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Source(Arc::from(text))
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Source(text) => fold_text(text, input),
            _ => {
                crate::fold::failed_file(input, "dockerfile", UnresolvedReason::GrammarUnavailable)
            }
        }
    }
}

/// One logical instruction: keyword, argument text and byte extent.
#[derive(Debug)]
struct Instruction {
    keyword: String,
    args: String,
    start: usize,
    end: usize,
}

/// One build stage found by the scan.
#[derive(Debug)]
struct Stage {
    name: String,
    alias: Option<String>,
    image: String,
    start: usize,
    end: usize,
}

/// Splits `text` into logical instructions (continuation lines joined, comments dropped).
fn instructions(text: &str) -> Vec<Instruction> {
    let mut out: Vec<Instruction> = Vec::new();
    let mut current: Option<(usize, usize, String)> = None;
    let mut offset = 0;
    for raw in text.split_inclusive('\n') {
        let start = offset;
        offset += raw.len();
        let line = raw.trim_end_matches(['\n', '\r']);
        let content = line.trim();
        if content.is_empty() || content.starts_with('#') {
            continue;
        }
        let (begin, mut buf) = match current.take() {
            Some((b, _, buf)) => (b, buf),
            None => (
                start + (line.len() - line.trim_start().len()),
                String::new(),
            ),
        };
        let cont = content.ends_with('\\');
        buf.push_str(content.trim_end_matches('\\').trim_end());
        buf.push(' ');
        let end = start + line.trim_end().len();
        if cont {
            current = Some((begin, end, buf));
        } else {
            push_instruction(&mut out, begin, end, &buf);
        }
    }
    if let Some((begin, end, buf)) = current {
        push_instruction(&mut out, begin, end, &buf);
    }
    out
}

/// Appends the instruction held in `buf` to `out`.
fn push_instruction(out: &mut Vec<Instruction>, start: usize, end: usize, buf: &str) {
    let buf = buf.trim();
    let (kw, args) = buf.split_once(char::is_whitespace).unwrap_or((buf, ""));
    out.push(Instruction {
        keyword: kw.to_ascii_uppercase(),
        args: args.trim().to_owned(),
        start,
        end,
    });
}

/// A stage name safe as a symref segment (dots and whitespace become `_`).
fn segment(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c == '.' || c.is_whitespace() {
                '_'
            } else {
                c
            }
        })
        .collect()
}

/// Parses `FROM [--flag..] image [AS name]` arguments into `(image, alias)`.
fn parse_from(args: &str) -> Option<(String, Option<String>)> {
    let mut toks = args.split_whitespace().filter(|t| !t.starts_with("--"));
    let image = toks.next()?.to_owned();
    let alias = match (toks.next(), toks.next()) {
        (Some(kw), Some(name)) if kw.eq_ignore_ascii_case("as") => Some(name.to_owned()),
        _ => None,
    };
    Some((image, alias))
}

/// The `--from=` value of a `COPY` instruction, if any.
fn copy_from(args: &str) -> Option<&str> {
    args.split_whitespace()
        .take_while(|t| t.starts_with("--"))
        .find_map(|t| t.strip_prefix("--from="))
}

/// Resolves `name` (an alias or a zero-based index) among `stages` before `limit`.
fn find_stage<'a>(stages: &'a [Stage], name: &str, limit: usize) -> Option<&'a Stage> {
    let visible = &stages[..limit.min(stages.len())];
    if let Ok(i) = name.parse::<usize>() {
        return visible.get(i);
    }
    visible.iter().find(|s| {
        s.alias
            .as_deref()
            .is_some_and(|a| a.eq_ignore_ascii_case(name))
    })
}

/// Builds the `unit(stage, impl)` node for `stage` over `text`.
fn fold_stage(cx: &mut Cx<'_>, stage: &Stage) -> Result<NodeId, TermError> {
    let loc = cx.loc(stage.start, stage.end);
    let image = cx.add(
        NodeSpec::new(Operator::lit("image", &stage.image), loc.clone()),
        &[],
    )?;
    let sig = cx.add(
        NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone())
            .attr(reserved::FACET, "sig"),
        &[image],
    )?;
    let body = cx.add(
        NodeSpec::new(
            Operator::lit("text", &cx.text[stage.start..stage.end]),
            loc.clone(),
        ),
        &[],
    )?;
    cx.add(
        NodeSpec::new(Operator::unit("stage", "impl"), loc).named(&stage.name),
        &[sig, body],
    )
}

/// Folds a Dockerfile into stage units with `FROM` and `COPY --from` references.
fn fold_text(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, "dockerfile", text);
    let insts = instructions(text);
    let mut stages: Vec<Stage> = Vec::new();
    for inst in &insts {
        if inst.keyword == "FROM" {
            let Some((image, alias)) = parse_from(&inst.args) else {
                continue;
            };
            let name = match alias.as_deref() {
                Some(n) => segment(n),
                None => format!("stage-{}", stages.len()),
            };
            stages.push(Stage {
                name,
                alias,
                image,
                start: inst.start,
                end: inst.end,
            });
        } else if let Some(s) = stages.last_mut() {
            s.end = inst.end;
        }
    }
    let mut units = Vec::new();
    for s in &stages {
        units.push(fold_stage(&mut cx, s)?);
    }
    let root = cx.add(file_root_spec(&cx, input.size as usize), &units)?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "dockerfile");
    file.fidelity = Fidelity::F2;
    file.parse_status = ParseStatus::Complete;
    file.symbols = v.symbols;
    file.extras = v.extras;
    file.refs = refs_of(input.path, &insts, &stages);
    tracing::debug!(
        path = input.path,
        stages = stages.len(),
        refs = file.refs.len(),
        "dockerfile folded"
    );
    Ok(Folded { term, scopes, file })
}

/// A reference to base `image` named in stage `i`, as a dependency or an instantiation.
fn image_ref(
    from: &Symref,
    path: &str,
    stages: &[Stage],
    i: usize,
    image: &str,
) -> Option<RefSite> {
    if image.eq_ignore_ascii_case("scratch") {
        return None;
    }
    Some(match find_stage(stages, image, i) {
        Some(dep) => RefSite {
            from: from.clone(),
            name: Symref::symbol(path, vec![dep.name.clone()]).to_string(),
            qualifier: None,
            kind: RefKind::Depends,
        },
        None => RefSite {
            from: from.clone(),
            name: image.to_owned(),
            qualifier: None,
            kind: RefKind::Instantiate,
        },
    })
}

/// The references of every stage: base images and `COPY --from` sources.
fn refs_of(path: &str, insts: &[Instruction], stages: &[Stage]) -> Vec<RefSite> {
    let mut out = Vec::new();
    let mut current: Option<(usize, Symref)> = None;
    for inst in insts {
        if inst.keyword == "FROM" {
            let Some(i) = stages.iter().position(|s| s.start == inst.start) else {
                continue;
            };
            let from = Symref::symbol(path, vec![stages[i].name.clone()]);
            out.extend(image_ref(&from, path, stages, i, &stages[i].image));
            current = Some((i, from));
        } else if inst.keyword == "COPY"
            && let (Some((i, from)), Some(src)) = (&current, copy_from(&inst.args))
        {
            out.extend(image_ref(from, path, stages, *i, src));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests is_dockerfile_path
    #[test]
    fn recognises_dockerfile_paths() {
        assert!(is_dockerfile_path("Dockerfile"));
        assert!(is_dockerfile_path("ci/Dockerfile.dev"));
        assert!(is_dockerfile_path("app.dockerfile"));
        assert!(!is_dockerfile_path("docker-compose.yml"));
    }

    // frob:tests instructions
    #[test]
    fn joins_continuations() {
        let i = instructions("FROM a AS b\nRUN x \\\n  && y\n# c\nCOPY . .\n");
        assert_eq!(i.len(), 3);
        assert_eq!(i[1].args, "x && y");
    }
}
