//! The planner and the numbering pass: name-based clauses to an op arena.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX
use std::collections::BTreeSet;

use super::LowerError;
use super::convert::{Cond, CountSideC, DefItem, FindItem, LangNames, Lim, Lowered, Opd, Src};
use crate::plan::{
    Certainty, CountSide, Def, Langs, Leaf, Limit, Need, NeedSet, Op, OpId, Operand, Plan,
    PlanParts, Polarity, Provenance, Report, StrId, Unresolved, VarId, cost_class,
};

/// The sort key of a condition: its structure, so equal clauses sort alike in any source order.
fn key(c: &Cond) -> String {
    format!("{c:?}")
}

fn sorted(mut v: Vec<Cond>) -> Vec<Cond> {
    v.sort_by_cached_key(key);
    v
}

fn free_in_opd(o: &Opd, bound: &[String], out: &mut BTreeSet<String>) {
    match o {
        Opd::Var(v) | Opd::Field(v, _) => {
            if !bound.contains(v) {
                out.insert(v.clone());
            }
        }
        Opd::Slug(a) => free_in_opd(a, bound, out),
        Opd::Resolve(a, b) => {
            free_in_opd(a, bound, out);
            free_in_opd(b, bound, out);
        }
        Opd::Int(_) | Opd::Str(_) | Opd::Bool(_) => {}
    }
}

/// The variables a condition uses that it does not bind itself.
fn free(c: &Cond, bound: &mut Vec<String>, out: &mut BTreeSet<String>) {
    let mut name = |v: &String, bound: &[String]| {
        if !bound.contains(v) {
            out.insert(v.clone());
        }
    };
    match c {
        Cond::And(v) | Cond::Or(v) => {
            for x in v {
                free(x, bound, out);
            }
        }
        Cond::Not(x) => free(x, bound, out),
        Cond::Quant { var, cond, .. } | Cond::CountCmp { var, cond, .. } => {
            bound.push(var.clone());
            free(cond, bound, out);
            bound.pop();
        }
        Cond::CountPair { lhs, rhs, .. } => {
            for side in [lhs, rhs] {
                bound.push(side.var.clone());
                free(&side.cond, bound, out);
                bound.pop();
            }
        }
        Cond::Inside { sub, sup, .. } => {
            name(sub, bound);
            name(sup, bound);
        }
        Cond::Order { a, b, .. } => {
            name(a, bound);
            name(b, bound);
        }
        Cond::Verb {
            subject, object, ..
        } => {
            name(subject, bound);
            name(object, bound);
        }
        Cond::Cmp { lhs, rhs, .. } => {
            free_in_opd(lhs, bound, out);
            free_in_opd(rhs, bound, out);
        }
        Cond::Regex { subject, .. }
        | Cond::Glob { subject, .. }
        | Cond::GlobSet { subject, .. }
        | Cond::Is { subject, .. }
        | Cond::Exists(subject) => {
            free_in_opd(subject, bound, out);
        }
        Cond::HasAttr { var, .. } | Cond::MatchSnippet { var, .. } | Cond::InVocab { var, .. } => {
            name(var, bound);
        }
        Cond::GlobOperand { subject, pattern } => {
            free_in_opd(subject, bound, out);
            free_in_opd(pattern, bound, out);
        }
        Cond::Under { subject, prefix } => {
            free_in_opd(subject, bound, out);
            free_in_opd(prefix, bound, out);
        }
        Cond::InUnit { sub, unit } => {
            name(sub, bound);
            name(unit, bound);
        }
        Cond::Reaches { from, to, .. } => {
            name(from, bound);
            name(to, bound);
        }
        Cond::Call { args, .. } => {
            for a in args {
                name(a, bound);
            }
        }
    }
}

fn free_vars(c: &Cond) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    free(c, &mut Vec::new(), &mut out);
    out
}

/// The binders in a fixed order: by what they range over, then by name. Nothing else about the
/// source order may leak into the plan, so conditions never decide it.
fn order_finds(finds: &[FindItem]) -> Vec<usize> {
    let mut order: Vec<usize> = (0..finds.len()).collect();
    order.sort_by(|&a, &b| (&finds[a].src, &finds[a].name).cmp(&(&finds[b].src, &finds[b].name)));
    order
}

struct Builder {
    strings: Vec<String>,
    ops: Vec<Op>,
    next_var: VarId,
    env: Vec<(String, VarId)>,
}

impl Builder {
    fn intern(&mut self, s: &str) -> StrId {
        let at = self.strings.iter().position(|x| x == s).unwrap_or_else(|| {
            self.strings.push(s.to_owned());
            self.strings.len() - 1
        });
        u32::try_from(at).unwrap_or(u32::MAX)
    }

    fn push(&mut self, op: Op) -> OpId {
        self.ops.push(op);
        u32::try_from(self.ops.len() - 1).unwrap_or(u32::MAX)
    }

    fn fresh(&mut self) -> VarId {
        let v = self.next_var;
        self.next_var = self.next_var.saturating_add(1);
        v
    }

    fn var(&self, name: &str) -> Result<VarId, LowerError> {
        self.env
            .iter()
            .rev()
            .find(|(n, _)| n == name)
            .map(|(_, v)| *v)
            .ok_or(LowerError::Internal {
                what: "a variable reached emission unbound",
            })
    }

    fn operand(&mut self, o: &Opd) -> Result<Operand, LowerError> {
        Ok(match o {
            Opd::Var(v) => Operand::Var(self.var(v)?),
            Opd::Field(v, f) => Operand::Field(self.var(v)?, self.intern(f)),
            Opd::Int(i) => Operand::Int(*i),
            Opd::Str(s) => Operand::Str(self.intern(s)),
            Opd::Bool(b) => Operand::Bool(*b),
            Opd::Slug(a) => Operand::Slug(self.leaf(a)?),
            Opd::Resolve(a, b) => Operand::Resolve(self.leaf(a)?, self.leaf(b)?),
        })
    }

    /// A call argument: a call-free operand.
    fn leaf(&mut self, o: &Opd) -> Result<Leaf, LowerError> {
        let plain = self.operand(o)?;
        Leaf::of(plain).ok_or(LowerError::Internal {
            what: "a call argument reached emission as a call",
        })
    }

    #[allow(
        clippy::too_many_lines,
        reason = "a flat match over every condition form"
    )]
    fn cond(&mut self, c: &Cond) -> Result<OpId, LowerError> {
        let op = match c {
            Cond::And(v) => Op::And(v.iter().map(|x| self.cond(x)).collect::<Result<_, _>>()?),
            Cond::Or(v) => Op::Or(v.iter().map(|x| self.cond(x)).collect::<Result<_, _>>()?),
            Cond::Not(x) => Op::Not(self.cond(x)?),
            Cond::Quant {
                quant,
                var,
                kind,
                cond,
            } => {
                let id = self.fresh();
                self.env.push((var.clone(), id));
                let inner = self.cond(cond);
                self.env.pop();
                Op::Quant {
                    quant: *quant,
                    var: id,
                    kind: self.intern(kind),
                    cond: inner?,
                }
            }
            Cond::Cmp { lhs, op, rhs } => Op::Cmp {
                lhs: self.operand(lhs)?,
                op: *op,
                rhs: self.operand(rhs)?,
            },
            Cond::Regex { subject, pattern } => Op::MatchRegex {
                subject: self.operand(subject)?,
                pattern: self.intern(pattern),
            },
            Cond::Glob { subject, pattern } => Op::MatchGlob {
                subject: self.operand(subject)?,
                pattern: self.intern(pattern),
            },
            Cond::GlobSet {
                subject,
                need,
                table,
                column,
            } => Op::MatchGlobSet {
                subject: self.operand(subject)?,
                need: *need,
                table: self.intern(table),
                column: self.intern(column),
            },
            Cond::Is { subject, test } => Op::Is {
                subject: self.operand(subject)?,
                test: self.intern(test),
            },
            Cond::Exists(subject) => Op::Exists {
                subject: self.operand(subject)?,
            },
            Cond::HasAttr { var, attr } => Op::HasAttr {
                var: self.var(var)?,
                attr: self.intern(attr),
            },
            Cond::MatchSnippet {
                var,
                lang,
                pattern,
                within,
            } => Op::MatchSnippet {
                var: self.var(var)?,
                lang: self.intern(lang),
                pattern: self.intern(pattern),
                within: *within,
            },
            Cond::InVocab { var, classes } => Op::InVocab {
                var: self.var(var)?,
                classes: classes.iter().map(|c| self.intern(c)).collect(),
            },
            Cond::GlobOperand { subject, pattern } => Op::MatchGlobOperand {
                subject: self.operand(subject)?,
                pattern: self.operand(pattern)?,
            },
            Cond::Under { subject, prefix } => Op::Under {
                subject: self.operand(subject)?,
                prefix: self.operand(prefix)?,
            },
            Cond::CountCmp {
                var,
                kind,
                cond,
                op,
                limit,
            } => {
                let id = self.fresh();
                self.env.push((var.clone(), id));
                let inner = self.cond(cond);
                self.env.pop();
                Op::CountCmp {
                    var: id,
                    kind: self.intern(kind),
                    cond: inner?,
                    op: *op,
                    limit: match limit {
                        Lim::Int(i) => Limit::Int(*i),
                        Lim::Knob(name, default) => Limit::Knob {
                            name: self.intern(name),
                            default: *default,
                        },
                    },
                }
            }
            Cond::CountPair { lhs, op, rhs } => Op::CountPair {
                lhs: self.count_side(lhs)?,
                op: *op,
                rhs: self.count_side(rhs)?,
            },
            _ => self.relation(c)?,
        };
        Ok(self.push(op))
    }

    /// One counted side of a pair: a fresh variable scoping its condition.
    fn count_side(&mut self, side: &CountSideC) -> Result<CountSide, LowerError> {
        let id = self.fresh();
        self.env.push((side.var.clone(), id));
        let inner = self.cond(&side.cond);
        self.env.pop();
        Ok(CountSide {
            var: id,
            kind: self.intern(&side.kind),
            cond: inner?,
            scale: side.scale,
        })
    }

    /// The conditions that relate variables: containment, order, verbs, units, def calls.
    fn relation(&mut self, c: &Cond) -> Result<Op, LowerError> {
        Ok(match c {
            Cond::Inside { sub, sup, direct } => Op::Inside {
                sub: self.var(sub)?,
                sup: self.var(sup)?,
                direct: *direct,
            },
            Cond::Order { a, b, pos } => Op::Order {
                a: self.var(a)?,
                b: self.var(b)?,
                pos: *pos,
            },
            Cond::Verb {
                subject,
                object,
                verb,
                certainty,
            } => Op::Verb {
                subject: self.var(subject)?,
                object: self.var(object)?,
                verb: self.intern(verb),
                certainty: *certainty,
            },
            Cond::InUnit { sub, unit } => Op::InUnit {
                sub: self.var(sub)?,
                unit: self.var(unit)?,
            },
            Cond::Reaches {
                from,
                to,
                via,
                within,
            } => Op::Reaches {
                from: self.var(from)?,
                to: self.var(to)?,
                via: self.intern(via),
                within: *within,
                certainty: Certainty::Default,
            },
            Cond::Call { def, args } => Op::Call {
                def: u16::try_from(*def).map_err(|_| LowerError::Internal {
                    what: "more defs than a plan can index",
                })?,
                args: args.iter().map(|a| self.var(a)).collect::<Result<_, _>>()?,
            },
            _ => {
                return Err(LowerError::Internal {
                    what: "a condition reached the relation emitter",
                });
            }
        })
    }
}

fn langs_of(b: &mut Builder, names: &LangNames) -> Langs {
    match names {
        LangNames::Any => Langs::Any,
        LangNames::Nothing => Langs::Nothing,
        LangNames::Only(names) => {
            let names: BTreeSet<&String> = names.iter().collect();
            let mut ids: Vec<StrId> = names.into_iter().map(|n| b.intern(n)).collect();
            ids.sort_unstable();
            ids.dedup();
            Langs::Only(ids)
        }
    }
}

/// Conditions by slot (the binder they follow), then the P- subject tail, then the plain tail.
fn place_conds(l: &Lowered, placed_names: &[&str]) -> (Vec<Vec<Cond>>, Vec<Cond>, Vec<Cond>) {
    // Every condition (written on a binder or standalone) goes right after the last binder it
    // uses. A P- plan instead keeps all binders and their written conditions first (the
    // subjects), then the standalone conditions (the good thing).
    let pminus = l.polarity == Polarity::Pminus;
    let mut slots: Vec<Vec<Cond>> = vec![Vec::new(); placed_names.len()];
    let mut subject_tail: Vec<Cond> = Vec::new();
    let mut tail: Vec<Cond> = Vec::new();
    let mut place = |c: &Cond, written: bool| {
        let last = free_vars(c)
            .iter()
            .filter_map(|v| placed_names.iter().position(|n| n == v))
            .max();
        match (pminus, written, last) {
            (true, true, _) => subject_tail.push(c.clone()),
            (false, _, Some(i)) => slots[i].push(c.clone()),
            _ => tail.push(c.clone()),
        }
    };
    for f in &l.finds {
        for c in &f.attached {
            place(c, true);
        }
    }
    for c in &l.wheres {
        place(c, false);
    }
    (slots, subject_tail, tail)
}

/// The defs in text order: each parameter is a fresh slot visible only in its own body.
fn emit_defs(b: &mut Builder, defs: &[DefItem]) -> Result<Vec<Def>, LowerError> {
    let mut out = Vec::new();
    for d in defs {
        let params: Vec<VarId> = d.params.iter().map(|_| b.fresh()).collect();
        let mark = b.env.len();
        b.env
            .extend(d.params.iter().cloned().zip(params.iter().copied()));
        let body = b.cond(&d.body);
        b.env.truncate(mark);
        out.push(Def {
            params,
            body: body?,
        });
    }
    Ok(out)
}

pub(super) fn emit(l: &Lowered, provenance: Provenance) -> Result<Plan, LowerError> {
    let order = order_finds(&l.finds);
    let placed_names: Vec<&str> = order.iter().map(|&i| l.finds[i].name.as_str()).collect();

    let (mut slots, subject_tail, tail) = place_conds(l, &placed_names);
    let pminus = l.polarity == Polarity::Pminus;

    let mut b = Builder {
        strings: Vec::new(),
        ops: Vec::new(),
        next_var: 0,
        env: Vec::new(),
    };
    let defs = emit_defs(&mut b, &l.defs)?;
    let mut clauses = Vec::new();
    for (slot, &fi) in order.iter().enumerate() {
        let f = &l.finds[fi];
        let var = b.fresh();
        b.env.push((f.name.clone(), var));
        let op = match &f.src {
            Src::Kind(k) => {
                let kind = b.intern(k);
                Op::Find { var, kind }
            }
            Src::Side(need, table) => Op::FindSide {
                var,
                need: *need,
                table: b.intern(table),
            },
        };
        clauses.push(b.push(op));
        for c in sorted(std::mem::take(&mut slots[slot])) {
            clauses.push(b.cond(&c)?);
        }
    }
    for c in sorted(subject_tail) {
        clauses.push(b.cond(&c)?);
    }
    let subjects = if pminus {
        u16::try_from(clauses.len()).unwrap_or(u16::MAX)
    } else {
        0
    };
    for c in sorted(tail) {
        clauses.push(b.cond(&c)?);
    }

    let mut unresolved = Vec::new();
    for (when, reason) in &l.unresolved {
        let when = b.cond(when)?;
        unresolved.push(Unresolved {
            when,
            reason: b.intern(reason),
        });
    }
    let mut reports = Vec::new();
    for r in &l.reports {
        let when = r.when.as_ref().map(|w| b.cond(w)).transpose()?;
        reports.push(Report {
            when,
            subject: b.var(&r.subject)?,
            message: b.intern(&r.message),
        });
    }

    let langs = langs_of(&mut b, &l.langs);
    // frob:ticket 01M3ZX7EQ5NARR4Z2SAY4H23AQ
    let kinds = super::prefilter_kinds(&b.ops, &clauses);
    let needs: Vec<Need> = l.needs.clone();
    let parts = PlanParts {
        rule: l.id.clone(),
        provenance,
        polarity: l.polarity,
        langs,
        needs: NeedSet::of(&needs),
        prefilter: kinds,
        // frob:ticket 01M3ZX7EQ5NARR4Z2SAY4H23AQ
        cost: cost_class(&b.ops, l.repo_scope),
        vars: b.next_var,
        strings: b.strings,
        ops: b.ops,
        defs,
        clauses,
        subjects,
        unresolved,
        reports,
    };
    Ok(Plan::new(parts)?)
}
