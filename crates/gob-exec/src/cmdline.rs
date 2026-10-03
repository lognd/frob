//! One-string command lines for the few programs that parse a whole line (git driver and hook
//! configuration, `sh -c` scripts, `.ps1` bodies, `cmd /c`), with per-shell quoting.
//!
//! Everywhere else a process takes an argument vector through [`crate::Runner`]; this module is
//! the single place a vector is turned into text (paths.md section 2, D86).

// frob:ticket 01M41RK1G648EJJNRK4G5RJY40
use std::ffi::{OsStr, OsString};
use std::path::{Path, PathBuf};

/// The shell (or parser) that will read the produced line.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shell {
    /// A POSIX `sh`: words bare when safe, otherwise single-quoted with `'\''` for an embedded quote.
    Posix,
    /// The `sh` bundled with git for Windows (MSYS): POSIX rules, and `:` and `\` always quoted so
    /// the MSYS path-list conversion never sees them bare.
    GitForWindowsSh,
    /// PowerShell: single-quoted strings (an embedded quote, smart quotes included, is doubled) and
    /// a leading `&` when the program word is quoted.
    PowerShell,
    /// `cmd.exe`: the Microsoft C runtime argument quoting, then every cmd metacharacter caret-escaped.
    /// A `%` cannot be made fully inert on a cmd command line (variable expansion runs first); a
    /// newline cannot be represented at all.
    Cmd,
}

/// One argument of a command line, an owned OS string that may hold a path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Arg(OsString);

impl Arg {
    /// Wrap anything convertible to an OS string.
    pub fn new(value: impl Into<OsString>) -> Self {
        Self(value.into())
    }

    /// The argument as an OS string.
    pub fn as_os_str(&self) -> &OsStr {
        &self.0
    }
}

impl From<&str> for Arg {
    fn from(v: &str) -> Self {
        Self(v.into())
    }
}
impl From<String> for Arg {
    fn from(v: String) -> Self {
        Self(v.into())
    }
}
impl From<&OsStr> for Arg {
    fn from(v: &OsStr) -> Self {
        Self(v.to_owned())
    }
}
impl From<&Path> for Arg {
    fn from(v: &Path) -> Self {
        Self(v.as_os_str().to_owned())
    }
}
impl From<PathBuf> for Arg {
    fn from(v: PathBuf) -> Self {
        Self(v.into_os_string())
    }
}

/// Quote `argv` into one command line that `shell` splits back into exactly `argv`.
///
/// A non-Unicode argument cannot be written into text; it is converted lossily and a warning is logged.
pub fn command_line(shell: Shell, argv: &[Arg]) -> String {
    let words: Vec<String> = argv.iter().map(text_of).collect();
    let line = match shell {
        Shell::Posix => join_with(&words, |w| posix_word(w, &|c| posix_safe(c))),
        Shell::GitForWindowsSh => {
            join_with(&words, |w| posix_word(w, &|c| posix_safe(c) && c != ':'))
        }
        Shell::PowerShell => powershell_line(&words),
        Shell::Cmd => join_with(&words, cmd_word),
    };
    tracing::debug!(?shell, args = argv.len(), %line, "command line built");
    line
}

fn text_of(arg: &Arg) -> String {
    if let Some(s) = arg.0.to_str() {
        return s.to_owned();
    }
    tracing::warn!(arg = ?arg.0, "non-Unicode argument written lossily into a command line");
    arg.0.to_string_lossy().into_owned()
}

fn join_with(words: &[String], f: impl Fn(&str) -> String) -> String {
    words.iter().map(|w| f(w)).collect::<Vec<_>>().join(" ")
}

/// Characters a POSIX word may contain bare: none is special to `sh`, and `%` is left for git's own expansion.
fn posix_safe(c: char) -> bool {
    c.is_ascii_alphanumeric() || "_-./+=,@%:".contains(c)
}

fn posix_word(word: &str, safe: &dyn Fn(char) -> bool) -> String {
    if !word.is_empty() && word.chars().all(safe) {
        word.to_owned()
    } else {
        format!("'{}'", word.replace('\'', r"'\''"))
    }
}

fn is_ps_quote(c: char) -> bool {
    matches!(c, '\'' | '\u{2018}' | '\u{2019}' | '\u{201A}' | '\u{201B}')
}

fn ps_word(word: &str) -> (String, bool) {
    if !word.is_empty()
        && word
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "_-./".contains(c))
    {
        return (word.to_owned(), false);
    }
    let mut out = String::from("'");
    for c in word.chars() {
        out.push(c);
        if is_ps_quote(c) {
            out.push(c);
        }
    }
    out.push('\'');
    (out, true)
}

fn powershell_line(words: &[String]) -> String {
    let parts: Vec<(String, bool)> = words.iter().map(|w| ps_word(w)).collect();
    let call = parts.first().is_some_and(|(_, quoted)| *quoted);
    let body = parts
        .into_iter()
        .map(|(w, _)| w)
        .collect::<Vec<_>>()
        .join(" ");
    if call { format!("& {body}") } else { body }
}

/// The Microsoft C runtime (`CommandLineToArgvW`) quoting of one argument.
fn msvcrt_word(word: &str) -> String {
    if !word.is_empty() && !word.contains([' ', '\t', '\n', '\u{b}', '"']) {
        return word.to_owned();
    }
    let mut out = String::from("\"");
    let mut slashes = 0usize;
    for c in word.chars() {
        match c {
            '\\' => slashes += 1,
            '"' => {
                out.extend(std::iter::repeat_n('\\', slashes * 2 + 1));
                out.push('"');
                slashes = 0;
            }
            c => {
                out.extend(std::iter::repeat_n('\\', slashes));
                out.push(c);
                slashes = 0;
            }
        }
    }
    out.extend(std::iter::repeat_n('\\', slashes * 2));
    out.push('"');
    out
}

fn cmd_word(word: &str) -> String {
    let mut out = String::new();
    for c in msvcrt_word(word).chars() {
        if "()%!^\"<>&|".contains(c) {
            out.push('^');
        }
        out.push(c);
    }
    out
}
