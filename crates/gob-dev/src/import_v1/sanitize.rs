//! Redaction of imported text: home paths and local private terms never enter the ledger (~TM4E1PN).
//!
//! The importer renders events itself, so it cannot use the ledger's write-time refusal; it applies
//! the same rules instead, but repairs rather than refuses: a v1 checkout path becomes `<repo>`, a
//! home directory `~`, any other home root `~other`, and a private term its rule label. Hits are
//! reported by label and pattern hash only, never by the matched text.

// frob:ticket 01M43A53W5X4PBCXWCTTM4E1PN
use std::path::Path;

use frob_evidence::scrub::{OTHER_HOME, PathScrub};
use frob_ledger::privacy::{find_home_path, find_home_root};
use frob_ledger::redact::RuleSet;

use super::{ImportError, V1Ticket};

/// Applies the path scrub and the private-term rules to v1 text.
pub struct Sanitizer {
    scrub: PathScrub,
    rules: RuleSet,
}

/// What redaction changed in one ticket, for the report.
#[derive(Debug, Default, Clone)]
pub struct Touched {
    /// A home or checkout path was rewritten.
    pub paths: bool,
    /// Private rules that matched, as `label#hash`.
    pub private: Vec<String>,
}

impl Sanitizer {
    /// A sanitizer for the v1 checkout containing `v1_tickets`, with private rules from `common_dir` (none when absent).
    ///
    /// # Errors
    ///
    /// [`ImportError::Ticket`] when a local privacy file cannot be read (fail closed, like ledger writes).
    pub fn new(v1_tickets: &Path, common_dir: Option<&Path>) -> Result<Self, ImportError> {
        let root = gob_exec::canonical(v1_tickets).unwrap_or_else(|_| v1_tickets.to_path_buf());
        let root = root.parent().unwrap_or(&root).to_path_buf();
        let rules = match common_dir {
            Some(dir) => {
                RuleSet::load_local(dir).map_err(|e| super::ticket_err("privacy", e.to_string()))?
            }
            None => RuleSet::empty(),
        };
        tracing::info!(private_rules = !rules.no_private(), "redaction rules ready");
        Ok(Self {
            scrub: PathScrub::new(&root, &root),
            rules,
        })
    }

    /// Whether any local private-term rule is loaded (a dry run can only find terms it knows).
    #[must_use]
    pub fn has_private_rules(&self) -> bool {
        !self.rules.no_private()
    }

    /// `text` redacted, noting in `touched` what was changed.
    pub fn text(&self, text: &str, touched: &mut Touched) -> String {
        let mut out = self.scrub.apply(text);
        while let Some(range) = find_home_root(out.as_bytes()) {
            out.replace_range(range, OTHER_HOME);
        }
        if out != text {
            touched.paths = true;
        }
        for hit in self.rules.hits(out.as_bytes()) {
            if !hit.builtin {
                touched.private.push(hit.to_string());
            }
        }
        self.rules.apply_private(&out)
    }

    /// Whether `text` still holds an absolute home path (it must not after [`Self::text`]).
    #[must_use]
    pub fn residual(text: &str) -> bool {
        find_home_path(text.as_bytes()).is_some()
    }

    /// Redact every free-text field of `v1` in place; returns what changed.
    pub(super) fn ticket(&self, v1: &mut V1Ticket) -> Touched {
        let mut t = Touched::default();
        let f = &mut v1.front;
        f.title = self.text(&f.title, &mut t);
        for s in f.scope.iter_mut().chain(f.labels.iter_mut()) {
            *s = self.text(s, &mut t);
        }
        for s in &mut f.evidence {
            *s = self.text(s, &mut t);
        }
        for a in &mut f.acceptance {
            a.text = self.text(&a.text, &mut t);
            for e in &mut a.evidence {
                *e = self.text(e, &mut t);
            }
        }
        v1.body = self.text(&v1.body, &mut t);
        if let Some(r) = v1.done_report.take() {
            v1.done_report = Some(self.text(&r, &mut t));
        }
        t.private.sort();
        t.private.dedup();
        t
    }
}
