//! Ownership per identity: the owner function of binding.md 2.6 over ranks 1, 2 and 4
//! (rank 3 is the inference stub and contributes nothing yet).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::owner_of_unit;
use gob_walk::selector::{AttrPred, Glob, Leaves, Tri};
use gob_walk::{
    Candidate, EntityName, MatchStatus, Owner, Ownership, Selector, Specificity, owner_of_path,
};

use crate::code::{Code, CodeFile};
use crate::relation::Relation;

/// A tie of tied nodes on one identity (SYS002).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Tie {
    /// The tied nodes with the shared top specificity.
    pub nodes: Vec<(EntityName, Specificity)>,
    /// True when two Must rows tie (fires); false when a May row is in the tie (Unresolved).
    pub fires: bool,
}

/// The merged owner answer of one identity.
#[derive(Clone, Debug)]
pub struct Merged {
    /// The answer.
    pub owner: Owner,
    /// Every rank 2 candidate row considered.
    pub candidates: Vec<Candidate>,
    /// No Must candidate exists, so the identity may be foreign.
    pub maybe_foreign: bool,
    /// The artifact hides units a selector may claim.
    pub hidden: bool,
    /// Two directives name different nodes (SYS003 `directive-directive`).
    pub directive_directive: Option<BTreeSet<EntityName>>,
    /// A directive's node is not in the top Must set of the selectors (SYS003 `directive-selector`).
    pub directive_selector: Option<(EntityName, Vec<(EntityName, Specificity)>)>,
    /// A tie among selectors that no directive resolved (SYS002).
    pub tie: Option<Tie>,
}

/// The owner of one unit and where it lives.
#[derive(Clone, Debug)]
pub struct UnitOwner {
    /// The file of the unit.
    pub file: String,
    /// The unit kind.
    pub kind: String,
    /// The merged answer.
    pub merged: Merged,
}

/// Per-file facts about ownership.
#[derive(Clone, Debug, Default)]
pub struct FileOwn {
    /// How many `owns` selectors may match some unit of the file.
    pub claimants: usize,
    /// True when every unit's owner was computed (otherwise every unit is foreign).
    pub expanded: bool,
    /// The identities computed, in document order.
    pub units: Vec<String>,
}

/// Ownership for the whole snapshot.
#[derive(Debug, Default)]
pub struct Owners {
    /// Owner of every computed identity by symref text.
    pub units: BTreeMap<String, UnitOwner>,
    /// Per-file facts by path.
    pub files: BTreeMap<String, FileOwn>,
}

struct PathLeaves<'a> {
    path: &'a str,
    file: &'a CodeFile,
}

impl Leaves for PathLeaves<'_> {
    fn glob(&self, glob: &Glob) -> Tri {
        if !glob.matches_path(self.path) {
            Tri::No
        } else if glob.qual().is_some() {
            Tri::Unknown
        } else {
            Tri::Yes
        }
    }

    fn lang(&self, lang: &str) -> Tri {
        Tri::from_bool(self.file.hint.tag() == lang)
    }

    fn kind(&self, _kinds: &[String]) -> Tri {
        Tri::Unknown
    }

    fn attr(&self, _pred: &AttrPred) -> Tri {
        Tri::Unknown
    }
}

fn claimants(all: &[(EntityName, Selector)], file: &CodeFile) -> Vec<(EntityName, Selector)> {
    let leaves = PathLeaves {
        path: &file.path,
        file,
    };
    all.iter()
        .filter(|(_, sel)| sel.truth(&leaves) != Tri::No)
        .cloned()
        .collect()
}

fn top_must(cands: &[Candidate]) -> Vec<(EntityName, Specificity)> {
    let Some(max) = cands
        .iter()
        .filter(|c| c.status == MatchStatus::Must)
        .map(|c| c.spec)
        .max()
    else {
        return Vec::new();
    };
    let mut out: Vec<(EntityName, Specificity)> = cands
        .iter()
        .filter(|c| c.status == MatchStatus::Must && c.spec == max)
        .map(|c| (c.entity.clone(), c.spec))
        .collect();
    out.dedup();
    out
}

/// Merge the rank 2 `ownership` with the rank 1 nodes named for the identity (binding.md 2.5).
pub fn merge(ownership: &Ownership, rank1: &BTreeSet<EntityName>) -> Merged {
    let mut m = Merged {
        owner: ownership.owner.clone(),
        candidates: ownership.candidates.clone(),
        maybe_foreign: ownership.maybe_foreign,
        hidden: ownership.hidden,
        directive_directive: None,
        directive_selector: None,
        tie: None,
    };
    match rank1.len() {
        0 => {
            let top = ownership.candidates.iter().map(|c| c.spec).max();
            m.tie = match (&ownership.owner, top) {
                (Owner::Unknown(set), _) if !set.is_empty() => Some(Tie {
                    nodes: ownership
                        .candidates
                        .iter()
                        .filter(|c| set.contains(&c.entity) && Some(c.spec) == top)
                        .map(|c| (c.entity.clone(), c.spec))
                        .collect(),
                    fires: true,
                }),
                (Owner::May(_), Some(top)) => {
                    let at_top: Vec<&Candidate> = ownership
                        .candidates
                        .iter()
                        .filter(|c| c.spec == top)
                        .collect();
                    let nodes: BTreeSet<&EntityName> = at_top.iter().map(|c| &c.entity).collect();
                    let some_may = at_top.iter().any(|c| c.status == MatchStatus::May);
                    (nodes.len() >= 2 && some_may).then(|| Tie {
                        nodes: at_top.iter().map(|c| (c.entity.clone(), c.spec)).collect(),
                        fires: false,
                    })
                }
                _ => None,
            };
        }
        1 => {
            let x = rank1
                .iter()
                .next()
                .cloned()
                .unwrap_or_else(|| unreachable!("len is 1"));
            let top = top_must(&ownership.candidates);
            if !top.is_empty() && !top.iter().any(|(n, _)| *n == x) {
                m.directive_selector = Some((x.clone(), top));
            }
            m.owner = Owner::Must(x);
            m.maybe_foreign = false;
        }
        _ => {
            m.directive_directive = Some(rank1.clone());
            m.owner = Owner::Unknown(rank1.clone());
            m.maybe_foreign = false;
        }
    }
    m
}

/// Compute ownership for every file of `code`.
///
/// A file's units are all computed when some `owns` selector may match it or when `expand`
/// names it (directive targets, modeled files, flow-end files); otherwise every unit is foreign
/// and none is computed.
pub fn build(
    all: &[(EntityName, Selector)],
    code: &Code,
    rel: &Relation,
    expand: &BTreeSet<String>,
) -> Owners {
    let mut out = Owners::default();
    code.prefold(
        code.files
            .iter()
            .filter(|f| {
                !f.unreadable && (expand.contains(&f.path) || !claimants(all, f).is_empty())
            })
            .map(|f| f.path.as_str()),
    );
    for file in &code.files {
        let claim = claimants(all, file);
        let mut fo = FileOwn {
            claimants: claim.len(),
            ..FileOwn::default()
        };
        if file.unreadable {
            let o = owner_of_path(&file.path, &claim, true);
            let rank1 = rank1_of(rel, &file.path);
            out.units.insert(
                file.path.clone(),
                UnitOwner {
                    file: file.path.clone(),
                    kind: "file".to_owned(),
                    merged: merge(&o, &rank1),
                },
            );
            fo.expanded = true;
            fo.units.push(file.path.clone());
        } else if !claim.is_empty() || expand.contains(&file.path) {
            fo.expanded = true;
            if let Some(f) = file.folded() {
                for u in f.term.units() {
                    let text = u.symref.to_string();
                    if out.units.contains_key(&text) {
                        continue;
                    }
                    let Some(mut o) = owner_of_unit(&claim, &u.symref, &f.term, &f.scopes) else {
                        continue;
                    };
                    if claim.is_empty() {
                        // No selector can reach this file, so hidden units cannot be claimed.
                        o.owner = Owner::Foreign;
                        o.hidden = false;
                        o.maybe_foreign = false;
                    }
                    let kind = crate::code::unit_kind(&f.term, u.node);
                    out.units.insert(
                        text.clone(),
                        UnitOwner {
                            file: file.path.clone(),
                            kind,
                            merged: merge(&o, &rank1_of(rel, &text)),
                        },
                    );
                    fo.units.push(text);
                }
            }
        }
        out.files.insert(file.path.clone(), fo);
    }
    tracing::info!(
        files = out.files.len(),
        units = out.units.len(),
        "ownership computed"
    );
    out
}

fn rank1_of(rel: &Relation, symref: &str) -> BTreeSet<EntityName> {
    rel.dir_owns
        .get(symref)
        .map(|v| {
            v.iter()
                .map(|d| EntityName::from(d.entity.clone()))
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use gob_walk::owner::resolve_owner;

    use super::*;

    fn cand(e: &str, spec: [i32; 6], status: MatchStatus) -> Candidate {
        Candidate {
            entity: e.into(),
            spec: Specificity::new(spec),
            status,
        }
    }

    const BROAD: [i32; 6] = [1, 1, -1, 0, 0, 0];
    const NARROW: [i32; 6] = [1, 2, 0, -1, 0, 0];

    fn none() -> BTreeSet<EntityName> {
        BTreeSet::new()
    }

    // frob:tests crates/grimble-bind/src/owner.rs::merge
    #[test]
    fn a_may_in_the_top_tie_is_an_unresolved_tie() {
        let o = resolve_owner(
            vec![
                cand("a", BROAD, MatchStatus::Must),
                cand("b", BROAD, MatchStatus::May),
            ],
            false,
        );
        let m = merge(&o, &none());
        assert!(matches!(m.owner, Owner::May(_)));
        assert!(m.tie.is_some_and(|t| !t.fires));
    }

    // frob:tests crates/grimble-bind/src/owner.rs::merge
    #[test]
    fn a_must_tie_fires_and_a_directive_naming_one_node_resolves_it() {
        let o = resolve_owner(
            vec![
                cand("a", BROAD, MatchStatus::Must),
                cand("b", BROAD, MatchStatus::Must),
            ],
            false,
        );
        assert!(merge(&o, &none()).tie.is_some_and(|t| t.fires));
        let m = merge(&o, &BTreeSet::from(["a".into()]));
        assert_eq!(m.owner, Owner::Must("a".into()));
        assert!(m.tie.is_none() && m.directive_selector.is_none());
    }

    // frob:tests crates/grimble-bind/src/owner.rs::merge
    #[test]
    fn possible_worlds_keeps_a_may_narrower_candidate_in_hi() {
        let o = resolve_owner(
            vec![
                cand("etl", BROAD, MatchStatus::Must),
                cand("loaders", NARROW, MatchStatus::May),
            ],
            false,
        );
        let m = merge(&o, &none());
        assert!(matches!(m.owner, Owner::May(ref s) if s.len() == 2));
        assert!(m.tie.is_none());
    }

    // frob:tests crates/grimble-bind/src/owner.rs::merge
    #[test]
    fn a_directive_against_a_may_selector_is_no_conflict() {
        let o = resolve_owner(vec![cand("a", BROAD, MatchStatus::May)], false);
        let m = merge(&o, &BTreeSet::from(["b".into()]));
        assert_eq!(m.owner, Owner::Must("b".into()));
        assert!(m.directive_selector.is_none() && m.directive_directive.is_none());
    }
}
