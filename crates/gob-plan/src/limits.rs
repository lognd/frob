//! Resource caps for plans and findings (security.md section 2.5): every breach is a typed
//! [`Breach`], which callers surface as `Unresolved budget`, or as a located load error for
//! regexes.

use regex::RegexBuilder;

use crate::exec::relations::Relations;

/// The caps one run enforces; the defaults are the shipped ones.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    /// Most findings kept per file.
    pub findings_per_file: usize,
    /// Longest finding message, in bytes.
    pub message_bytes: usize,
    /// Most bytes of findings output for the whole run.
    pub output_bytes: usize,
    /// Most condition evaluations per tier-2 plan run.
    pub plan_steps: u64,
    /// Largest compiled regex, in bytes.
    pub regex_size: usize,
    /// Deepest regex group nesting.
    pub regex_nesting: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            findings_per_file: 1_000,
            message_bytes: 4 * 1024,
            output_bytes: 64 * 1024 * 1024,
            plan_steps: crate::exec::relations::DEFAULT_STEP_BUDGET,
            regex_size: 1 << 20,
            regex_nesting: 32,
        }
    }
}

/// Which cap was breached.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum Breach {
    /// A file produced more findings than allowed.
    #[error("budget: more than {limit} findings in one file")]
    Findings {
        /// The cap.
        limit: usize,
    },
    /// A message is longer than allowed.
    #[error("budget: message of {len} bytes exceeds {limit}")]
    Message {
        /// The message length.
        len: usize,
        /// The cap.
        limit: usize,
    },
    /// The run's total output is larger than allowed.
    #[error("budget: total output exceeds {limit} bytes")]
    Output {
        /// The cap.
        limit: usize,
    },
    /// A regex compiles to more than the size cap, or does not compile.
    #[error("regex rejected: {why}")]
    RegexSize {
        /// The compiler's reason.
        why: String,
    },
    /// A regex nests groups deeper than allowed.
    #[error("regex nests groups {depth} deep, more than {limit}")]
    RegexNesting {
        /// The measured depth.
        depth: usize,
        /// The cap.
        limit: usize,
    },
}

/// A regex breach with the place in the pack it came from.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{file}:{line}: {breach}")]
pub struct LimitError {
    /// The pack file.
    pub file: String,
    /// The 1-based line of the pattern.
    pub line: u32,
    /// What was breached.
    pub breach: Breach,
}

impl Limits {
    /// Applies the plan step cap to `rels`; an overrun becomes `Unresolved budget` for that
    /// rule and file only, other rules still run.
    #[must_use]
    pub fn relations(&self, rels: Relations) -> Relations {
        rels.with_step_budget(self.plan_steps)
    }

    /// Checks a pattern's size and nesting at pack load, naming `file` and `line` on refusal.
    ///
    /// # Errors
    /// [`LimitError`] when the regex is over the size or nesting cap or does not compile.
    pub fn check_regex(&self, src: &str, file: &str, line: u32) -> Result<(), LimitError> {
        let fail = |breach| {
            tracing::warn!(file, line, %breach, "regex refused at load");
            LimitError {
                file: file.to_owned(),
                line,
                breach,
            }
        };
        let depth = nesting_depth(src);
        if depth > self.regex_nesting {
            return Err(fail(Breach::RegexNesting {
                depth,
                limit: self.regex_nesting,
            }));
        }
        RegexBuilder::new(src)
            .size_limit(self.regex_size)
            .nest_limit(u32::try_from(self.regex_nesting).unwrap_or(u32::MAX))
            .build()
            .map(|_| ())
            .map_err(|e| fail(Breach::RegexSize { why: e.to_string() }))
    }
}

/// The deepest group nesting of a regex source, ignoring escapes and character classes.
fn nesting_depth(src: &str) -> usize {
    let (mut depth, mut max, mut class, mut esc) = (0usize, 0usize, false, false);
    for c in src.chars() {
        if esc {
            esc = false;
            continue;
        }
        match c {
            '\\' => esc = true,
            '[' => class = true,
            ']' => class = false,
            '(' if !class => {
                depth += 1;
                max = max.max(depth);
            }
            ')' if !class => depth = depth.saturating_sub(1),
            _ => {}
        }
    }
    max
}

/// Running output totals for one run, charged per finding.
#[derive(Debug, Clone)]
pub struct Meter {
    limits: Limits,
    file_findings: usize,
    total_bytes: usize,
}

impl Meter {
    /// A meter with nothing charged yet.
    #[must_use]
    pub fn new(limits: Limits) -> Self {
        Self {
            limits,
            file_findings: 0,
            total_bytes: 0,
        }
    }

    /// Starts a new file: resets the per-file finding count.
    pub fn next_file(&mut self) {
        self.file_findings = 0;
    }

    /// Charges one finding with a message of `len` bytes.
    ///
    /// # Errors
    /// The [`Breach`] that the finding would cause; nothing is charged then.
    pub fn charge(&mut self, len: usize) -> Result<(), Breach> {
        let l = &self.limits;
        let breach = if self.file_findings >= l.findings_per_file {
            Breach::Findings {
                limit: l.findings_per_file,
            }
        } else if len > l.message_bytes {
            Breach::Message {
                len,
                limit: l.message_bytes,
            }
        } else if self.total_bytes.saturating_add(len) > l.output_bytes {
            Breach::Output {
                limit: l.output_bytes,
            }
        } else {
            self.file_findings += 1;
            self.total_bytes += len;
            return Ok(());
        };
        tracing::warn!(%breach, "output cap breached");
        Err(breach)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-plan/src/limits.rs::relations
    #[test]
    fn relations_carry_the_plan_step_cap() {
        let l = Limits {
            plan_steps: 17,
            ..Limits::default()
        };
        assert_eq!(l.relations(Relations::new()).step_budget, 17);
    }

    // frob:tests crates/gob-plan/src/limits.rs::check_regex
    #[test]
    fn oversized_regex_is_rejected_with_location() {
        let l = Limits {
            regex_size: 1000,
            ..Limits::default()
        };
        let e = l.check_regex("(a{100}){100}", "pack/r.grl", 7).unwrap_err();
        assert_eq!((e.file.as_str(), e.line), ("pack/r.grl", 7));
        assert!(matches!(e.breach, Breach::RegexSize { .. }));
        assert!(l.check_regex("a+b", "p", 1).is_ok());
    }

    // frob:tests crates/gob-plan/src/limits.rs::check_regex
    #[test]
    fn deep_nesting_is_rejected_and_classes_do_not_count() {
        let l = Limits::default();
        let deep = format!("{}a{}", "(".repeat(40), ")".repeat(40));
        assert!(matches!(
            l.check_regex(&deep, "p", 2).unwrap_err().breach,
            Breach::RegexNesting { depth: 40, .. }
        ));
        assert!(l.check_regex(r"[(((]\(\(x", "p", 3).is_ok());
    }

    // frob:tests crates/gob-plan/src/limits.rs::charge
    #[test]
    fn meter_caps_findings_messages_and_output() {
        let l = Limits {
            findings_per_file: 2,
            message_bytes: 10,
            output_bytes: 15,
            ..Limits::default()
        };
        let mut m = Meter::new(l);
        assert!(m.charge(8).is_ok());
        assert!(matches!(m.charge(11), Err(Breach::Message { .. })));
        assert!(matches!(m.charge(8), Err(Breach::Output { .. })));
        assert!(m.charge(7).is_ok());
        assert!(matches!(m.charge(0), Err(Breach::Findings { .. })));
        m.next_file();
        assert!(m.charge(0).is_ok());
    }
}
