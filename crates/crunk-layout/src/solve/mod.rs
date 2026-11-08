//! The T1 solver driver (docs/design/crunk/crunk.md section 3): scene to styled tree to taffy
//! compute to layout-solve JSON, deterministic across runs.
//!
//! [`solve_scene_html`] refuses a scene with a duplicate or missing `data-id` (SCENE002, context
//! not solved), maps inline styles, builds the taffy tree with text leaves measured by the
//! bundled-font [`TextMeasurer`], computes it at the viewport and normalizes the result.
//!
//! - Text properties (`font-family`, `font-size`, `letter-spacing`, `line-height`, `white-space`)
//!   inherit; the default is Lato 16px, line-height 1.2.
//! - An element with direct text and no layout children is a `text` node; with children, its text
//!   becomes a synthetic first child `<id>::text`.
//! - Unknown tags and components lay out as empty blocks and add a [`SolveNote::UnknownTag`].
//! - A root larger than the viewport adds a [`SolveNote::PageOverflow`].
//! - Rounding is off in taffy; the output grid snap (1/64 px) is the only quantization.
//! - The solve runs on a thread with a 256 MiB stack so deep trees (depth 200 and beyond) cannot
//!   overflow the caller's stack.
//! - Several roots are each solved against the full viewport from the origin.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

mod collect;
mod error;
mod prepare;
mod textstyle;
mod tokens;
mod tree;

pub use error::{SolveError, SolveNote};

use crunk_scene::SceneDoc;

use crate::FocusGraph;
use crate::output::{LayoutSolve, RawSolve, focus_order};
use crate::style::{FindingKind, ParentCtx, StyleError, StyledScene, TokenMap, style_scene};
use crate::text::TextMeasurer;

/// A solved scene: the document plus the observations made on the way.
#[derive(Debug, Clone, PartialEq)]
pub struct Solved {
    /// The layout-solve document.
    pub doc: LayoutSolve,
    /// Non-fatal notes (unknown tags, missing glyphs, page overflow, style findings).
    pub notes: Vec<SolveNote>,
}

/// Solve `doc` at `viewport` (width, height in px) with `tokens`, measuring text with `fonts`.
///
/// # Errors
/// [`SolveError::Refused`] on a duplicate or missing `data-id`, [`SolveError::Style`] on an
/// unmappable style, [`SolveError::Text`] on a font outside the bundle, and engine or output
/// errors for internal inconsistencies or non-finite values.
pub fn solve_scene_html(
    doc: &SceneDoc,
    tokens: &TokenMap,
    viewport: (f32, f32),
    fonts: &mut TextMeasurer,
) -> Result<Solved, SolveError> {
    let spawned = std::thread::scope(|scope| {
        std::thread::Builder::new()
            .name("crunk-solve".to_owned())
            .stack_size(SOLVE_STACK_BYTES)
            .spawn_scoped(scope, || solve_inner(doc, tokens, viewport, fonts))
            .map(std::thread::ScopedJoinHandle::join)
    });
    match spawned {
        Ok(Ok(result)) => result,
        Ok(Err(panic)) => std::panic::resume_unwind(panic),
        Err(e) => Err(SolveError::Engine(format!(
            "cannot start solver thread: {e}"
        ))),
    }
}

/// Stack for the solver thread: taffy recurses per tree level, so deep scenes need headroom.
const SOLVE_STACK_BYTES: usize = 256 * 1024 * 1024;

fn solve_inner(
    doc: &SceneDoc,
    tokens: &TokenMap,
    viewport: (f32, f32),
    fonts: &mut TextMeasurer,
) -> Result<Solved, SolveError> {
    let styled = style_or_refuse(doc, tokens)?;
    let prep = prepare::prepare(doc, &styled, tokens)?;
    let mut built = tree::build(&prep)?;
    let mut notes: Vec<SolveNote> = styled.findings.into_iter().map(SolveNote::Style).collect();
    collect::compute(&mut built, viewport, fonts)?;
    let laid = collect::collect(&built, viewport, fonts, &mut notes)?;
    let raw = RawSolve {
        viewport_width: viewport.0,
        viewport_height: viewport.1,
        nodes: laid,
        focus_order: focus_order(&FocusGraph::from_scene(doc)),
    };
    tracing::debug!(nodes = raw.nodes.len(), notes = notes.len(), "scene solved");
    Ok(Solved {
        doc: raw.finish()?,
        notes,
    })
}

/// Style the scene, turning SCENE002 conditions into a refusal.
fn style_or_refuse(doc: &SceneDoc, tokens: &TokenMap) -> Result<StyledScene, SolveError> {
    let styled = match style_scene(doc, tokens, ParentCtx::DEFINITE) {
        Ok(s) => s,
        Err(errors) => return Err(refuse_or_style(errors)),
    };
    let missing: Vec<String> = styled
        .findings
        .iter()
        .filter(|f| f.kind == FindingKind::MissingDataId)
        .map(ToString::to_string)
        .collect();
    if missing.is_empty() {
        Ok(styled)
    } else {
        tracing::warn!(count = missing.len(), "missing data-id: context not solved");
        Err(SolveError::Refused(missing))
    }
}

fn refuse_or_style(errors: Vec<StyleError>) -> SolveError {
    let dups: Vec<String> = errors
        .iter()
        .filter(|e| matches!(e, StyleError::DuplicateDataId { .. }))
        .map(ToString::to_string)
        .collect();
    if dups.is_empty() {
        SolveError::Style(errors)
    } else {
        tracing::warn!(count = dups.len(), "duplicate data-id: context not solved");
        SolveError::Refused(dups)
    }
}
