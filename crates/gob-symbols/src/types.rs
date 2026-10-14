//! Type facts from a bound checker (ty, pyright) and the trust policy that decides what an annotation proves.
//!
//! An annotation is a claim, not a guarantee (docs/design/cohesion.md 2.2). Under
//! `[types] trust = "checked"` a Python annotation resolves a call exactly (Must) only
//! when the checker ran clean on the caller's file and no ignore comment sits on the
//! call's line; otherwise the annotated target is only claimed (May). `"annotated"`
//! always claims May and `"none"` keeps annotations as hints that never narrow a call.

// frob:ticket 01M4CXSWZ95SVDADAB97TYG963

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

/// How far an annotation is trusted (`[types] trust`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TypesTrust {
    /// Exact only in a file the checker ran clean on (the default).
    #[default]
    Checked,
    /// Annotations are claimed (May) whether or not a checker agrees; explicitly unsound.
    Annotated,
    /// Annotations are hints only and never narrow a call.
    None,
}

impl TypesTrust {
    /// Parses the `[types] trust` spelling (`checked`, `annotated`, `none`).
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "checked" => Some(Self::Checked),
            "annotated" => Some(Self::Annotated),
            "none" => Some(Self::None),
            _ => None,
        }
    }
}

/// What an annotated receiver type proves at one call site.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AnnotationWeight {
    /// The checker vouches for the annotation: the target is exact.
    Exact,
    /// The annotation is a claim: the target is a May candidate.
    Claimed,
    /// The annotation is a hint only: the call is not narrowed.
    Hint,
}

/// Checker results for a run: which files checked clean and which lines carry ignore comments.
#[derive(Debug, Clone, Default)]
pub struct TypeFacts {
    /// The trust policy in force.
    pub trust: TypesTrust,
    /// Files the checker ran clean on, in strict configuration.
    clean: BTreeSet<String>,
    /// One-based lines holding an ignore comment, by file.
    ignored: BTreeMap<String, BTreeSet<u32>>,
}

impl TypeFacts {
    /// Facts under `trust` with no clean file (every annotation is a claim).
    pub fn new(trust: TypesTrust) -> Self {
        Self {
            trust,
            ..Self::default()
        }
    }

    /// Records that the checker reported nothing for `path`.
    pub fn mark_clean(&mut self, path: &str) {
        tracing::debug!(path, "type checker clean");
        self.clean.insert(path.to_owned());
    }

    /// Records the `type: ignore`, `pyright: ignore` and `ty: ignore` comment lines of `text` for `path`.
    pub fn scan_ignores(&mut self, path: &str, text: &str) {
        for (i, line) in text.lines().enumerate() {
            let Some((_, comment)) = line.split_once('#') else {
                continue;
            };
            if ["type: ignore", "pyright: ignore", "ty: ignore"]
                .iter()
                .any(|m| comment.contains(m))
            {
                let n = u32::try_from(i + 1).unwrap_or(u32::MAX);
                self.ignored.entry(path.to_owned()).or_default().insert(n);
            }
        }
    }

    /// What an annotation on a call at `path:line` proves under the trust policy.
    pub fn weight(&self, path: &str, line: u32) -> AnnotationWeight {
        match self.trust {
            TypesTrust::None => AnnotationWeight::Hint,
            TypesTrust::Annotated => AnnotationWeight::Claimed,
            TypesTrust::Checked => {
                let demoted = self.ignored.get(path).is_some_and(|l| l.contains(&line));
                if self.clean.contains(path) && !demoted {
                    AnnotationWeight::Exact
                } else {
                    AnnotationWeight::Claimed
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/types.rs::TypeFacts.weight
    #[test]
    fn clean_file_is_exact_failing_is_claimed_ignore_demotes() {
        let mut f = TypeFacts::new(TypesTrust::Checked);
        assert_eq!(f.weight("a.py", 3), AnnotationWeight::Claimed);
        f.mark_clean("a.py");
        f.scan_ignores("a.py", "x = 1\ny = 2\nz = f()  # type: ignore[attr]\n");
        assert_eq!(f.weight("a.py", 2), AnnotationWeight::Exact);
        assert_eq!(f.weight("a.py", 3), AnnotationWeight::Claimed);
        assert_eq!(f.weight("b.py", 2), AnnotationWeight::Claimed);
    }

    // frob:tests crates/gob-symbols/src/types.rs::TypeFacts.weight
    #[test]
    fn annotated_claims_and_none_hints() {
        let mut f = TypeFacts::new(TypesTrust::Annotated);
        f.mark_clean("a.py");
        assert_eq!(f.weight("a.py", 1), AnnotationWeight::Claimed);
        f.trust = TypesTrust::None;
        assert_eq!(f.weight("a.py", 1), AnnotationWeight::Hint);
    }

    // frob:tests crates/gob-symbols/src/types.rs::TypesTrust.parse
    #[test]
    fn trust_spellings_parse() {
        assert_eq!(TypesTrust::parse("checked"), Some(TypesTrust::Checked));
        assert_eq!(TypesTrust::parse("annotated"), Some(TypesTrust::Annotated));
        assert_eq!(TypesTrust::parse("none"), Some(TypesTrust::None));
        assert_eq!(TypesTrust::parse("x"), None);
    }
}
