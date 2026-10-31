//! Pretty TTY decoration for the human text views, built on `frob-present` (docs/design/output.md).
//!
//! Verbs hand back plain pre-rendered rows; [`Theme::decorate`] colours ids, status words,
//! headings and labels only when the stdout stream is a colour-capable terminal, so piped,
//! `NO_COLOR` and `TERM=dumb` output is byte-identical to the plain rows. Nothing here prints:
//! it returns strings, and `gob-cli` owns stdout.
// frob:ticket 01M5XMN8V9MT31K1CR6W1GQTPG

use std::io::IsTerminal;
use std::sync::OnceLock;

use frob_present::{Capabilities, EnvSnapshot, Palette, Role, StreamFacts};
use gob_cli::Payload;

/// Words that read as success, failure or caution wherever they stand alone in a row.
const OK_WORDS: [&str; 7] = [
    "ok", "clean", "passed", "done", "closed", "landed", "approved",
];
/// Words that read as failure.
const ERR_WORDS: [&str; 5] = ["error", "failed", "denied", "blocked", "refused"];
/// Words that read as caution.
const WARN_WORDS: [&str; 4] = ["warning", "stale", "skipped", "snoozed"];
/// A heading longer than this is prose, not a heading.
const HEADING_MAX: usize = 40;
/// A label longer than this is prose, not a `label  value` key.
const LABEL_MAX: usize = 14;

/// How the human text view of this process should look.
#[derive(Debug, Clone)]
pub(crate) struct Theme {
    palette: Palette,
    color: bool,
    /// Columns to fit table rows into; `None` when not a terminal or the width is unknown.
    width: Option<usize>,
}

impl Theme {
    /// A theme with no colour and no width limit: the byte-identical plain form.
    #[cfg(test)]
    pub(crate) fn plain() -> Self {
        Self {
            palette: Palette::plain(),
            color: false,
            width: None,
        }
    }

    /// A coloured theme limited to `width` columns (tests; `None` for unlimited).
    #[cfg(test)]
    pub(crate) fn colored(width: Option<usize>) -> Self {
        Self {
            palette: Palette::colored(),
            color: true,
            width,
        }
    }

    /// Derive the theme from an environment and stream facts (pure; the width needs `COLUMNS` or a measured width).
    pub(crate) fn detect(env: &EnvSnapshot, stdout_tty: bool, width: Option<u16>) -> Self {
        let caps = Capabilities::detect(
            env,
            StreamFacts {
                stdout_tty,
                stderr_tty: false,
                width,
            },
        );
        let theme = Self {
            palette: if caps.stdout.color {
                Palette::colored()
            } else {
                Palette::plain()
            },
            color: caps.stdout.color,
            width: stdout_tty.then_some(usize::from(caps.width)),
        };
        tracing::debug!(
            color = theme.color,
            width = ?theme.width,
            stdout_tty,
            "pretty: theme detected"
        );
        theme
    }

    /// The width table rows are fitted to, if any.
    #[cfg(test)]
    pub(crate) fn width(&self) -> Option<usize> {
        self.width
    }

    /// Wrap `text` in the style of `role`; plain text on a no-colour theme.
    pub(crate) fn paint(&self, role: Role, text: &str) -> String {
        self.palette.paint(role, text)
    }

    /// Colour the rows: ids, status words, headings and labels. Identity on a no-colour theme.
    pub(crate) fn decorate(&self, rows: Vec<String>) -> Vec<String> {
        if !self.color {
            return rows;
        }
        let out: Vec<String> = rows
            .iter()
            .enumerate()
            .map(|(i, line)| {
                if line.contains('\x1b') {
                    return line.clone();
                }
                let prev_blank = i == 0 || rows[i - 1].trim().is_empty();
                let next_indented = rows.get(i + 1).is_some_and(|n| n.starts_with("  "));
                if prev_blank && next_indented && is_heading(line) {
                    return self.paint(Role::Info, line);
                }
                self.decorate_line(line)
            })
            .collect();
        tracing::debug!(rows = out.len(), "pretty: rows decorated");
        out
    }

    /// Colour one row: a leading `label  value` key, then every token that reads as an id or status.
    fn decorate_line(&self, line: &str) -> String {
        let (label_end, rest_start) = label_span(line);
        let mut out = String::with_capacity(line.len() + 16);
        let label = &line[..label_end];
        let indent = label.len() - label.trim_start().len();
        out.push_str(&label[..indent]);
        let key = &label[indent..];
        if !key.is_empty() {
            out.push_str(&self.paint(Role::Dim, key));
        }
        out.push_str(&line[label_end..rest_start]);
        out.push_str(&self.tokens(&line[rest_start..]));
        out
    }

    /// Colour the id and status tokens of `text`, leaving separators untouched.
    fn tokens(&self, text: &str) -> String {
        let mut out = String::with_capacity(text.len() + 16);
        let mut word = String::new();
        let flush = |word: &mut String, out: &mut String| {
            if word.is_empty() {
                return;
            }
            out.push_str(&match role_of(word) {
                Some(role) => self.paint(role, word),
                None => word.clone(),
            });
            word.clear();
        };
        for ch in text.chars() {
            if ch.is_ascii_alphanumeric() || ch == '~' {
                word.push(ch);
            } else {
                flush(&mut word, &mut out);
                out.push(ch);
            }
        }
        flush(&mut word, &mut out);
        out
    }

    /// Cut `line` to the theme width with a trailing `...`; untouched when it fits or no width is set.
    pub(crate) fn fit(&self, line: &str, reserve: usize) -> String {
        let Some(width) = self.width else {
            return line.to_owned();
        };
        let max = width.saturating_sub(reserve).max(4);
        if line.chars().count() <= max {
            return line.to_owned();
        }
        let mut cut: String = line.chars().take(max - 3).collect();
        cut.push_str("...");
        tracing::debug!(max, "pretty: row truncated to terminal width");
        cut
    }
}

/// Whether `line` reads as a section heading: short, capitalised, no trailing punctuation.
fn is_heading(line: &str) -> bool {
    line.len() <= HEADING_MAX
        && line.chars().next().is_some_and(|c| c.is_ascii_uppercase())
        && !line.contains("  ")
        && !line.ends_with(['.', ':', ',', ';'])
        && line
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || " -".contains(c))
}

/// Byte spans of a leading `label  value` key: `(end of label, start of value)`; `(0, 0)` when absent.
fn label_span(line: &str) -> (usize, usize) {
    let trimmed = line.trim_start();
    let indent = line.len() - trimmed.len();
    let Some(gap) = trimmed.find("  ") else {
        return (0, 0);
    };
    let label = &trimmed[..gap];
    let value = trimmed[gap..].trim_start();
    let plausible = !label.is_empty()
        && label.len() <= LABEL_MAX
        && !value.is_empty()
        && label.chars().next().is_some_and(|c| c.is_ascii_lowercase())
        && label.chars().all(|c| c.is_ascii_lowercase() || c == ' ');
    if !plausible {
        return (0, 0);
    }
    let rest = line.len() - value.len();
    (indent + gap, rest)
}

/// The semantic role of a whole word: ticket handle, rule id, or a status word.
fn role_of(word: &str) -> Option<Role> {
    if is_handle(word) || is_rule_id(word) {
        return Some(Role::Id);
    }
    if OK_WORDS.contains(&word) {
        Some(Role::Ok)
    } else if ERR_WORDS.contains(&word) {
        Some(Role::Error)
    } else if WARN_WORDS.contains(&word) {
        Some(Role::Warn)
    } else {
        None
    }
}

/// `~` plus seven Crockford characters.
fn is_handle(word: &str) -> bool {
    word.strip_prefix('~').is_some_and(|h| {
        h.len() == 7
            && h.chars()
                .all(|c| c.is_ascii_digit() || c.is_ascii_uppercase())
    })
}

/// Two or more capitals then three or more digits, e.g. `SCOPE001`.
fn is_rule_id(word: &str) -> bool {
    let letters = word.chars().take_while(char::is_ascii_uppercase).count();
    let digits = word.len() - letters;
    letters >= 2 && digits >= 3 && word[letters..].chars().all(|c| c.is_ascii_digit())
}

/// The theme of this process: stdout terminal-ness, environment and `COLUMNS`, detected once.
pub(crate) fn theme() -> &'static Theme {
    static THEME: OnceLock<Theme> = OnceLock::new();
    THEME.get_or_init(|| {
        Theme::detect(
            &EnvSnapshot::from_process(),
            std::io::stdout().is_terminal(),
            None,
        )
    })
}

/// Builder sugar: attach rows to a payload, decorated for this process's terminal.
pub(crate) trait PrettyExt: Sized {
    /// Like `with_rendered`, with colour applied when stdout is a colour terminal.
    fn with_pretty(self, rows: Vec<String>) -> Self;
}

impl<T> PrettyExt for Payload<T> {
    /// Attach the decorated rows as the pre-rendered text view.
    fn with_pretty(self, rows: Vec<String>) -> Self {
        let t = theme();
        let fitted = rows.iter().map(|r| t.fit(r, 0)).collect();
        self.with_rendered(t.decorate(fitted))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env(pairs: &[(&str, &str)]) -> EnvSnapshot {
        EnvSnapshot::from_pairs(pairs.iter().copied())
    }

    fn rows(lines: &[&str]) -> Vec<String> {
        lines.iter().map(|s| (*s).to_owned()).collect()
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.decorate
    #[test]
    fn plain_theme_is_the_identity() {
        let input = rows(&["Tickets", "  ~ABCDEFG  closed  SCOPE001"]);
        assert_eq!(Theme::plain().decorate(input.clone()), input);
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.detect
    #[test]
    fn piped_no_color_and_dumb_streams_get_no_color() {
        let tty = env(&[("TERM", "xterm")]);
        assert!(Theme::detect(&tty, true, Some(80)).color);
        assert!(!Theme::detect(&tty, false, Some(80)).color);
        assert!(!Theme::detect(&env(&[("TERM", "xterm"), ("NO_COLOR", "1")]), true, None).color);
        assert!(!Theme::detect(&env(&[("TERM", "dumb")]), true, None).color);
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.detect
    #[test]
    fn width_comes_from_columns_only_on_a_terminal() {
        let e = env(&[("TERM", "xterm"), ("COLUMNS", "50")]);
        assert_eq!(Theme::detect(&e, true, None).width(), Some(50));
        assert_eq!(Theme::detect(&e, false, None).width(), None);
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.decorate
    #[test]
    fn colored_theme_styles_ids_status_headings_and_labels() {
        let out = Theme::colored(None).decorate(rows(&[
            "Tickets",
            "  ~ABCDEFG  closed  SCOPE001",
            "",
            "status      blocked",
        ]));
        assert!(out[0].contains('\x1b'), "heading styled: {:?}", out[0]);
        assert!(out[1].contains("\x1b[1m~ABCDEFG"));
        assert!(out[1].contains("closed"));
        assert!(out[3].contains("status"));
        assert!(out[3].contains("\x1b["));
        // stripping the escapes gives back the plain row
        let strip = |s: &str| {
            let mut o = String::new();
            let mut esc = false;
            for c in s.chars() {
                match (esc, c) {
                    (false, '\x1b') => esc = true,
                    (true, 'm') => esc = false,
                    (false, c) => o.push(c),
                    _ => {}
                }
            }
            o
        };
        assert_eq!(strip(&out[1]), "  ~ABCDEFG  closed  SCOPE001");
        assert_eq!(strip(&out[3]), "status      blocked");
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.decorate
    #[test]
    fn already_styled_rows_and_prose_are_left_alone() {
        let styled = "\x1b[31mred\x1b[0m done".to_owned();
        let out = Theme::colored(None).decorate(vec![styled.clone(), "the build is ok.".into()]);
        assert_eq!(out[0], styled);
        assert!(out[1].starts_with("the build is "));
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.fit
    #[test]
    fn fit_truncates_to_the_width_with_an_ascii_ellipsis() {
        let t = Theme::colored(Some(20));
        assert_eq!(t.fit("short", 2), "short");
        let cut = t.fit("abcdefghijklmnopqrstuvwxyz", 2);
        assert_eq!(cut.chars().count(), 18);
        assert!(cut.ends_with("..."));
        assert_eq!(
            Theme::plain().fit("abcdefghijklmnopqrstuvwxyz", 2).len(),
            26
        );
        // a hopeless width still leaves a few characters
        assert!(
            Theme::colored(Some(1))
                .fit("abcdefghij", 2)
                .ends_with("...")
        );
    }

    // frob:tests crates/frob/src/pretty.rs::PrettyExt.with_pretty
    #[test]
    fn with_pretty_sets_the_rendered_rows() {
        let p = Payload::new(1_u8).with_pretty(rows(&["x"]));
        assert_eq!(p.rendered, Some(rows(&["x"])));
    }

    // frob:tests crates/frob/src/pretty.rs::Theme.decorate
    #[test]
    fn table_rows_keep_their_visible_alignment_when_coloured() {
        let table = crate::text_view::table(&[
            vec!["~ABCDEFG".into(), "done".into(), "first".into()],
            vec!["~HIJKLMN".into(), "blocked".into(), "second".into()],
        ]);
        let out = Theme::colored(None).decorate(table.clone());
        assert!(out.iter().all(|l| l.contains('\x1b')));
        let visible = |s: &str| {
            let mut o = String::new();
            let mut esc = false;
            for c in s.chars() {
                match (esc, c) {
                    (false, '\x1b') => esc = true,
                    (true, 'm') => esc = false,
                    (false, c) => o.push(c),
                    _ => {}
                }
            }
            o
        };
        let plain: Vec<String> = out.iter().map(|l| visible(l)).collect();
        assert_eq!(plain, table);
    }
}
