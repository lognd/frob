//! Shared helpers for executor tests: a plan builder and small term builders.
#![allow(dead_code, missing_docs, reason = "each test binary uses a subset")]

use gob_ir::{GroupOrder, Location, Model, NodeId, NodeSpec, Operator, TermBuilder};
use gob_plan::plan::{
    Certainty, CmpOp, CostClass, Def, Langs, Limit, NeedSet, Op, OpId, Operand, Plan, PlanParts,
    Polarity, Position, Provenance, Quant, Report, StrId, VarId,
};
use gob_text::{FileId, FileInterner};

/// Builds a [`Plan`] op by op; strings are pooled, the prefilter is derived from the finds.
pub struct PlanBuilder {
    rule: String,
    polarity: Polarity,
    strings: Vec<String>,
    ops: Vec<Op>,
    defs: Vec<Def>,
    clauses: Vec<OpId>,
    reports: Vec<Report>,
    vars: u16,
    needs: NeedSet,
    max_within: Option<u16>,
}

impl PlanBuilder {
    pub fn new(rule: &str, polarity: Polarity) -> Self {
        Self {
            rule: rule.to_owned(),
            polarity,
            strings: Vec::new(),
            ops: Vec::new(),
            defs: Vec::new(),
            clauses: Vec::new(),
            reports: Vec::new(),
            vars: 0,
            needs: NeedSet::default(),
            max_within: None,
        }
    }

    pub fn needs(&mut self, needs: NeedSet) -> &mut Self {
        self.needs = needs;
        self
    }

    pub fn var(&mut self) -> VarId {
        self.vars += 1;
        self.vars - 1
    }

    pub fn s(&mut self, text: &str) -> StrId {
        if let Some(i) = self.strings.iter().position(|s| s == text) {
            return StrId::try_from(i).unwrap();
        }
        self.strings.push(text.to_owned());
        StrId::try_from(self.strings.len() - 1).unwrap()
    }

    pub fn op(&mut self, op: Op) -> OpId {
        if let Op::Reaches { within, .. } = op {
            self.max_within = Some(self.max_within.map_or(within, |m| m.max(within)));
        }
        self.ops.push(op);
        OpId::try_from(self.ops.len() - 1).unwrap()
    }

    /// A top-level `find var: kind`.
    pub fn find(&mut self, kind: &str) -> VarId {
        let var = self.var();
        let kind = self.s(kind);
        let id = self.op(Op::Find { var, kind });
        self.clauses.push(id);
        var
    }

    /// A top-level condition clause.
    pub fn clause(&mut self, op: OpId) -> &mut Self {
        self.clauses.push(op);
        self
    }

    pub fn field(&mut self, v: VarId, name: &str) -> Operand {
        Operand::Field(v, self.s(name))
    }

    pub fn str_lit(&mut self, text: &str) -> Operand {
        Operand::Str(self.s(text))
    }

    pub fn cmp(&mut self, lhs: Operand, op: CmpOp, rhs: Operand) -> OpId {
        self.op(Op::Cmp { lhs, op, rhs })
    }

    pub fn inside(&mut self, sub: VarId, sup: VarId, direct: bool) -> OpId {
        self.op(Op::Inside { sub, sup, direct })
    }

    pub fn order(&mut self, a: VarId, b: VarId, pos: Position) -> OpId {
        self.op(Op::Order { a, b, pos })
    }

    /// `some`/`no` `var: kind where cond`, building `cond` with `body(var)`.
    pub fn quant(
        &mut self,
        quant: Quant,
        kind: &str,
        body: impl FnOnce(&mut Self, VarId) -> OpId,
    ) -> OpId {
        let var = self.var();
        let cond = body(self, var);
        let kind = self.s(kind);
        self.op(Op::Quant {
            quant,
            var,
            kind,
            cond,
        })
    }

    pub fn verb(
        &mut self,
        subject: VarId,
        verb: &str,
        object: VarId,
        certainty: Certainty,
    ) -> OpId {
        let verb = self.s(verb);
        self.op(Op::Verb {
            subject,
            object,
            verb,
            certainty,
        })
    }

    /// A def with `n` fresh parameters whose body `body` builds; returns its index.
    pub fn def(&mut self, n: usize, body: impl FnOnce(&mut Self, &[VarId]) -> OpId) -> u16 {
        let params: Vec<VarId> = (0..n).map(|_| self.var()).collect();
        let body = body(self, &params);
        self.defs.push(Def { params, body });
        u16::try_from(self.defs.len() - 1).unwrap()
    }

    pub fn call(&mut self, def: u16, args: &[VarId]) -> OpId {
        self.op(Op::Call {
            def,
            args: args.to_vec(),
        })
    }

    /// `count(var: kind where body(var)) op limit`.
    pub fn count_cmp(
        &mut self,
        kind: &str,
        op: CmpOp,
        limit: Limit,
        body: impl FnOnce(&mut Self, VarId) -> OpId,
    ) -> OpId {
        let var = self.var();
        let cond = body(self, var);
        let kind = self.s(kind);
        self.op(Op::CountCmp {
            var,
            kind,
            cond,
            op,
            limit,
        })
    }

    pub fn report(&mut self, when: Option<OpId>, subject: VarId, message: &str) {
        let message = self.s(message);
        self.reports.push(Report {
            when,
            subject,
            message,
        });
    }

    pub fn build(&mut self) -> Plan {
        let mut prefilter: Vec<StrId> = self
            .ops
            .iter()
            .filter_map(|o| match o {
                Op::Find { kind, .. } => Some(*kind),
                _ => None,
            })
            .collect();
        prefilter.sort_unstable();
        prefilter.dedup();
        let parts = PlanParts {
            rule: self.rule.clone(),
            provenance: Provenance::Std,
            polarity: self.polarity,
            langs: Langs::Any,
            needs: self.needs,
            prefilter,
            cost: self
                .max_within
                .map_or(CostClass::PerFile, CostClass::Closure),
            vars: self.vars,
            strings: self.strings.clone(),
            ops: self.ops.clone(),
            defs: self.defs.clone(),
            clauses: self.clauses.clone(),
            reports: self.reports.clone(),
        };
        Plan::new(parts).expect("test plan is valid")
    }
}

/// A term under construction with a running offset, so nodes get distinct locations.
pub struct Doc {
    pub tb: TermBuilder,
    pub file: FileId,
    pub at: u32,
}

impl Doc {
    pub fn new(path: &str, lang: &str) -> Self {
        Self {
            tb: TermBuilder::new(path, lang),
            file: FileInterner::new().intern(path),
            at: 0,
        }
    }

    /// A node over the explicit byte range `[start, end)`.
    pub fn at_range(
        &mut self,
        spec: impl FnOnce(Location) -> NodeSpec,
        start: u32,
        end: u32,
        kids: &[NodeId],
    ) -> NodeId {
        self.tb
            .node(spec(Location::text(self.file, start, end)), kids)
            .unwrap()
    }

    /// A node over the next free byte.
    pub fn add(&mut self, op: Operator, name: Option<&str>, kids: &[NodeId]) -> NodeId {
        self.at += 1;
        let mut spec = NodeSpec::new(op, Location::text(self.file, self.at, self.at + 1));
        if let Some(n) = name {
            spec = spec.named(n);
        }
        self.tb.node(spec, kids).unwrap()
    }

    pub fn root(self, kids: &[NodeId]) -> (Model, Vec<NodeId>) {
        let mut d = self;
        let root = d.add(Operator::group(GroupOrder::Sequence), None, kids);
        let term = d.tb.finish(root).unwrap();
        (Model::lexical(term), kids.to_vec())
    }
}
