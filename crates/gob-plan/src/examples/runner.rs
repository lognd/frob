//! Running one example: lower the rule, build the example's model, execute, judge.

// frob:ticket 01M4M99GMQDG93W4X05A4HFP5X
// frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
use super::judge::{judge, ExampleResult};
use super::markers::{expect_line, parse_markers, Actual, Expected, Level, Mark};
use super::side::{side_data, SideInputs};
use crate::catalog::lang_of;
use crate::exec::outcome::{outcomes, Kind};
use crate::exec::relations::Relations;
use crate::exec::{ExecError, Input};
use crate::grl::ast::{
    Example, ExampleBody, ExpectKind, HeaderKind, InputKind, LangSet, Rule, Severity,
};
use crate::lower::{lower_rule, LowerError};
use crate::plan::{Langs, Op, Plan, Provenance};

/// The line reported for a finding whose subject is not a node of the example source.
const NO_LINE: u32 = 0;

/// The language an empty model is built in when an example names none.
const EMPTY_MODEL_LANG: &str = "markdown";

/// Why an example could not be run at all (as opposed to failing with GRL016).
#[derive(Debug, thiserror::Error)]
pub enum RunError {
    /// The rule does not lower to a plan.
    #[error(transparent)]
    Lower(#[from] LowerError),
    /// The executor refused the plan.
    #[error(transparent)]
    Exec(#[from] ExecError),
    /// The example's source could not be folded into a model.
    #[error("cannot build the example model: {0}")]
    Model(String),
    /// The example uses an input this runner does not execute yet.
    #[error("example input `{0}` is not supported by the runner yet")]
    Unsupported(&'static str),
    /// The example names no language and the rule is not language-less (`lang -`).
    #[error("the example has no language and the rule does not name exactly one")]
    NoLanguage,
    /// The example text is too large to index.
    #[error("example text is too large")]
    TooLarge,
}

/// The language of an example: its own `lang`, else the rule's single `lang` header; `None` for
/// a language-less rule (`lang -`) whose example names none.
fn language(rule: &Rule, example: &Example, plan: &Plan) -> Result<Option<String>, RunError> {
    if let Some(w) = &example.lang {
        return Ok(Some(w.text.clone()));
    }
    let single = rule.headers.iter().find_map(|h| match &h.node {
        HeaderKind::Lang(LangSet::One(w)) => Some(w.text.clone()),
        _ => None,
    });
    match single {
        Some(l) => Ok(Some(l)),
        None if matches!(plan.parts().langs, Langs::Nothing) => Ok(None),
        None => Err(RunError::NoLanguage),
    }
}

/// The edge relations the plan names, built from the example model.
fn edges(plan: &Plan, model: &gob_ir::Model) -> Relations {
    let p = plan.parts();
    let mut rel = Relations::new();
    let ctx = gob_ir::eval::Ctx::new(model);
    let mut named: Vec<&str> = p
        .ops
        .iter()
        .filter_map(|op| match op {
            Op::Verb { verb, .. } => Some(*verb),
            Op::Reaches { via, .. } => Some(*via),
            _ => None,
        })
        .map(|id| p.strings[id as usize].as_str())
        .collect();
    named.sort_unstable();
    named.dedup();
    for name in named {
        match name {
            "calls" => rel = rel.with_edges(name, ctx.rel_calls()),
            "resolves to" => rel = rel.with_edges(name, ctx.rel_resolves()),
            // `frob:tests` links join files; one example source has none.
            "tests" => rel = rel.with_edges(name, gob_ir::eval::Relation::new()),
            other => tracing::debug!(edge = other, "no example edge relation for this word"),
        }
    }
    rel
}

fn severity(rule: &Rule) -> Level {
    rule.headers
        .iter()
        .find_map(|h| match h.node {
            HeaderKind::Severity(Severity::Error) => Some(Level::Error),
            HeaderKind::Severity(Severity::Advisory) => Some(Level::Advisory),
            _ => None,
        })
        .unwrap_or(Level::Warn)
}

/// The example's source text and the expectations written in sub-blocks.
fn inputs(
    example: &Example,
) -> Result<(Option<String>, Option<String>, Vec<Expected>, SideInputs), RunError> {
    match &example.body {
        ExampleBody::Source(b) => Ok((
            Some(b.value.clone()),
            None,
            Vec::new(),
            SideInputs::default(),
        )),
        ExampleBody::Inputs(items) => {
            let (mut text, mut path, mut expected) = (None, None, Vec::new());
            let mut side = SideInputs::default();
            for i in items {
                match &i.node {
                    InputKind::File { path: p, text: t } if text.is_none() => {
                        text = Some(t.value.clone());
                        path = Some(p.value.clone());
                    }
                    InputKind::File { .. } => return Err(RunError::Unsupported("second file")),
                    InputKind::Expect(s) => expected.extend(expect_line(&s.value)),
                    InputKind::Config(b) => side.config = Some(b.value.clone()),
                    InputKind::Model(_) => return Err(RunError::Unsupported("model")),
                    InputKind::Diff(v) => {
                        side.diff = Some(v.iter().map(|p| p.value.clone()).collect());
                    }
                    InputKind::Lease(v) => {
                        side.lease = Some(v.iter().map(|p| p.value.clone()).collect());
                    }
                    InputKind::Fixed(_) => return Err(RunError::Unsupported("fixed")),
                }
            }
            if text.is_none() && side == SideInputs::default() {
                return Err(RunError::Unsupported("no file"));
            }
            Ok((text, path, expected, side))
        }
    }
}

/// Run one example of `rule` and judge it: pass, or GRL016 with the expected-versus-actual diff.
///
/// # Errors
/// [`RunError`] when the rule does not lower, the executor refuses the plan, or the example uses
/// an input the runner does not execute yet. A wrong outcome is not an error; it is a failed
/// [`ExampleResult`].
pub fn run_example(rule: &Rule, example: &Example) -> Result<ExampleResult, RunError> {
    let plan = lower_rule(rule, Provenance::Std)?;
    let lang = language(rule, example, &plan)?;
    let (file_text, file_path, mut expected, side) = inputs(example)?;
    let has_file = file_text.is_some();
    let text = file_text.unwrap_or_default();
    if let Some(l) = &lang {
        expected.extend(parse_markers(l, &text));
    }
    let not_applicable = match (&plan.parts().langs, &lang) {
        // A language the capability matrix does not model has no adapter: its source folds to one
        // opaque node, so a universal rule has nothing to say about it.
        (Langs::Any, Some(l)) => lang_of(l).is_none(),
        (Langs::Any | Langs::Nothing, None) => false,
        (Langs::Nothing, Some(_)) => true,
        (Langs::Only(ids), Some(l)) => !ids.iter().any(|&i| plan.parts().strings[i as usize] == *l),
        (Langs::Only(_), None) => return Err(RunError::NoLanguage),
    };
    let mut actual: Vec<Actual> = Vec::new();
    if !not_applicable {
        let model_lang = lang.as_deref().unwrap_or(EMPTY_MODEL_LANG);
        let model_text = if lang.is_some() { text.as_str() } else { "" };
        let model = match (file_path.as_deref(), lang.is_some()) {
            (Some(p), true) => gob_symbols::model_of_source_at(p, model_text),
            _ => gob_symbols::model_of_source(model_lang, model_text),
        }
        .map_err(|e| RunError::Model(e.to_string()))?;
        let source = gob_text::SourceText::new(text).map_err(|_| RunError::TooLarge)?;
        let input = Input {
            model: &model,
            source: Some(&source),
        };
        let relations = edges(&plan, &model).with_side(side_data(&plan, &side)?);
        let out = outcomes(&plan, &input, &relations)?;
        let level = severity(rule);
        for f in &out.findings {
            let line = match f.subject {
                Some(n) => {
                    let Some(span) = model.term().node(n).location().span() else {
                        continue;
                    };
                    let Some(lc) = source.line_col(span.range.start()) else {
                        continue;
                    };
                    lc.line
                }
                // A side-table row (a changed path, a config row) has no source line.
                None => NO_LINE,
            };
            let mark = match f.kind {
                Kind::Fire => Mark::Finding(level),
                Kind::Unresolved => Mark::Unresolved,
            };
            actual.push(Actual { line, mark });
        }
        // An example with only side inputs has no file to carry markers: a `fire` one expects
        // the findings it got, so it passes iff the rule fires at all.
        if !has_file && example.expect.kind == ExpectKind::Fire {
            expected.extend(actual.iter().copied());
        }
    }
    tracing::debug!(rule = %rule.id.text, found = actual.len(), "ran example");
    Ok(judge(
        example.expect.kind,
        &expected,
        &actual,
        not_applicable,
    ))
}
