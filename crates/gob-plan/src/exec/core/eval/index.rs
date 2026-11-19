//! Equality-join indexes for quantifier bodies (frob:ticket 01M5C7AA29V08HTNZM0BA2A6ST).
//!
//! `some x: K where x.a == e and ...` scans every member of `K`. When a conjunct is an
//! equality between an operand that reads only the bound variable and one that does not, the
//! members are bucketed once by the former's value, and a probe visits only the bucket the
//! latter selects plus the members whose key is not a known scalar. A skipped member would have
//! decided that conjunct `No`, which under `and` is a `No` disjunct: the identity of `or`.

use std::rc::Rc;

use super::super::fxmap::FastMap;
use super::{Domain, Env, Eval, Val};
use crate::exec::core::field::{Datum, Scalar};
use crate::plan::{CmpOp, Op, OpId, Operand, VarId};

/// Domains this small are scanned, not indexed.
const SCAN_ALL: usize = 4;

/// The domain positions of one kind bucketed by one equality key.
pub(super) struct EqIndex {
    /// Which side of the comparison reads the bound variable: the key side.
    probe: Operand,
    /// The position list of each known key, by index into `lists`.
    buckets: FastMap<Scalar, u32>,
    /// The ascending position lists the buckets point at.
    lists: Vec<Vec<u32>>,
    /// Positions whose key is not a known scalar, ascending; always visited.
    wild: Vec<u32>,
}

/// An equality conjunct: (op, key side, probe side, whether the probe is the right-hand side).
pub(super) type Conjunct = (OpId, Operand, Operand, bool);

/// The variables an operand reads (at most two).
fn reads(o: Operand) -> [Option<VarId>; 2] {
    let leaf = |l: crate::plan::Leaf| match l.operand() {
        Operand::Var(v) | Operand::Field(v, _) => Some(v),
        _ => None,
    };
    match o {
        Operand::Var(v) | Operand::Field(v, _) => [Some(v), None],
        Operand::Slug(a) => [leaf(a), None],
        Operand::Resolve(a, b) => [leaf(a), leaf(b)],
        Operand::Int(_) | Operand::Str(_) | Operand::Bool(_) | Operand::KnobInt { .. } => {
            [None, None]
        }
    }
}

/// Whether `o` reads `var` and nothing else.
fn only(o: Operand, var: VarId) -> bool {
    let r = reads(o);
    !matches!(o, Operand::Var(_)) && r.contains(&Some(var)) && r.iter().flatten().all(|&v| v == var)
}

impl Eval<'_> {
    /// The key operands of the equality conjuncts of `cond` over `var`: (conjunct, key side,
    /// probe side).
    fn eq_conjuncts(&self, cond: OpId, var: VarId) -> Rc<Vec<Conjunct>> {
        if let Some(c) = self.conjuncts.borrow().get(&cond) {
            return Rc::clone(c);
        }
        let found = Rc::new(self.find_eq_conjuncts(cond, var));
        self.conjuncts.borrow_mut().insert(cond, Rc::clone(&found));
        found
    }

    fn find_eq_conjuncts(&self, cond: OpId, var: VarId) -> Vec<Conjunct> {
        let single = [cond];
        let cs: &[OpId] = match &self.plan.ops[cond as usize] {
            Op::And(cs) => cs,
            _ => &single,
        };
        let mut found: Vec<Conjunct> = cs
            .iter()
            .filter_map(|&c| {
                let Op::Cmp {
                    lhs,
                    op: CmpOp::Eq,
                    rhs,
                } = self.plan.ops[c as usize]
                else {
                    return None;
                };
                let reads_var = |o: Operand| reads(o).contains(&Some(var));
                if only(lhs, var) && !reads_var(rhs) {
                    Some((c, lhs, rhs, true))
                } else if only(rhs, var) && !reads_var(lhs) {
                    Some((c, rhs, lhs, false))
                } else {
                    None
                }
            })
            .collect();
        // Cheap probes first: a probe that selects nothing then spares the dearer ones.
        found.sort_by_key(|&(_, _, probe, _)| {
            matches!(probe, Operand::Resolve(..) | Operand::Slug(_))
        });
        found
    }

    /// The index of conjunct `c` over `domain`, built on first use.
    fn eq_index(
        &self,
        c: OpId,
        key: Operand,
        probe: Operand,
        var: VarId,
        domain: &Domain,
        env: &mut Env,
    ) -> Rc<EqIndex> {
        if let Some(i) = self.indexes.borrow().get(&c) {
            return Rc::clone(i);
        }
        let mut buckets: FastMap<Scalar, u32> = FastMap::default();
        let mut lists: Vec<Vec<u32>> = Vec::new();
        let mut wild = Vec::new();
        for (pos, &(n, _)) in domain.iter().enumerate() {
            let pos = u32::try_from(pos).expect("domains are far below u32::MAX members");
            env[usize::from(var)] = Some(Val::Node(n));
            match self.datum(&key, env) {
                Datum::Known(s) => {
                    let at = *buckets.entry(s).or_insert_with(|| {
                        lists.push(Vec::new());
                        u32::try_from(lists.len() - 1).expect("lists are far below u32::MAX")
                    });
                    lists[at as usize].push(pos);
                }
                _ => wild.push(pos),
            }
        }
        env[usize::from(var)] = None;
        tracing::debug!(
            op = c,
            keys = buckets.len(),
            wild = wild.len(),
            "equality index built"
        );
        let idx = Rc::new(EqIndex {
            probe,
            buckets,
            lists,
            wild,
        });
        self.indexes.borrow_mut().insert(c, Rc::clone(&idx));
        idx
    }

    /// The domain positions `some var: kind where cond` must visit under `env`, or `None` for
    /// all of them (no usable equality conjunct, or a probe that is not a known scalar).
    pub(super) fn candidates(
        &self,
        var: VarId,
        cond: OpId,
        domain: &Domain,
        env: &mut Env,
    ) -> Option<Visit> {
        // A handful of members is cheaper to scan than to probe; a skipped member would decide
        // No anyway, so the verdict is the same.
        if domain.len() <= SCAN_ALL {
            return None;
        }
        // The smallest candidate set so far: its index, the bucket and its size.
        let mut best: Option<(Rc<EqIndex>, Option<u32>, usize)> = None;
        for &(c, key, probe, probe_rhs) in self.eq_conjuncts(cond, var).iter() {
            let idx = self.eq_index(c, key, probe, var, domain, env);
            self.mark_probe(c, probe_rhs);
            // Read through the operand cache: the body evaluates this same side next.
            let side = self.side(c, probe_rhs, &idx.probe, env);
            let Datum::Known(k) = &*side else {
                continue;
            };
            let list = idx.buckets.get(k).copied();
            let hits = list.map_or(0, |l| idx.lists[l as usize].len());
            let n = hits + idx.wild.len();
            if best.as_ref().is_none_or(|(_, _, m)| n < *m) {
                best = Some((Rc::clone(&idx), list, n));
            }
            if n == 0 {
                break;
            }
        }
        best.map(|(idx, list, _)| {
            let hits = list.map_or(&[][..], |l| idx.lists[l as usize].as_slice());
            let merged = (!idx.wild.is_empty()).then(|| merge(hits, &idx.wild));
            Visit { idx, list, merged }
        })
    }
}

/// The domain positions a probe selected, ascending.
pub(super) struct Visit {
    idx: Rc<EqIndex>,
    list: Option<u32>,
    /// The bucket and the wild positions merged, when there are wild ones.
    merged: Option<Vec<u32>>,
}

impl Visit {
    /// The positions to visit.
    pub(super) fn positions(&self) -> &[u32] {
        match (&self.merged, self.list) {
            (Some(m), _) => m,
            (None, Some(l)) => &self.idx.lists[l as usize],
            (None, None) => &[],
        }
    }
}

/// The ascending union of two disjoint ascending position lists.
fn merge(a: &[u32], b: &[u32]) -> Vec<u32> {
    let mut out = Vec::with_capacity(a.len() + b.len());
    let (mut i, mut j) = (0, 0);
    while i < a.len() && j < b.len() {
        if a[i] < b[j] {
            out.push(a[i]);
            i += 1;
        } else {
            out.push(b[j]);
            j += 1;
        }
    }
    out.extend_from_slice(&a[i..]);
    out.extend_from_slice(&b[j..]);
    out
}
