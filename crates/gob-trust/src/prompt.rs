//! The trust review prompt (security.md 2.3): host-derived facts only, TTY only, no auto-approve.
//!
//! [`ReviewFacts`] has no field for pack-supplied prose, so a pack cannot talk to the reader;
//! every string that does appear (pack id, effect names, author) is stripped of control
//! characters. [`render`] puts a widening of effects first and in full. [`review`] approves only
//! on the exact answer, and for a widening or a subprocess only on the typed pack name.
//! [`presence`] refuses a non-terminal or an agent-marked environment before anything is shown.

// frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z

use std::fmt::Write as _;
use std::io::{BufRead, Write};

use tracing::{debug, info, warn};

/// Environment variables that mark a known agent harness (the review refuses to run under one).
pub const AGENT_MARKERS: &[&str] = &["CLAUDECODE", "CLAUDE_CODE", "CODEX_SANDBOX", "AIDER_AGENT"];

/// Longest host-derived string shown, in characters.
const MAX_FIELD: usize = 200;

/// How an effect differs from what was already trusted.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Delta {
    /// Not trusted before: a widening.
    Added,
    /// Already trusted, unchanged.
    Unchanged,
    /// Trusted before, no longer requested: a narrowing.
    Removed,
}

/// One effect the pack requests, with its delta against the trusted set.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EffectLine {
    /// The effect, for example `net api.example.com`.
    pub effect: String,
    /// Its delta.
    pub delta: Delta,
}

/// Everything the review shows; every field is derived by the host, none is pack prose.
#[expect(
    clippy::struct_excessive_bools,
    reason = "each bool is an independent host-derived fact shown on its own line"
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReviewFacts {
    /// Pack id, also the string the person types for a widening.
    pub pack: String,
    /// Digest of the pack tree.
    pub tree_digest: String,
    /// Requested effects with their deltas.
    pub effects: Vec<EffectLine>,
    /// Size in bytes of each binary (name, size).
    pub binaries: Vec<(String, u64)>,
    /// Whether the change is on a protected branch.
    pub on_protected_branch: bool,
    /// Whether the build reproduced.
    pub reproduced: bool,
    /// Whether the commit is signed.
    pub signed: bool,
    /// Author of the last git commit touching the pack.
    pub last_author: String,
    /// Whether the pack asks to run subprocesses.
    pub subprocess: bool,
}

impl ReviewFacts {
    /// True when any effect is added.
    #[must_use]
    pub fn widens(&self) -> bool {
        self.effects.iter().any(|e| e.delta == Delta::Added)
    }

    /// True when approval needs the pack name typed: a widening or a subprocess.
    #[must_use]
    pub fn needs_typed_name(&self) -> bool {
        self.widens() || self.subprocess
    }
}

/// What the person decided.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    /// Trust the pack.
    Approve,
    /// Do not trust it.
    Deny,
}

/// Why the review could not run.
#[derive(Debug, thiserror::Error)]
pub enum PromptError {
    /// Reading the answer or writing the prompt failed.
    #[error("prompt i/o failed: {0}")]
    Io(#[from] std::io::Error),
}

/// Whether a person can be at the other end.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Presence {
    /// Both streams are terminals and no agent marker is set.
    Human,
    /// Stdin or stdout is not a terminal.
    NoTty,
    /// A known agent marker is set in the environment.
    Agent,
}

/// Classify the session from the two stream kinds and the environment lookup `env`.
pub fn presence(
    stdin_tty: bool,
    stdout_tty: bool,
    env: impl Fn(&str) -> Option<String>,
) -> Presence {
    let verdict = if !(stdin_tty && stdout_tty) {
        Presence::NoTty
    } else if AGENT_MARKERS
        .iter()
        .any(|k| env(k).is_some_and(|v| !v.is_empty()))
    {
        Presence::Agent
    } else {
        Presence::Human
    };
    debug!(stdin_tty, stdout_tty, ?verdict, "trust presence");
    verdict
}

/// Strip control characters and cap the length of a host-derived field.
fn clean(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control())
        .take(MAX_FIELD)
        .collect()
}

fn yn(b: bool) -> &'static str {
    if b { "yes" } else { "no" }
}

/// Render the review text: the widening first and in full, then the other host-derived facts.
#[must_use]
pub fn render(facts: &ReviewFacts) -> String {
    let mut out = String::new();
    let line = |out: &mut String, s: String| {
        out.push_str(&s);
        out.push('\n');
    };
    let _ = writeln!(out, "Review of pack {}", clean(&facts.pack));
    let added: Vec<_> = facts
        .effects
        .iter()
        .filter(|e| e.delta == Delta::Added)
        .collect();
    if !added.is_empty() {
        line(&mut out, "WIDENING: this pack asks for new effects".into());
        for e in &added {
            line(&mut out, format!("  + {}", clean(&e.effect)));
        }
    }
    if facts.subprocess {
        line(&mut out, "SUBPROCESS: this pack runs programs".into());
    }
    for e in facts.effects.iter().filter(|e| e.delta != Delta::Added) {
        let mark = if e.delta == Delta::Removed { '-' } else { '=' };
        line(&mut out, format!("  {mark} {}", clean(&e.effect)));
    }
    line(
        &mut out,
        format!("tree digest: {}", clean(&facts.tree_digest)),
    );
    for (name, size) in &facts.binaries {
        line(&mut out, format!("binary: {} ({size} bytes)", clean(name)));
    }
    line(
        &mut out,
        format!("on protected branch: {}", yn(facts.on_protected_branch)),
    );
    line(&mut out, format!("reproduced: {}", yn(facts.reproduced)));
    line(&mut out, format!("signed: {}", yn(facts.signed)));
    line(
        &mut out,
        format!("last git author: {}", clean(&facts.last_author)),
    );
    out
}

/// Show the review and read the answer; approval needs `yes`, or the pack name for a widening or subprocess.
///
/// # Errors
/// [`PromptError::Io`] when the prompt cannot be written or the answer read.
pub fn review(
    facts: &ReviewFacts,
    input: &mut impl BufRead,
    out: &mut impl Write,
) -> Result<Decision, PromptError> {
    out.write_all(render(facts).as_bytes())?;
    let pack = clean(&facts.pack);
    let typed = facts.needs_typed_name();
    if typed {
        write!(
            out,
            "Type the pack name ({pack}) to trust it, anything else denies: "
        )?;
    } else {
        write!(out, "Type yes to trust it, anything else denies: ")?;
    }
    out.flush()?;
    let mut answer = String::new();
    input.read_line(&mut answer)?;
    let answer = answer.trim();
    let expected = if typed { pack.as_str() } else { "yes" };
    let decision = if answer == expected {
        Decision::Approve
    } else {
        Decision::Deny
    };
    if decision == Decision::Approve {
        info!(pack = %pack, typed, "trust review approved");
    } else {
        warn!(pack = %pack, typed, "trust review denied");
    }
    Ok(decision)
}
