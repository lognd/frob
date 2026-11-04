//! Rendering a rule's fixes for one binding (grl-spec.md section 8).
//!
//! The plan carries each `fix` clause with its snippet template untouched. [`render_fixes`]
//! gathers the metavariable bindings of every `x is` snippet match that covers the binding's
//! node and renders each template with `gob_pattern::grammar::render` over them, producing byte
//! edits the caller applies (`gob_pattern::grammar::apply`) or shows.

use std::ops::Range;

use gob_ir::Location;
use gob_pattern::grammar::{Bindings, Edit, GrammarError, Pattern, render};

use super::core::{Input, Row};
use crate::plan::{Applicability, FixAction, FixPlace, Op, Plan};

/// What a rendered fix asks of the caller.
///
/// frob:ticket 01M4XJ9HCS3WP614D698VN2V5Y
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FixEdit {
    /// A byte edit in the artifact's text.
    Edit(Edit),
    /// A std host fix: its name and literal arguments, applied by the host.
    Host {
        /// The host fix name.
        name: String,
        /// The arguments as text.
        args: Vec<String>,
    },
    /// Help text only; nothing is edited.
    Manual(String),
}

/// One fix of a rule rendered for one binding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderedFix {
    /// How safe the fix is to apply; `None` for a manual fix.
    pub applicability: Option<Applicability>,
    /// What to do.
    pub edit: FixEdit,
}

/// Why a fix could not be rendered for a binding.
#[derive(Debug, thiserror::Error)]
#[non_exhaustive]
pub enum FixError {
    /// The artifact text is not available, so no edit can be located.
    #[error("the artifact text is not available to render a fix")]
    NoText,
    /// The fix target is unbound in this binding or has no text location.
    #[error("the fix target has no text location")]
    NoTarget,
    /// The template could not be rendered (an unbound metavariable) or a pattern failed.
    #[error("fix template: {0}")]
    Template(#[from] GrammarError),
}

/// Renders every fix of `plan` for the binding `row`, in text order.
///
/// # Errors
/// [`FixError::NoText`] or [`FixError::NoTarget`] when an edit cannot be placed, and
/// [`FixError::Template`] when a template names a metavariable no snippet bound.
///
/// frob:ticket 01M4XJ9HCS3WP614D698VN2V5Y
pub fn render_fixes(
    plan: &Plan,
    input: &Input<'_>,
    row: &Row,
) -> Result<Vec<RenderedFix>, FixError> {
    let p = plan.parts();
    let mut out = Vec::with_capacity(p.fixes.len());
    let mut bindings: Option<Bindings> = None;
    for f in &p.fixes {
        let edit = match &f.action {
            FixAction::Replace { place, template } => {
                let range = target_range(input, row, f.target)?;
                let b = match &mut bindings {
                    Some(b) => b,
                    slot => slot.insert(gather(plan, input, row)?),
                };
                let text = render(&p.strings[*template as usize], b)?;
                FixEdit::Edit(Edit {
                    range: place_range(*place, range),
                    text,
                })
            }
            FixAction::Delete => FixEdit::Edit(Edit {
                range: target_range(input, row, f.target)?,
                text: String::new(),
            }),
            FixAction::Host { name, args } => FixEdit::Host {
                name: p.strings[*name as usize].clone(),
                args: args
                    .iter()
                    .map(|a| p.strings[*a as usize].clone())
                    .collect(),
            },
            FixAction::Manual { message } => FixEdit::Manual(p.strings[*message as usize].clone()),
        };
        tracing::debug!(rule = %p.rule, applicability = ?f.applicability, "rendered a fix");
        out.push(RenderedFix {
            applicability: f.applicability,
            edit,
        });
    }
    Ok(out)
}

/// The edited byte range for a placement: the target itself, or an empty range beside it.
fn place_range(place: FixPlace, r: Range<usize>) -> Range<usize> {
    match place {
        FixPlace::Over => r,
        FixPlace::Before => r.start..r.start,
        FixPlace::After => r.end..r.end,
    }
}

/// The byte range of the node bound to `var` in `row`.
fn target_range(input: &Input<'_>, row: &Row, var: u16) -> Result<Range<usize>, FixError> {
    let node = row.node(var).ok_or(FixError::NoTarget)?;
    match input.model.term().node(node).location() {
        Location::Text { range, .. } => {
            Ok(u32::from(range.start()) as usize..u32::from(range.end()) as usize)
        }
        _ => Err(FixError::NoTarget),
    }
}

/// The union of the bindings of every snippet match that covers its variable's node in `row`.
fn gather(plan: &Plan, input: &Input<'_>, row: &Row) -> Result<Bindings, FixError> {
    let p = plan.parts();
    let src = input.source.ok_or(FixError::NoText)?.as_str();
    let mut all = Bindings::new();
    for op in &p.ops {
        let Op::MatchSnippet {
            var,
            lang,
            pattern,
            within,
        } = op
        else {
            continue;
        };
        let Ok(r) = target_range(input, row, *var) else {
            continue;
        };
        let pat = Pattern::compile(&p.strings[*lang as usize], &p.strings[*pattern as usize])?;
        for m in pat.find(src)? {
            let hit = if *within {
                m.range.start <= r.start && r.end <= m.range.end
            } else {
                m.range == r
            };
            if hit {
                tracing::debug!(
                    vars = m.bindings.len(),
                    "snippet bindings gathered for a fix"
                );
                for (k, v) in m.bindings {
                    all.entry(k).or_insert(v);
                }
            }
        }
    }
    Ok(all)
}
