//! File-level selection and owner(path) over the walk (grmb-spec 6.4 step 1, 6.5).

use crate::owner::{EntityName, MatchStatus, Ownership, owner};
use crate::selector::{AttrPred, Glob, Leaves, Selector, Tri};
use crate::{LanguageHint, WalkResult};

/// A file selected by a selector and how certain the match is.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct PathMatch {
    /// Repository-relative path.
    pub path: String,
    /// Must when the match rests on PATH and file-level predicates alone, May otherwise.
    pub status: MatchStatus,
}

/// Leaves at file granularity: PATH and `lang` are decided, unit predicates are Unknown.
struct FileLeaves<'a> {
    path: &'a str,
    lang: &'a LanguageHint,
    /// `true` evaluates `::` globs against the file's module unit (empty qualname), `false`
    /// leaves them Unknown (some unit of the file may match).
    module_unit: bool,
}

impl Leaves for FileLeaves<'_> {
    fn glob(&self, glob: &Glob) -> Tri {
        if !glob.matches_path(self.path) {
            Tri::No
        } else if glob.qual().is_none() {
            Tri::Yes
        } else if self.module_unit {
            Tri::from_bool(glob.matches_qual::<&str>(&[]))
        } else {
            Tri::Unknown
        }
    }

    fn lang(&self, lang: &str) -> Tri {
        Tri::from_bool(self.lang.tag() == lang)
    }

    fn kind(&self, _kinds: &[String]) -> Tri {
        Tri::Unknown
    }

    fn attr(&self, _pred: &AttrPred) -> Tri {
        Tri::Unknown
    }
}

/// The files of `walk` selected by `sel`, in path order; Unknown membership yields May.
pub fn select_files(sel: &Selector, walk: &WalkResult) -> Vec<PathMatch> {
    let out: Vec<PathMatch> = walk
        .files
        .iter()
        .filter_map(|f| {
            let leaves = FileLeaves {
                path: &f.path,
                lang: &f.language,
                module_unit: false,
            };
            MatchStatus::from_tri(sel.truth(&leaves)).map(|status| PathMatch {
                path: f.path.clone(),
                status,
            })
        })
        .collect();
    tracing::debug!(selector = %sel, files = out.len(), "file selection");
    out
}

/// Oversized files the selector may match: their units are hidden, never silently absent.
pub fn unseen_files(sel: &Selector, walk: &WalkResult) -> Vec<String> {
    walk.oversized
        .iter()
        .filter(|o| {
            let lang = LanguageHint::from_path(&o.path);
            let leaves = FileLeaves {
                path: &o.path,
                lang: &lang,
                module_unit: false,
            };
            sel.truth(&leaves) != Tri::No
        })
        .map(|o| o.path.clone())
        .collect()
}

/// The owner of the file at `path`, that is of its module unit (grmb-spec 6.5 last line).
///
/// `unseen` is true when the file hides units it may define (see [`unseen_files`]).
pub fn owner_of_path(path: &str, entities: &[(EntityName, Selector)], unseen: bool) -> Ownership {
    let lang = LanguageHint::from_path(path);
    let leaves = FileLeaves {
        path,
        lang: &lang,
        module_unit: true,
    };
    owner(entities, &leaves, MatchStatus::Must, unseen)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::owner::Owner;
    use crate::{Digest, FileEntry, Oversized};

    fn file(path: &str) -> FileEntry {
        FileEntry {
            path: path.to_owned(),
            size: 1,
            digest: Digest::of(path.as_bytes()),
            language: LanguageHint::from_path(path),
        }
    }

    fn walk() -> WalkResult {
        WalkResult {
            files: vec![
                file("README.md"),
                file("crates/a/src/lib.rs"),
                file("crates/a/src/x/mod.rs"),
                file("crates/a/tests/t.rs"),
                file("docs/a.md"),
            ],
            oversized: vec![Oversized {
                path: "crates/a/src/big.rs".into(),
                size: 99,
            }],
        }
    }

    fn sel(t: &str) -> Selector {
        Selector::parse(t).unwrap()
    }

    fn got(t: &str) -> Vec<(String, MatchStatus)> {
        select_files(&sel(t), &walk())
            .into_iter()
            .map(|m| (m.path, m.status))
            .collect()
    }

    #[test]
    fn glob_and_lang_select_files_with_must() {
        let m = got(r#""crates/*/src/**" & lang(rust)"#);
        assert_eq!(
            m,
            [
                ("crates/a/src/lib.rs".to_owned(), MatchStatus::Must),
                ("crates/a/src/x/mod.rs".to_owned(), MatchStatus::Must),
            ]
        );
    }

    #[test]
    fn unit_predicates_and_symbol_globs_degrade_to_may() {
        let m = got(r#""crates/a/src/lib.rs::run""#);
        assert_eq!(m, [("crates/a/src/lib.rs".to_owned(), MatchStatus::May)]);
        let m = got(r#""crates/a/**" & kind(function)"#);
        assert_eq!(m.len(), 3);
        assert!(m.iter().all(|(_, s)| *s == MatchStatus::May));
    }

    #[test]
    fn negation_is_the_complement_within_the_walk() {
        let m = got(r#"!lang(rust) & !"docs/**""#);
        assert_eq!(m, [("README.md".to_owned(), MatchStatus::Must)]);
    }

    #[test]
    fn oversized_matches_are_reported_as_unseen() {
        assert_eq!(
            unseen_files(&sel(r#""crates/a/src/**""#), &walk()),
            ["crates/a/src/big.rs"]
        );
        assert!(unseen_files(&sel(r#""docs/**""#), &walk()).is_empty());
    }

    fn entities(list: &[(&str, &str)]) -> Vec<(EntityName, Selector)> {
        list.iter().map(|(n, s)| ((*n).into(), sel(s))).collect()
    }

    #[test]
    fn owner_of_path_uses_the_review_m12_order() {
        let es = entities(&[("broad", r#""src/**""#), ("narrow", r#""src/*/mod.rs""#)]);
        assert_eq!(
            owner_of_path("src/x/mod.rs", &es, false).owner,
            Owner::Must("narrow".into())
        );
        assert_eq!(
            owner_of_path("src/y.rs", &es, false).owner,
            Owner::Must("broad".into())
        );
        assert_eq!(owner_of_path("other.rs", &es, false).owner, Owner::Foreign);
    }

    #[test]
    fn owner_ties_on_a_path_are_unknown_with_both_recorded() {
        let es = entities(&[("a", r#""src/**""#), ("b", r#""src/**""#)]);
        let o = owner_of_path("src/x.rs", &es, false);
        match o.owner {
            Owner::Unknown(tied) => {
                assert_eq!(tied.len(), 2);
            }
            other => panic!("expected tie, got {other:?}"),
        }
    }

    #[test]
    fn predicate_narrowing_wins_a_directory_tie() {
        let es = entities(&[("rs", r#""src/**" & lang(rust)"#), ("all", r#""src/**""#)]);
        assert_eq!(
            owner_of_path("src/a.rs", &es, false).owner,
            Owner::Must("rs".into())
        );
        assert_eq!(
            owner_of_path("src/a.md", &es, false).owner,
            Owner::Must("all".into())
        );
    }

    #[test]
    fn symbol_globs_do_not_claim_the_module_unit_unless_they_match_it() {
        let es = entities(&[("sym", r#""src/a.rs::run""#), ("dir", r#""src/**""#)]);
        assert_eq!(
            owner_of_path("src/a.rs", &es, false).owner,
            Owner::Must("dir".into())
        );
    }
}
