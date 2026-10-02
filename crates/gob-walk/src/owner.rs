//! The owner function over selectors: specificity order and the possible-worlds reading
//! (grmb-spec 6.5, binding.md 2.2). Ranks 1 (directive binds) and 3 (pack inference) belong to
//! grimble-bind; this module resolves rank 2 only.

use std::collections::BTreeSet;
use std::fmt;

use crate::selector::{Leaves, Row, Selector, Tri};
use crate::specificity::Specificity;

/// The name of an entity that can own code (a node of the model).
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub struct EntityName(String);

impl EntityName {
    /// The name as text.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for EntityName {
    fn from(s: &str) -> Self {
        Self(s.to_owned())
    }
}

impl From<String> for EntityName {
    fn from(s: String) -> Self {
        Self(s)
    }
}

impl fmt::Display for EntityName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// How certain a candidate row is.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum MatchStatus {
    /// Rests only on Must facts.
    Must,
    /// Goes through a May or Unknown fact.
    May,
}

impl MatchStatus {
    /// Maps a non-`No` truth to a status (`Unknown` degrades to May, never dropped).
    pub fn from_tri(t: Tri) -> Option<Self> {
        match t {
            Tri::Yes => Some(Self::Must),
            Tri::Unknown => Some(Self::May),
            Tri::No => None,
        }
    }
}

/// One `owns` row: an entity whose selector matches the item at a specificity.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Candidate {
    /// The owning entity.
    pub entity: EntityName,
    /// The specificity of the matching branch.
    pub spec: Specificity,
    /// The certainty of the match.
    pub status: MatchStatus,
}

/// The answer of the owner function.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Owner {
    /// Exactly this entity owns the item.
    Must(EntityName),
    /// The owner is one of these (or, see [`Ownership`], possibly nobody).
    May(BTreeSet<EntityName>),
    /// No owner can be named: a tie at the top specificity (the tied entities are listed, and
    /// SYS002 fires when two are Must) or an item whose file hides units (empty set).
    Unknown(BTreeSet<EntityName>),
    /// No selector claims the item and nothing is hidden.
    Foreign,
}

/// The owner with its provenance.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Ownership {
    /// The answer.
    pub owner: Owner,
    /// Every candidate row considered, sorted by entity then specificity.
    pub candidates: Vec<Candidate>,
    /// For [`Owner::May`]: no Must candidate exists, so the item may be foreign.
    pub maybe_foreign: bool,
    /// The item's file has an unseen remainder, so a hidden unit might claim it.
    pub hidden: bool,
}

/// The candidate rows of `entities` for one item, from its leaves and a status ceiling.
///
/// `ceiling` caps every row's status (a May containment chain makes every row May).
pub fn candidates<L: Leaves + ?Sized>(
    entities: &[(EntityName, Selector)],
    leaves: &L,
    ceiling: MatchStatus,
) -> Vec<Candidate> {
    let mut out = Vec::new();
    for (entity, sel) in entities {
        for Row { spec, truth } in sel.rows(leaves) {
            if let Some(status) = MatchStatus::from_tri(truth) {
                out.push(Candidate {
                    entity: entity.clone(),
                    spec,
                    status: status.max(ceiling),
                });
            }
        }
    }
    out
}

/// Resolves rank-2 candidates into an owner by the possible-worlds reading.
///
/// `unseen` says the item's file has hidden units. See grmb-spec 6.5 and binding.md 2.2.
pub fn resolve_owner(mut cands: Vec<Candidate>, unseen: bool) -> Ownership {
    cands.sort_by(|a, b| (&a.entity, a.spec, a.status).cmp(&(&b.entity, b.spec, b.status)));
    cands.dedup();
    let owner = pick(&cands, unseen);
    tracing::debug!(candidates = cands.len(), ?owner, unseen, "owner resolved");
    let must_any = cands.iter().any(|c| c.status == MatchStatus::Must);
    Ownership {
        maybe_foreign: matches!(owner, Owner::May(_)) && !must_any,
        hidden: unseen,
        candidates: cands,
        owner,
    }
}

fn pick(cands: &[Candidate], unseen: bool) -> Owner {
    if cands.is_empty() {
        return if unseen {
            Owner::Unknown(BTreeSet::new())
        } else {
            Owner::Foreign
        };
    }
    let must_max = cands
        .iter()
        .filter(|c| c.status == MatchStatus::Must)
        .map(|c| c.spec)
        .max();
    let Some(m) = must_max else {
        return Owner::May(cands.iter().map(|c| c.entity.clone()).collect());
    };
    let must_at_m: BTreeSet<&EntityName> = cands
        .iter()
        .filter(|c| c.status == MatchStatus::Must && c.spec == m)
        .map(|c| &c.entity)
        .collect();
    let higher = cands.iter().any(|c| c.spec > m);
    if must_at_m.len() >= 2 && !higher {
        return Owner::Unknown(
            cands
                .iter()
                .filter(|c| c.spec == m)
                .map(|c| c.entity.clone())
                .collect(),
        );
    }
    if let [x] = must_at_m.iter().copied().collect::<Vec<_>>().as_slice()
        && cands.iter().filter(|c| &c.entity != *x).all(|c| c.spec < m)
    {
        return Owner::Must((*x).clone());
    }
    let live = |c: &&Candidate| {
        !cands
            .iter()
            .any(|d| d.status == MatchStatus::Must && d.entity != c.entity && d.spec > c.spec)
    };
    Owner::May(
        cands
            .iter()
            .filter(live)
            .map(|c| c.entity.clone())
            .collect(),
    )
}

/// The owner of the item whose leaves are `leaves` under `entities`' selectors.
pub fn owner<L: Leaves + ?Sized>(
    entities: &[(EntityName, Selector)],
    leaves: &L,
    ceiling: MatchStatus,
    unseen: bool,
) -> Ownership {
    resolve_owner(candidates(entities, leaves, ceiling), unseen)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cand(e: &str, spec: [i32; 6], status: MatchStatus) -> Candidate {
        Candidate {
            entity: e.into(),
            spec: Specificity::new(spec),
            status,
        }
    }

    fn set(names: &[&str]) -> BTreeSet<EntityName> {
        names.iter().map(|n| (*n).into()).collect()
    }

    const BROAD: [i32; 6] = [1, 1, -1, 0, 0, 0];
    const NARROW: [i32; 6] = [1, 2, 0, -1, 0, 0];

    #[test]
    fn most_specific_must_wins() {
        let o = resolve_owner(
            vec![
                cand("broad", BROAD, MatchStatus::Must),
                cand("narrow", NARROW, MatchStatus::Must),
            ],
            false,
        );
        assert_eq!(o.owner, Owner::Must("narrow".into()));
    }

    #[test]
    fn tie_of_must_candidates_is_unknown_with_both_recorded() {
        let o = resolve_owner(
            vec![
                cand("a", BROAD, MatchStatus::Must),
                cand("b", BROAD, MatchStatus::Must),
                cand("c", [1, 0, -1, 0, 0, 0], MatchStatus::Must),
            ],
            false,
        );
        assert_eq!(o.owner, Owner::Unknown(set(&["a", "b"])));
        assert_eq!(o.candidates.len(), 3);
    }

    #[test]
    fn tie_with_a_higher_may_is_not_a_tie() {
        let o = resolve_owner(
            vec![
                cand("a", BROAD, MatchStatus::Must),
                cand("b", BROAD, MatchStatus::Must),
                cand("c", NARROW, MatchStatus::May),
            ],
            false,
        );
        assert_eq!(o.owner, Owner::May(set(&["a", "b", "c"])));
    }

    #[test]
    fn may_more_specific_over_must_broader_gives_bounds() {
        let o = resolve_owner(
            vec![
                cand("broad", BROAD, MatchStatus::Must),
                cand("loaders", NARROW, MatchStatus::May),
            ],
            false,
        );
        assert_eq!(o.owner, Owner::May(set(&["broad", "loaders"])));
        assert!(!o.maybe_foreign);
    }

    #[test]
    fn must_dominates_less_specific_may() {
        let o = resolve_owner(
            vec![
                cand("narrow", NARROW, MatchStatus::Must),
                cand("broad", BROAD, MatchStatus::May),
            ],
            false,
        );
        assert_eq!(o.owner, Owner::Must("narrow".into()));
    }

    #[test]
    fn may_only_candidates_may_be_foreign() {
        let o = resolve_owner(vec![cand("a", BROAD, MatchStatus::May)], false);
        assert_eq!(o.owner, Owner::May(set(&["a"])));
        assert!(o.maybe_foreign);
    }

    #[test]
    fn same_entity_rows_never_tie_with_themselves() {
        let o = resolve_owner(
            vec![
                cand("a", BROAD, MatchStatus::Must),
                cand("a", NARROW, MatchStatus::May),
            ],
            true,
        );
        assert_eq!(o.owner, Owner::Must("a".into()));
        assert!(o.hidden);
    }

    #[test]
    fn nobody_is_foreign_unless_something_is_hidden() {
        assert_eq!(resolve_owner(vec![], false).owner, Owner::Foreign);
        assert_eq!(
            resolve_owner(vec![], true).owner,
            Owner::Unknown(BTreeSet::new())
        );
    }
}
