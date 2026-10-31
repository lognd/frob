//! The `Presenter` trait and its `Quiet`, `Plain` and `Live` implementations.

use std::io::Write;
use std::sync::Mutex;
use std::time::Duration;

use tracing::debug;

use crate::caps::Capabilities;
use crate::error::PresentError;
use crate::palette::{Glyphs, Palette, Role};
use crate::stage::{Outcome, ProfileReport, StageId};
use crate::widget::{fmt_elapsed, status_line};

/// ANSI: carriage return then erase the whole line.
const CLEAR_LINE: &str = "\r\x1b[2K";

/// Sink for stage events and human lines; all methods write through an injected writer.
///
/// # Errors
///
/// Every method returns [`PresentError`] when the writer fails or the state lock is poisoned.
#[allow(clippy::missing_errors_doc)] // documented once on the trait above
pub trait Presenter: Send + Sync {
    /// A stage began; `total` is the known step count when there is one.
    fn stage_start(&self, stage: &StageId, total: Option<u64>) -> Result<(), PresentError>;
    /// Progress inside the current stage (monotonic).
    fn stage_progress(&self, stage: &StageId, done: u64) -> Result<(), PresentError>;
    /// A stage finished with its measured duration and outcome.
    fn stage_end(
        &self,
        stage: &StageId,
        elapsed: Duration,
        outcome: Outcome,
    ) -> Result<(), PresentError>;
    /// Print a human line above any live widget.
    fn line(&self, role: Role, text: &str) -> Result<(), PresentError>;
    /// Called once at verb exit; renders the profile report.
    fn finish(&self, report: &ProfileReport) -> Result<(), PresentError>;
}

/// Which implementation [`select`] chose.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    /// No output at all.
    Quiet,
    /// One line per event.
    Plain,
    /// Redrawing bar or throbber.
    Live,
}

/// Choose a presenter for stderr: pure function of capabilities and `--quiet`.
pub fn select(caps: &Capabilities, quiet: bool) -> Kind {
    let kind = if quiet {
        Kind::Quiet
    } else if caps.interactive {
        Kind::Live
    } else {
        Kind::Plain
    };
    debug!(
        ?kind,
        quiet,
        interactive = caps.interactive,
        "presenter selected"
    );
    kind
}

/// Build the presenter [`select`] picks, styled per the stderr colour capability.
pub fn build<W: Write + Send + 'static>(
    caps: &Capabilities,
    quiet: bool,
    writer: W,
) -> Box<dyn Presenter> {
    let palette = if caps.stderr.color {
        Palette::colored()
    } else {
        Palette::plain()
    };
    match select(caps, quiet) {
        Kind::Quiet => Box::new(Quiet),
        Kind::Plain => Box::new(Plain::new(writer, palette, Glyphs::select(caps.ascii))),
        Kind::Live => Box::new(Live::new(
            writer,
            palette,
            Glyphs::select(caps.ascii),
            caps.width,
        )),
    }
}

/// Presenter that renders nothing.
#[derive(Debug, Clone, Copy, Default)]
pub struct Quiet;

impl Presenter for Quiet {
    /// Ignored.
    fn stage_start(&self, _: &StageId, _: Option<u64>) -> Result<(), PresentError> {
        Ok(())
    }
    /// Ignored.
    fn stage_progress(&self, _: &StageId, _: u64) -> Result<(), PresentError> {
        Ok(())
    }
    /// Ignored.
    fn stage_end(&self, _: &StageId, _: Duration, _: Outcome) -> Result<(), PresentError> {
        Ok(())
    }
    /// Ignored.
    fn line(&self, _: Role, _: &str) -> Result<(), PresentError> {
        Ok(())
    }
    /// Ignored.
    fn finish(&self, _: &ProfileReport) -> Result<(), PresentError> {
        Ok(())
    }
}

fn outcome_role(o: Outcome) -> Role {
    match o {
        Outcome::Ok => Role::Ok,
        Outcome::Warn | Outcome::Skipped => Role::Warn,
        Outcome::Failed => Role::Error,
    }
}

fn outcome_mark(g: &Glyphs, o: Outcome) -> &'static str {
    match o {
        Outcome::Ok => g.ok,
        Outcome::Failed => g.fail,
        Outcome::Warn | Outcome::Skipped => g.warn,
    }
}

/// The completed-stage line shared by `Plain` and `Live`.
fn end_line(p: &Palette, g: &Glyphs, stage: &StageId, elapsed: Duration, o: Outcome) -> String {
    format!(
        "{} {} {} {}",
        p.paint(outcome_role(o), outcome_mark(g, o)),
        p.paint(Role::Info, stage.as_str()),
        p.paint(outcome_role(o), o.label()),
        p.paint(Role::Dim, &fmt_elapsed(elapsed)),
    )
}

/// The profile report block shared by `Plain` and `Live`.
fn report_lines(p: &Palette, report: &ProfileReport) -> Vec<String> {
    if report.stages.is_empty() {
        return Vec::new();
    }
    let total = report.total();
    let slowest = report.slowest_above(0.5).map(|s| s.stage.clone());
    let mut out = vec![p.paint(Role::Info, "profile")];
    for s in &report.stages {
        let role = if slowest.as_ref() == Some(&s.stage) {
            Role::Warn
        } else {
            Role::Dim
        };
        let share = if total.is_zero() {
            0.0
        } else {
            s.elapsed.as_secs_f64() / total.as_secs_f64() * 100.0
        };
        out.push(p.paint(
            role,
            &format!("  {} {} {share:.0}%", s.stage, fmt_elapsed(s.elapsed)),
        ));
    }
    out.push(p.paint(Role::Dim, &format!("  total {}", fmt_elapsed(total))));
    out
}

fn write_lines<W: Write>(w: &mut W, lines: &[String]) -> Result<(), PresentError> {
    for l in lines {
        writeln!(w, "{l}")?;
    }
    w.flush()?;
    Ok(())
}

/// One line per event; no cursor control. For CI, dumb terminals and piped stderr.
pub struct Plain<W: Write + Send> {
    out: Mutex<W>,
    palette: Palette,
    glyphs: Glyphs,
}

impl<W: Write + Send> Plain<W> {
    /// Create a plain presenter over `out`.
    pub fn new(out: W, palette: Palette, glyphs: Glyphs) -> Self {
        Self {
            out: Mutex::new(out),
            palette,
            glyphs,
        }
    }

    fn emit(&self, lines: &[String]) -> Result<(), PresentError> {
        let mut w = self.out.lock().map_err(|_| PresentError::Poisoned)?;
        write_lines(&mut *w, lines)
    }
}

impl<W: Write + Send> Presenter for Plain<W> {
    /// Print `> stage` (with the step count when known).
    fn stage_start(&self, stage: &StageId, total: Option<u64>) -> Result<(), PresentError> {
        let count = total.map_or_else(String::new, |t| format!(" ({t} steps)"));
        self.emit(&[format!(
            "{} {}{}",
            self.palette.paint(Role::Accent, ">"),
            self.palette.paint(Role::Info, stage.as_str()),
            self.palette.paint(Role::Dim, &count),
        )])
    }
    /// Progress prints nothing: plain output has no redraw.
    fn stage_progress(&self, _: &StageId, _: u64) -> Result<(), PresentError> {
        Ok(())
    }
    /// Print the finished-stage line.
    fn stage_end(
        &self,
        stage: &StageId,
        elapsed: Duration,
        outcome: Outcome,
    ) -> Result<(), PresentError> {
        self.emit(&[end_line(
            &self.palette,
            &self.glyphs,
            stage,
            elapsed,
            outcome,
        )])
    }
    /// Print a styled line.
    fn line(&self, role: Role, text: &str) -> Result<(), PresentError> {
        self.emit(&[self.palette.paint(role, text)])
    }
    /// Print the profile report.
    fn finish(&self, report: &ProfileReport) -> Result<(), PresentError> {
        self.emit(&report_lines(&self.palette, report))
    }
}

struct LiveState {
    current: Option<(StageId, u64, Option<u64>)>,
    tick: usize,
}

/// Redrawing bar (known total) or throbber (unknown) on one line, with finished stages
/// scrolling above it.
pub struct Live<W: Write + Send> {
    out: Mutex<(W, LiveState)>,
    palette: Palette,
    glyphs: Glyphs,
    width: u16,
}

impl<W: Write + Send> Live<W> {
    /// Create a live presenter over `out` for a terminal `width` columns wide.
    pub fn new(out: W, palette: Palette, glyphs: Glyphs, width: u16) -> Self {
        Self {
            out: Mutex::new((
                out,
                LiveState {
                    current: None,
                    tick: 0,
                },
            )),
            palette,
            glyphs,
            width,
        }
    }

    /// Advance the throbber one frame and redraw (call from a timer).
    ///
    /// # Errors
    ///
    /// [`PresentError`] when the writer fails or the state lock is poisoned.
    pub fn tick(&self) -> Result<(), PresentError> {
        self.with(|w, st, me| {
            st.tick = st.tick.wrapping_add(1);
            me.draw(w, st)
        })
    }

    /// Update the terminal width (call on resize); the next redraw uses it.
    pub fn set_width(&mut self, width: u16) {
        self.width = width;
    }

    fn with(
        &self,
        f: impl FnOnce(&mut W, &mut LiveState, &Self) -> Result<(), PresentError>,
    ) -> Result<(), PresentError> {
        let mut g = self.out.lock().map_err(|_| PresentError::Poisoned)?;
        let (w, st) = &mut *g;
        f(w, st, self)
    }

    /// Redraw the live line in place (no trailing newline); nothing when no stage is active.
    fn draw(&self, w: &mut W, st: &LiveState) -> Result<(), PresentError> {
        if let Some((stage, done, total)) = &st.current {
            let text = status_line(
                &self.glyphs,
                self.width,
                stage.as_str(),
                *done,
                *total,
                st.tick,
            );
            write!(w, "{CLEAR_LINE}{}", self.palette.paint(Role::Accent, &text))?;
        }
        w.flush()?;
        Ok(())
    }

    /// Print finished lines above the live widget, then redraw it.
    fn scroll(&self, w: &mut W, st: &LiveState, lines: &[String]) -> Result<(), PresentError> {
        write!(w, "{CLEAR_LINE}")?;
        for l in lines {
            writeln!(w, "{l}")?;
        }
        self.draw(w, st)
    }
}

impl<W: Write + Send> Presenter for Live<W> {
    /// Begin drawing the bar or throbber for the stage.
    fn stage_start(&self, stage: &StageId, total: Option<u64>) -> Result<(), PresentError> {
        self.with(|w, st, me| {
            st.current = Some((stage.clone(), 0, total));
            me.draw(w, st)
        })
    }
    /// Move the bar and redraw.
    fn stage_progress(&self, stage: &StageId, done: u64) -> Result<(), PresentError> {
        self.with(|w, st, me| {
            if let Some((_, d, _)) = st.current.as_mut().filter(|(c, _, _)| c == stage) {
                *d = (*d).max(done);
            }
            st.tick = st.tick.wrapping_add(1);
            me.draw(w, st)
        })
    }
    /// Replace the live line with the finished-stage line.
    fn stage_end(
        &self,
        stage: &StageId,
        elapsed: Duration,
        outcome: Outcome,
    ) -> Result<(), PresentError> {
        self.with(|w, st, me| {
            if st.current.as_ref().is_some_and(|(c, _, _)| c == stage) {
                st.current = None;
            }
            let line = end_line(&me.palette, &me.glyphs, stage, elapsed, outcome);
            me.scroll(w, st, &[line])
        })
    }
    /// Print a styled line above the live widget.
    fn line(&self, role: Role, text: &str) -> Result<(), PresentError> {
        self.with(|w, st, me| me.scroll(w, st, &[me.palette.paint(role, text)]))
    }
    /// Clear the live line and print the profile report.
    fn finish(&self, report: &ProfileReport) -> Result<(), PresentError> {
        self.with(|w, st, me| {
            st.current = None;
            me.scroll(w, st, &report_lines(&me.palette, report))
        })
    }
}
