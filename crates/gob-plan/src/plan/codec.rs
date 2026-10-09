//! The canonical byte form: fixed-width little-endian, no padding, no varints.
//!
//! Canonical means one plan has exactly one encoding, so any accepted bytes
//! re-encode to themselves. Decoding checks every count against the bytes left
//! before allocating and never indexes or recurses on untrusted data.

use super::error::PlanError;
use super::ir::{
    Certainty, CmpOp, CostClass, Def, Langs, Limit, Need, NeedSet, Op, Operand, PlanParts,
    Polarity, Position, Provenance, Quant, Report,
};
use super::limits::{MAX_BYTES, MAX_DEFS, MAX_LIST, MAX_OPS, MAX_PARAMS, MAX_STR_LEN, MAX_STRINGS};

/// File magic.
pub const MAGIC: &[u8; 8] = b"FROBPLAN";
/// The one format version this engine reads and writes.
pub const VERSION: u16 = 2;

/// Encodes `p` canonically; the caller guarantees `p` is valid.
pub fn encode(p: &PlanParts) -> Vec<u8> {
    let mut w = Vec::new();
    w.extend_from_slice(MAGIC);
    put_u16(&mut w, VERSION);
    put_str(&mut w, &p.rule);
    match &p.provenance {
        Provenance::Std => w.push(0),
        Provenance::Pack(n) => {
            w.push(1);
            put_str(&mut w, n);
        }
    }
    w.push(polarity_tag(p.polarity));
    match &p.langs {
        Langs::Any => w.push(0),
        Langs::Nothing => w.push(1),
        Langs::Only(l) => {
            w.push(2);
            put_u32s(&mut w, l);
        }
    }
    w.push(p.needs.0);
    put_u32s(&mut w, &p.prefilter);
    match p.cost {
        CostClass::PerFile => w.push(0),
        CostClass::PerRepo => w.push(1),
        CostClass::Closure(d) => {
            w.push(2);
            put_u16(&mut w, d);
        }
    }
    put_u16(&mut w, p.vars);
    put_len(&mut w, p.strings.len());
    for s in &p.strings {
        put_str(&mut w, s);
    }
    put_len(&mut w, p.ops.len());
    for op in &p.ops {
        put_op(&mut w, op);
    }
    put_len(&mut w, p.defs.len());
    for d in &p.defs {
        put_u16s(&mut w, &d.params);
        put_u32(&mut w, d.body);
    }
    put_u32s(&mut w, &p.clauses);
    put_len(&mut w, p.reports.len());
    for r in &p.reports {
        match r.when {
            None => w.push(0),
            Some(c) => {
                w.push(1);
                put_u32(&mut w, c);
            }
        }
        put_u16(&mut w, r.subject);
        put_u32(&mut w, r.message);
    }
    w
}

/// Decodes untrusted bytes into unvalidated parts; structure only, no semantics.
#[allow(
    clippy::too_many_lines,
    reason = "one flat match or field list per wire item"
)]
pub fn decode(bytes: &[u8]) -> Result<PlanParts, PlanError> {
    if bytes.len() > MAX_BYTES {
        return Err(PlanError::TooLarge {
            what: "plan bytes",
            found: bytes.len() as u64,
            limit: MAX_BYTES as u64,
        });
    }
    let mut r = Reader { b: bytes };
    if r.take(MAGIC.len(), "magic")
        .map_err(|_| PlanError::BadMagic)?
        != MAGIC
    {
        return Err(PlanError::BadMagic);
    }
    let found = r.u16("version")?;
    if found != VERSION {
        return Err(PlanError::UnsupportedVersion {
            found,
            supported: VERSION,
        });
    }
    let rule = r.string("rule id")?;
    let provenance = match r.u8("provenance")? {
        0 => Provenance::Std,
        1 => Provenance::Pack(r.string("pack name")?),
        tag => {
            return Err(PlanError::BadTag {
                what: "provenance",
                tag,
            });
        }
    };
    let polarity = polarity_from(r.u8("polarity")?)?;
    let langs = match r.u8("langs")? {
        0 => Langs::Any,
        1 => Langs::Nothing,
        2 => Langs::Only(r.u32s("langs", MAX_LIST)?),
        tag => return Err(PlanError::BadTag { what: "langs", tag }),
    };
    let needs = NeedSet(r.u8("needs")?);
    let prefilter = r.u32s("prefilter", MAX_LIST)?;
    let cost = match r.u8("cost class")? {
        0 => CostClass::PerFile,
        1 => CostClass::PerRepo,
        2 => CostClass::Closure(r.u16("closure depth")?),
        tag => {
            return Err(PlanError::BadTag {
                what: "cost class",
                tag,
            });
        }
    };
    let vars = r.u16("var count")?;
    let n = r.count("strings", MAX_STRINGS, 4)?;
    let mut strings = Vec::with_capacity(n);
    for _ in 0..n {
        strings.push(r.string("pool string")?);
    }
    let n = r.count("ops", MAX_OPS, 1)?;
    let mut ops = Vec::with_capacity(n);
    for _ in 0..n {
        ops.push(r.op()?);
    }
    let n = r.count("defs", MAX_DEFS, 8)?;
    let mut defs = Vec::with_capacity(n);
    for _ in 0..n {
        defs.push(Def {
            params: r.u16s("def parameters", MAX_PARAMS)?,
            body: r.u32("def body")?,
        });
    }
    let clauses = r.u32s("clauses", MAX_LIST)?;
    let n = r.count("reports", MAX_LIST, 7)?;
    let mut reports = Vec::with_capacity(n);
    for _ in 0..n {
        let when = match r.u8("report guard")? {
            0 => None,
            1 => Some(r.u32("report guard op")?),
            tag => {
                return Err(PlanError::BadTag {
                    what: "report guard",
                    tag,
                });
            }
        };
        reports.push(Report {
            when,
            subject: r.u16("report subject")?,
            message: r.u32("report message")?,
        });
    }
    if !r.b.is_empty() {
        return Err(PlanError::TrailingBytes { extra: r.b.len() });
    }
    Ok(PlanParts {
        rule,
        provenance,
        polarity,
        langs,
        needs,
        prefilter,
        cost,
        vars,
        strings,
        ops,
        defs,
        clauses,
        reports,
    })
}

fn polarity_tag(p: Polarity) -> u8 {
    match p {
        Polarity::Pplus => 0,
        Polarity::Pminus => 1,
        Polarity::P0 => 2,
        Polarity::Pn => 3,
        Polarity::Pc => 4,
    }
}

fn polarity_from(tag: u8) -> Result<Polarity, PlanError> {
    Ok(match tag {
        0 => Polarity::Pplus,
        1 => Polarity::Pminus,
        2 => Polarity::P0,
        3 => Polarity::Pn,
        4 => Polarity::Pc,
        tag => {
            return Err(PlanError::BadTag {
                what: "polarity",
                tag,
            });
        }
    })
}

fn put_u16(w: &mut Vec<u8>, v: u16) {
    w.extend_from_slice(&v.to_le_bytes());
}

fn put_u32(w: &mut Vec<u8>, v: u32) {
    w.extend_from_slice(&v.to_le_bytes());
}

/// Lengths are bounded far below `u32::MAX` by the limits, so the cast is lossless for valid plans.
#[allow(clippy::cast_possible_truncation)]
fn put_len(w: &mut Vec<u8>, n: usize) {
    put_u32(w, n as u32);
}

fn put_u16s(w: &mut Vec<u8>, v: &[u16]) {
    put_len(w, v.len());
    for x in v {
        put_u16(w, *x);
    }
}

fn put_str(w: &mut Vec<u8>, s: &str) {
    put_len(w, s.len());
    w.extend_from_slice(s.as_bytes());
}

fn put_u32s(w: &mut Vec<u8>, v: &[u32]) {
    put_len(w, v.len());
    for x in v {
        put_u32(w, *x);
    }
}

fn put_operand(w: &mut Vec<u8>, o: &Operand) {
    match *o {
        Operand::Var(v) => {
            w.push(0);
            put_u16(w, v);
        }
        Operand::Field(v, f) => {
            w.push(1);
            put_u16(w, v);
            put_u32(w, f);
        }
        Operand::Int(i) => {
            w.push(2);
            w.extend_from_slice(&i.to_le_bytes());
        }
        Operand::Str(s) => {
            w.push(3);
            put_u32(w, s);
        }
        Operand::Bool(b) => {
            w.push(4);
            w.push(u8::from(b));
        }
    }
}

#[allow(
    clippy::too_many_lines,
    reason = "one flat match or field list per wire item"
)]
fn put_op(w: &mut Vec<u8>, op: &Op) {
    match op {
        Op::Find { var, kind } => {
            w.push(0);
            put_u16(w, *var);
            put_u32(w, *kind);
        }
        Op::FindSide { var, need, table } => {
            w.push(1);
            put_u16(w, *var);
            w.push(*need as u8);
            put_u32(w, *table);
        }
        Op::And(c) => {
            w.push(2);
            put_u32s(w, c);
        }
        Op::Or(c) => {
            w.push(3);
            put_u32s(w, c);
        }
        Op::Not(c) => {
            w.push(4);
            put_u32(w, *c);
        }
        Op::Quant {
            quant,
            var,
            kind,
            cond,
        } => {
            w.push(5);
            w.push(*quant as u8);
            put_u16(w, *var);
            put_u32(w, *kind);
            put_u32(w, *cond);
        }
        Op::Inside { sub, sup, direct } => {
            w.push(6);
            put_u16(w, *sub);
            put_u16(w, *sup);
            w.push(u8::from(*direct));
        }
        Op::Order { a, b, pos } => {
            w.push(7);
            put_u16(w, *a);
            put_u16(w, *b);
            w.push(*pos as u8);
        }
        Op::Verb {
            subject,
            object,
            verb,
            certainty,
        } => {
            w.push(8);
            put_u16(w, *subject);
            put_u16(w, *object);
            put_u32(w, *verb);
            w.push(*certainty as u8);
        }
        Op::Reaches {
            from,
            to,
            via,
            within,
            certainty,
        } => {
            w.push(9);
            put_u16(w, *from);
            put_u16(w, *to);
            put_u32(w, *via);
            put_u16(w, *within);
            w.push(*certainty as u8);
        }
        Op::CountCmp {
            var,
            kind,
            cond,
            op,
            limit,
        } => {
            w.push(13);
            put_u16(w, *var);
            put_u32(w, *kind);
            put_u32(w, *cond);
            w.push(*op as u8);
            match *limit {
                Limit::Int(n) => {
                    w.push(0);
                    w.extend_from_slice(&n.to_le_bytes());
                }
                Limit::Knob { name, default } => {
                    w.push(1);
                    put_u32(w, name);
                    w.extend_from_slice(&default.to_le_bytes());
                }
            }
        }
        Op::Call { def, args } => {
            w.push(14);
            put_u16(w, *def);
            put_u16s(w, args);
        }
        Op::Cmp { lhs, op, rhs } => {
            w.push(10);
            put_operand(w, lhs);
            w.push(*op as u8);
            put_operand(w, rhs);
        }
        Op::MatchRegex { subject, pattern } => {
            w.push(11);
            put_operand(w, subject);
            put_u32(w, *pattern);
        }
        Op::MatchGlob { subject, pattern } => {
            w.push(12);
            put_operand(w, subject);
            put_u32(w, *pattern);
        }
    }
}

/// A cursor over untrusted bytes; every read is bounds-checked.
struct Reader<'a> {
    b: &'a [u8],
}

impl Reader<'_> {
    fn take(&mut self, n: usize, what: &'static str) -> Result<&[u8], PlanError> {
        if self.b.len() < n {
            return Err(PlanError::Truncated { what });
        }
        let (head, tail) = self.b.split_at(n);
        self.b = tail;
        Ok(head)
    }

    fn array<const N: usize>(&mut self, what: &'static str) -> Result<[u8; N], PlanError> {
        let mut out = [0u8; N];
        out.copy_from_slice(self.take(N, what)?);
        Ok(out)
    }

    fn u8(&mut self, what: &'static str) -> Result<u8, PlanError> {
        Ok(self.array::<1>(what)?[0])
    }

    fn u16(&mut self, what: &'static str) -> Result<u16, PlanError> {
        Ok(u16::from_le_bytes(self.array(what)?))
    }

    fn u32(&mut self, what: &'static str) -> Result<u32, PlanError> {
        Ok(u32::from_le_bytes(self.array(what)?))
    }

    fn i64(&mut self, what: &'static str) -> Result<i64, PlanError> {
        Ok(i64::from_le_bytes(self.array(what)?))
    }

    fn u64(&mut self, what: &'static str) -> Result<u64, PlanError> {
        Ok(u64::from_le_bytes(self.array(what)?))
    }

    fn u16s(&mut self, what: &'static str, limit: usize) -> Result<Vec<u16>, PlanError> {
        let n = self.count(what, limit, 2)?;
        (0..n).map(|_| self.u16(what)).collect()
    }

    fn limit(&mut self) -> Result<Limit, PlanError> {
        match self.u8("limit")? {
            0 => Ok(Limit::Int(self.u64("limit value")?)),
            1 => Ok(Limit::Knob {
                name: self.u32("knob name")?,
                default: self.u64("knob default")?,
            }),
            tag => Err(PlanError::BadTag { what: "limit", tag }),
        }
    }

    fn bool(&mut self, what: &'static str) -> Result<bool, PlanError> {
        match self.u8(what)? {
            0 => Ok(false),
            1 => Ok(true),
            tag => Err(PlanError::BadTag { what, tag }),
        }
    }

    /// A count of items each at least `min_item` bytes: bounded by `limit` and by the bytes left.
    fn count(
        &mut self,
        what: &'static str,
        limit: usize,
        min_item: usize,
    ) -> Result<usize, PlanError> {
        let n = self.u32(what)? as usize;
        if n > limit {
            return Err(PlanError::TooLarge {
                what,
                found: n as u64,
                limit: limit as u64,
            });
        }
        if n.saturating_mul(min_item) > self.b.len() {
            return Err(PlanError::Truncated { what });
        }
        Ok(n)
    }

    fn string(&mut self, what: &'static str) -> Result<String, PlanError> {
        let n = self.count(what, MAX_STR_LEN, 1)?;
        let raw = self.take(n, what)?;
        std::str::from_utf8(raw)
            .map(str::to_owned)
            .map_err(|_| PlanError::BadUtf8 { what })
    }

    fn u32s(&mut self, what: &'static str, limit: usize) -> Result<Vec<u32>, PlanError> {
        let n = self.count(what, limit, 4)?;
        (0..n).map(|_| self.u32(what)).collect()
    }

    fn operand(&mut self) -> Result<Operand, PlanError> {
        Ok(match self.u8("operand")? {
            0 => Operand::Var(self.u16("operand var")?),
            1 => Operand::Field(self.u16("operand var")?, self.u32("operand field")?),
            2 => Operand::Int(self.i64("operand int")?),
            3 => Operand::Str(self.u32("operand string")?),
            4 => Operand::Bool(self.bool("operand bool")?),
            tag => {
                return Err(PlanError::BadTag {
                    what: "operand",
                    tag,
                });
            }
        })
    }

    fn certainty(&mut self) -> Result<Certainty, PlanError> {
        match self.u8("certainty")? {
            0 => Ok(Certainty::Default),
            1 => Ok(Certainty::Certainly),
            2 => Ok(Certainty::Possibly),
            tag => Err(PlanError::BadTag {
                what: "certainty",
                tag,
            }),
        }
    }

    fn need(&mut self) -> Result<Need, PlanError> {
        match self.u8("need")? {
            0 => Ok(Need::Config),
            1 => Ok(Need::Diff),
            2 => Ok(Need::Lease),
            3 => Ok(Need::Model),
            tag => Err(PlanError::BadTag { what: "need", tag }),
        }
    }

    fn quant(&mut self) -> Result<Quant, PlanError> {
        match self.u8("quantifier")? {
            0 => Ok(Quant::Some),
            1 => Ok(Quant::No),
            tag => Err(PlanError::BadTag {
                what: "quantifier",
                tag,
            }),
        }
    }

    fn position(&mut self) -> Result<Position, PlanError> {
        match self.u8("position")? {
            0 => Ok(Position::Before),
            1 => Ok(Position::After),
            2 => Ok(Position::Adjoins),
            tag => Err(PlanError::BadTag {
                what: "position",
                tag,
            }),
        }
    }

    fn cmp_op(&mut self) -> Result<CmpOp, PlanError> {
        match self.u8("cmp op")? {
            0 => Ok(CmpOp::Eq),
            1 => Ok(CmpOp::Ne),
            2 => Ok(CmpOp::Lt),
            3 => Ok(CmpOp::Le),
            4 => Ok(CmpOp::Gt),
            5 => Ok(CmpOp::Ge),
            tag => Err(PlanError::BadTag {
                what: "cmp op",
                tag,
            }),
        }
    }

    fn op(&mut self) -> Result<Op, PlanError> {
        Ok(match self.u8("op")? {
            0 => Op::Find {
                var: self.u16("var")?,
                kind: self.u32("kind")?,
            },
            1 => Op::FindSide {
                var: self.u16("var")?,
                need: self.need()?,
                table: self.u32("table")?,
            },
            2 => Op::And(self.u32s("and operands", MAX_LIST)?),
            3 => Op::Or(self.u32s("or operands", MAX_LIST)?),
            4 => Op::Not(self.u32("not operand")?),
            5 => Op::Quant {
                quant: self.quant()?,
                var: self.u16("var")?,
                kind: self.u32("kind")?,
                cond: self.u32("cond")?,
            },
            6 => Op::Inside {
                sub: self.u16("var")?,
                sup: self.u16("var")?,
                direct: self.bool("direct")?,
            },
            7 => Op::Order {
                a: self.u16("var")?,
                b: self.u16("var")?,
                pos: self.position()?,
            },
            8 => Op::Verb {
                subject: self.u16("var")?,
                object: self.u16("var")?,
                verb: self.u32("verb")?,
                certainty: self.certainty()?,
            },
            9 => Op::Reaches {
                from: self.u16("var")?,
                to: self.u16("var")?,
                via: self.u32("via")?,
                within: self.u16("within")?,
                certainty: self.certainty()?,
            },
            10 => Op::Cmp {
                lhs: self.operand()?,
                op: self.cmp_op()?,
                rhs: self.operand()?,
            },
            11 => Op::MatchRegex {
                subject: self.operand()?,
                pattern: self.u32("pattern")?,
            },
            12 => Op::MatchGlob {
                subject: self.operand()?,
                pattern: self.u32("pattern")?,
            },
            13 => Op::CountCmp {
                var: self.u16("var")?,
                kind: self.u32("kind")?,
                cond: self.u32("cond")?,
                op: self.cmp_op()?,
                limit: self.limit()?,
            },
            14 => Op::Call {
                def: self.u16("def")?,
                args: self.u16s("call arguments", MAX_PARAMS)?,
            },
            tag => return Err(PlanError::BadTag { what: "op", tag }),
        })
    }
}
