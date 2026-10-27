//! Semantic palette and the glyph table (one place, ASCII fallback beside each).

use anstyle::{AnsiColor, Style};

/// Semantic role a styled span plays; callers pick roles, never colours.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// Passed gate, closed ticket.
    Ok,
    /// Warning finding, stale lease.
    Warn,
    /// Error finding, refusal.
    Error,
    /// Stage name, verb heading.
    Info,
    /// Elapsed time, secondary ids, paths.
    Dim,
    /// Ticket and rule ids.
    Id,
    /// The changed, selected or current row.
    Accent,
}

/// Styles by [`Role`], 16 ANSI colours only.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Palette {
    ok: Style,
    warn: Style,
    error: Style,
    info: Style,
    dim: Style,
    id: Style,
    accent: Style,
}

impl Palette {
    /// The default coloured palette from the design table.
    pub fn colored() -> Self {
        let fg = |c: AnsiColor| Style::new().fg_color(Some(c.into()));
        Self {
            ok: fg(AnsiColor::Green),
            warn: fg(AnsiColor::Yellow),
            error: fg(AnsiColor::Red).bold(),
            info: fg(AnsiColor::Cyan).bold(),
            dim: fg(AnsiColor::BrightBlack),
            id: Style::new().bold(),
            accent: fg(AnsiColor::Magenta),
        }
    }

    /// All-empty styles: what a no-colour stream renders with.
    pub fn plain() -> Self {
        let s = Style::new();
        Self {
            ok: s,
            warn: s,
            error: s,
            info: s,
            dim: s,
            id: s,
            accent: s,
        }
    }

    /// The style for a role.
    pub fn style(&self, role: Role) -> Style {
        match role {
            Role::Ok => self.ok,
            Role::Warn => self.warn,
            Role::Error => self.error,
            Role::Info => self.info,
            Role::Dim => self.dim,
            Role::Id => self.id,
            Role::Accent => self.accent,
        }
    }

    /// Wrap `text` in the role's style; returns it untouched when the style is empty.
    pub fn paint(&self, role: Role, text: &str) -> String {
        let style = self.style(role);
        if style == Style::new() {
            return text.to_owned();
        }
        format!("{style}{text}{style:#}")
    }
}

/// Glyph set: unicode with a runtime-selected ASCII fallback.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Glyphs {
    /// Spinner frames, cycled by redraw count.
    pub spinner: &'static [&'static str],
    /// Marker for a passed stage.
    pub ok: &'static str,
    /// Marker for a failed stage.
    pub fail: &'static str,
    /// Marker for a warning or skipped stage.
    pub warn: &'static str,
    /// Filled bar cell.
    pub fill: char,
    /// Empty bar cell.
    pub empty: char,
}

impl Glyphs {
    /// Unicode glyphs (braille spinner, check and cross marks).
    pub fn unicode() -> Self {
        Self {
            spinner: &[
                "\u{280b}", "\u{2819}", "\u{2839}", "\u{2838}", "\u{283c}", "\u{2834}", "\u{2826}",
                "\u{2827}", "\u{2807}", "\u{280f}",
            ],
            ok: "\u{2713}",
            fail: "\u{2717}",
            warn: "!",
            fill: '\u{2588}',
            empty: '\u{2591}',
        }
    }

    /// ASCII-only fallback (`|/-\`).
    pub fn ascii() -> Self {
        Self {
            spinner: &["|", "/", "-", "\\"],
            ok: "+",
            fail: "x",
            warn: "!",
            fill: '#',
            empty: '-',
        }
    }

    /// Pick by the `ascii` capability flag.
    pub fn select(ascii: bool) -> Self {
        if ascii {
            Self::ascii()
        } else {
            Self::unicode()
        }
    }
}
