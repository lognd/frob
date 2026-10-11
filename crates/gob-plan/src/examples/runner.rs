//! Running one example: lower the rule, build the example's model, execute, judge.

// frob:ticket 01M4M99GMQDG93W4X05A4HFP5X
use super::judge::{ExampleResult, judge};
use super::markers::{Actual, Expected, Level, Mark, expect_line, parse_markers};
use crate::exec::outcome::{Kind, outcomes};
use crate::exec::relations::Relations;
use crate::exec::{ExecError, Input};
use crate::grl::ast::{Example, ExampleBody, HeaderKind, InputKind, LangSet, Rule, Severity};
use crate::lower::{LowerError, lower_rule};
use crate::plan::{Langs, Provenance};

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
    /// The example names no language and the rule does not name exactly one.
    #[error("the example has no language and the rule does not name exactly one")]
    NoLanguage,
    /// The example text is too large to index.
    #[error("example text is too large")]
    TooLarge,
}

/// The language of an example: its own `lang`, else the rule's single `lang` header.
fn language(rule: &Rule, example: &Example) -> Result<String, RunError> {
    if let Some(w) = &example.lang {
        return Ok(w.text.clone());
    }
    rule.headers
        .iter()
        .find_map(|h| match &h.node {
            HeaderKind::Lang(LangSet::One(w)) => Some(w.text.clone()),
            _ => None,
        })
        .ok_or(RunError::NoLanguage)
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
fn inputs(example: &Example) -> Result<(String, Vec<Expected>), RunError> {
    match &example.body {
        ExampleBody::Source(b) => Ok((b.value.clone(), Vec::new())),
        ExampleBody::Inputs(items) => {
            let (mut text, mut expected) = (None, Vec::new());
            for i in items {
                match &i.node {
                    InputKind::File { text: t, .. } if text.is_none() => {
                        text = Some(t.value.clone());
                    }
                    InputKind::File { .. } => return Err(RunError::Unsupported("second file")),
                    InputKind::Expect(s) => expected.extend(expect_line(&s.value)),
                    InputKind::Config(_) => return Err(RunError::Unsupported("config")),
                    InputKind::Model(_) => return Err(RunError::Unsupported("model")),
                    InputKind::Diff(_) => return Err(RunError::Unsupported("diff")),
                    InputKind::Lease(_) => return Err(RunError::Unsupported("lease")),
                    InputKind::Fixed(_) => return Err(RunError::Unsupported("fixed")),
                }
            }
            Ok((text.ok_or(RunError::Unsupported("no file"))?, expected))
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
    let lang = language(rule, example)?;
    let (text, mut expected) = inputs(example)?;
    expected.extend(parse_markers(&lang, &text));
    let not_applicable = match &plan.parts().langs {
        Langs::Any => false,
        Langs::Nothing => true,
        Langs::Only(ids) => !ids
            .iter()
            .any(|&i| plan.parts().strings[i as usize] == lang),
    };
    let mut actual: Vec<Actual> = Vec::new();
    if !not_applicable {
        let model = gob_symbols::model_of_source(&lang, &text)
            .map_err(|e| RunError::Model(e.to_string()))?;
        let source = gob_text::SourceText::new(text).map_err(|_| RunError::TooLarge)?;
        let input = Input {
            model: &model,
            source: Some(&source),
        };
        let out = outcomes(&plan, &input, &Relations::new())?;
        let level = severity(rule);
        for f in &out.findings {
            let Some(span) = f
                .subject
                .and_then(|n| model.term().node(n).location().span())
            else {
                continue;
            };
            let Some(lc) = source.line_col(span.range.start()) else {
                continue;
            };
            let mark = match f.kind {
                Kind::Fire => Mark::Finding(level),
                Kind::Unresolved => Mark::Unresolved,
            };
            actual.push(Actual {
                line: lc.line,
                mark,
            });
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
