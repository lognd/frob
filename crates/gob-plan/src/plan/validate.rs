//! Full semantic validation of a plan: nothing the executor relies on is assumed.
//!
//! Passes: limits and names, reference ranges and ordering (which rules out
//! cycles), then one bounded-depth walk checking tree shape, binding scopes,
//! declared needs, prefilter coverage and cost class.

// Op and variable counts are bounded by MAX_OPS and MAX_VARS before any index is cast.
#![allow(clippy::cast_possible_truncation)]

use std::str::FromStr;

use gob_rules::RuleId;

use super::error::PlanError;
use super::ir::{CostClass, Langs, Limit, Op, OpId, Operand, PlanParts, Provenance, StrId, VarId};
use super::limits::{
    MAX_DEFS, MAX_DEPTH, MAX_LIST, MAX_OPS, MAX_PACK_NAME, MAX_PARAMS, MAX_STR_LEN, MAX_STRINGS,
    MAX_VARS, MAX_WITHIN,
};

/// Checks every invariant of `p`; `Ok` means the executor may run it.
pub fn validate(p: &PlanParts) -> Result<(), PlanError> {
    limits_and_names(p)?;
    references(p)?;
    Walk::new(p).run()
}

fn too_large(what: &'static str, found: usize, limit: usize) -> PlanError {
    PlanError::TooLarge {
        what,
        found: found as u64,
        limit: limit as u64,
    }
}

fn check_len(what: &'static str, found: usize, limit: usize) -> Result<(), PlanError> {
    if found > limit {
        Err(too_large(what, found, limit))
    } else {
        Ok(())
    }
}

fn limits_and_names(p: &PlanParts) -> Result<(), PlanError> {
    check_len("ops", p.ops.len(), MAX_OPS)?;
    check_len("strings", p.strings.len(), MAX_STRINGS)?;
    check_len("variables", usize::from(p.vars), MAX_VARS)?;
    check_len("defs", p.defs.len(), MAX_DEFS)?;
    check_len("clauses", p.clauses.len(), MAX_LIST)?;
    check_len("reports", p.reports.len(), MAX_LIST)?;
    check_len("prefilter", p.prefilter.len(), MAX_LIST)?;
    for s in &p.strings {
        check_len("string length", s.len(), MAX_STR_LEN)?;
    }
    if RuleId::from_str(&p.rule).is_err() {
        return Err(PlanError::Invalid {
            what: "rule id",
            why: "not a rule id like TODO001",
        });
    }
    if let Provenance::Pack(name) = &p.provenance {
        let ok = !name.is_empty()
            && name.len() <= MAX_PACK_NAME
            && name
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-' || b == b'_');
        if !ok {
            return Err(PlanError::Invalid {
                what: "pack name",
                why: "must be 1-64 of a-z 0-9 - _",
            });
        }
    }
    if !p.needs.valid() {
        return Err(PlanError::Invalid {
            what: "needs",
            why: "unknown side relation bit",
        });
    }
    if p.reports.is_empty() {
        return Err(PlanError::Invalid {
            what: "reports",
            why: "a plan needs at least one report",
        });
    }
    Ok(())
}

fn strictly_ascending(v: &[StrId], strings: usize, what: &'static str) -> Result<(), PlanError> {
    for w in v.windows(2) {
        if w[0] >= w[1] {
            return Err(PlanError::NotCanonical { what });
        }
    }
    for &id in v {
        str_in_range(id, strings)?;
    }
    Ok(())
}

fn str_in_range(id: StrId, strings: usize) -> Result<(), PlanError> {
    if (id as usize) < strings {
        Ok(())
    } else {
        Err(PlanError::OutOfRange {
            what: "string",
            index: u64::from(id),
            len: strings as u64,
        })
    }
}

fn var_in_range(v: VarId, vars: u16) -> Result<(), PlanError> {
    if v < vars {
        Ok(())
    } else {
        Err(PlanError::OutOfRange {
            what: "variable",
            index: u64::from(v),
            len: u64::from(vars),
        })
    }
}

/// Children of an op, in order.
fn children(op: &Op) -> &[OpId] {
    match op {
        Op::And(c) | Op::Or(c) => c,
        Op::Not(c) | Op::Quant { cond: c, .. } | Op::CountCmp { cond: c, .. } => {
            std::slice::from_ref(c)
        }
        _ => &[],
    }
}

fn operand_refs(o: &Operand, p: &PlanParts) -> Result<(), PlanError> {
    match *o {
        Operand::Var(v) => var_in_range(v, p.vars),
        Operand::Field(v, f) => {
            var_in_range(v, p.vars).and_then(|()| str_in_range(f, p.strings.len()))
        }
        Operand::Str(s) => str_in_range(s, p.strings.len()),
        Operand::Int(_) | Operand::Bool(_) => Ok(()),
    }
}

/// Every index is in range; every child op comes strictly earlier than its parent.
#[allow(
    clippy::too_many_lines,
    reason = "one flat match or field list per wire item"
)]
fn references(p: &PlanParts) -> Result<(), PlanError> {
    let n = p.strings.len();
    strictly_ascending(&p.prefilter, n, "prefilter")?;
    if let Langs::Only(l) = &p.langs {
        check_len("languages", l.len(), MAX_LIST)?;
        strictly_ascending(l, n, "languages")?;
    }
    let ops = p.ops.len();
    let op_ref = |id: OpId| -> Result<(), PlanError> {
        if (id as usize) < ops {
            Ok(())
        } else {
            Err(PlanError::OutOfRange {
                what: "op",
                index: u64::from(id),
                len: ops as u64,
            })
        }
    };
    for (i, op) in p.ops.iter().enumerate() {
        let this = i as OpId;
        for &c in children(op) {
            op_ref(c)?;
            if c >= this {
                return Err(PlanError::Cyclic {
                    op: this,
                    target: c,
                });
            }
        }
        match op {
            Op::Find { var, kind }
            | Op::Quant { var, kind, .. }
            | Op::CountCmp { var, kind, .. } => {
                var_in_range(*var, p.vars)?;
                str_in_range(*kind, n)?;
            }
            Op::FindSide { var, table, .. } => {
                var_in_range(*var, p.vars)?;
                str_in_range(*table, n)?;
            }
            Op::Inside { sub: a, sup: b, .. } | Op::Order { a, b, .. } => {
                var_in_range(*a, p.vars)?;
                var_in_range(*b, p.vars)?;
            }
            Op::Verb {
                subject,
                object,
                verb,
                ..
            } => {
                var_in_range(*subject, p.vars)?;
                var_in_range(*object, p.vars)?;
                str_in_range(*verb, n)?;
            }
            Op::Reaches {
                from,
                to,
                via,
                within,
                ..
            } => {
                var_in_range(*from, p.vars)?;
                var_in_range(*to, p.vars)?;
                str_in_range(*via, n)?;
                if *within == 0 || *within > MAX_WITHIN {
                    return Err(PlanError::Invalid {
                        what: "within",
                        why: "must be 1..=1024",
                    });
                }
            }
            Op::Cmp { lhs, rhs, .. } => {
                operand_refs(lhs, p)?;
                operand_refs(rhs, p)?;
            }
            Op::Call { def, args } => {
                let d = p.defs.get(usize::from(*def)).ok_or(PlanError::OutOfRange {
                    what: "def",
                    index: u64::from(*def),
                    len: p.defs.len() as u64,
                })?;
                check_len("call arguments", args.len(), MAX_PARAMS)?;
                if args.len() != d.params.len() {
                    return Err(PlanError::Invalid {
                        what: "call",
                        why: "argument count differs from the def's parameters",
                    });
                }
                for &a in args {
                    var_in_range(a, p.vars)?;
                }
            }
            Op::MatchRegex { subject, pattern } | Op::MatchGlob { subject, pattern } => {
                operand_refs(subject, p)?;
                str_in_range(*pattern, n)?;
            }
            Op::And(_) | Op::Or(_) | Op::Not(_) => {}
        }
        if let Op::CountCmp {
            limit: Limit::Knob { name, .. },
            ..
        } = op
        {
            str_in_range(*name, n)?;
        }
    }
    for d in &p.defs {
        check_len("def parameters", d.params.len(), MAX_PARAMS)?;
        op_ref(d.body)?;
        for &v in &d.params {
            var_in_range(v, p.vars)?;
        }
    }
    for &c in &p.clauses {
        op_ref(c)?;
    }
    for r in &p.reports {
        if let Some(w) = r.when {
            op_ref(w)?;
        }
        var_in_range(r.subject, p.vars)?;
        str_in_range(r.message, n)?;
    }
    Ok(())
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum VarState {
    Unbound,
    Bound,
    Closed,
}

struct Walk<'a> {
    p: &'a PlanParts,
    seen: Vec<bool>,
    vars: Vec<VarState>,
    max_within: Option<u16>,
    /// The def whose body is being walked, if any (calls may only go to earlier defs).
    in_def: Option<usize>,
}

impl<'a> Walk<'a> {
    fn new(p: &'a PlanParts) -> Self {
        Walk {
            p,
            seen: vec![false; p.ops.len()],
            vars: vec![VarState::Unbound; usize::from(p.vars)],
            max_within: None,
            in_def: None,
        }
    }

    fn run(mut self) -> Result<(), PlanError> {
        let p = self.p;
        for (i, d) in p.defs.iter().enumerate() {
            for &v in &d.params {
                self.bind(v)?;
            }
            self.in_def = Some(i);
            self.visit(d.body, 0, false)?;
            for &v in &d.params {
                self.vars[usize::from(v)] = VarState::Closed;
            }
        }
        self.in_def = None;
        for &c in &p.clauses {
            self.visit(c, 0, true)?;
        }
        for r in &p.reports {
            if let Some(w) = r.when {
                self.visit(w, 0, false)?;
            }
            if self.state(r.subject) != VarState::Bound {
                return Err(PlanError::Unbound { var: r.subject });
            }
        }
        if let Some(i) = self.seen.iter().position(|s| !s) {
            return Err(PlanError::OrphanOp { op: i as OpId });
        }
        if let Some(i) = self.vars.iter().position(|s| *s == VarState::Unbound) {
            return Err(PlanError::UnusedVar { var: i as VarId });
        }
        self.cost()
    }

    fn state(&self, v: VarId) -> VarState {
        self.vars
            .get(usize::from(v))
            .copied()
            .unwrap_or(VarState::Unbound)
    }

    fn bind(&mut self, v: VarId) -> Result<(), PlanError> {
        match self.vars.get_mut(usize::from(v)) {
            Some(s @ VarState::Unbound) => {
                *s = VarState::Bound;
                Ok(())
            }
            Some(_) => Err(PlanError::Rebound { var: v }),
            None => Err(PlanError::OutOfRange {
                what: "variable",
                index: u64::from(v),
                len: u64::from(self.p.vars),
            }),
        }
    }

    fn use_var(&self, v: VarId) -> Result<(), PlanError> {
        if self.state(v) == VarState::Bound {
            Ok(())
        } else {
            Err(PlanError::Unbound { var: v })
        }
    }

    fn use_operand(&self, o: &Operand) -> Result<(), PlanError> {
        match *o {
            Operand::Var(v) | Operand::Field(v, _) => self.use_var(v),
            _ => Ok(()),
        }
    }

    fn need_kind(&self, kind: StrId) -> Result<(), PlanError> {
        if self.p.prefilter.binary_search(&kind).is_ok() {
            return Ok(());
        }
        let name = self
            .p
            .strings
            .get(kind as usize)
            .cloned()
            .unwrap_or_default();
        Err(PlanError::PrefilterMissing { kind: name })
    }

    fn visit(&mut self, id: OpId, depth: u32, clause: bool) -> Result<(), PlanError> {
        if depth > MAX_DEPTH {
            return Err(PlanError::TooDeep { limit: MAX_DEPTH });
        }
        let p = self.p;
        let Some(op) = p.ops.get(id as usize) else {
            return Err(PlanError::OutOfRange {
                what: "op",
                index: u64::from(id),
                len: p.ops.len() as u64,
            });
        };
        if std::mem::replace(&mut self.seen[id as usize], true) {
            return Err(PlanError::SharedOp { op: id });
        }
        match op {
            Op::Find { var, kind } => {
                Self::binder(id, clause)?;
                self.need_kind(*kind)?;
                self.bind(*var)?;
            }
            Op::FindSide { var, need, .. } => {
                Self::binder(id, clause)?;
                if !p.needs.contains(*need) {
                    return Err(PlanError::UndeclaredNeed { need: need.name() });
                }
                self.bind(*var)?;
            }
            Op::And(c) | Op::Or(c) => {
                for &k in c {
                    self.visit(k, depth + 1, false)?;
                }
            }
            Op::Not(c) => self.visit(*c, depth + 1, false)?,
            Op::Quant { var, cond, .. } | Op::CountCmp { var, cond, .. } => {
                self.bind(*var)?;
                self.visit(*cond, depth + 1, false)?;
                self.vars[usize::from(*var)] = VarState::Closed;
            }
            Op::Inside { sub: a, sup: b, .. } | Op::Order { a, b, .. } => {
                self.use_var(*a)?;
                self.use_var(*b)?;
            }
            Op::Verb {
                subject, object, ..
            } => {
                self.use_var(*subject)?;
                self.use_var(*object)?;
            }
            Op::Reaches {
                from, to, within, ..
            } => {
                self.use_var(*from)?;
                self.use_var(*to)?;
                self.max_within = Some(self.max_within.map_or(*within, |m| m.max(*within)));
            }
            Op::Call { def, args } => {
                if self.in_def.is_some_and(|cur| usize::from(*def) >= cur) {
                    return Err(PlanError::Misplaced {
                        op: id,
                        why: "a def may call only earlier defs",
                    });
                }
                for &a in args {
                    self.use_var(a)?;
                }
            }
            Op::Cmp { lhs, rhs, .. } => {
                self.use_operand(lhs)?;
                self.use_operand(rhs)?;
            }
            Op::MatchRegex { subject, .. } | Op::MatchGlob { subject, .. } => {
                self.use_operand(subject)?;
            }
        }
        Ok(())
    }

    fn binder(op: OpId, clause: bool) -> Result<(), PlanError> {
        if clause {
            Ok(())
        } else {
            Err(PlanError::Misplaced {
                op,
                why: "a find may only be a top-level clause",
            })
        }
    }

    fn cost(&self) -> Result<(), PlanError> {
        match (self.max_within, self.p.cost) {
            (Some(m), CostClass::Closure(d)) if d == m => Ok(()),
            (Some(_), _) => Err(PlanError::CostMismatch {
                why: "a reaches needs Closure(max within)",
            }),
            (None, CostClass::Closure(_)) => Err(PlanError::CostMismatch {
                why: "Closure without any reaches",
            }),
            (None, _) => Ok(()),
        }
    }
}
