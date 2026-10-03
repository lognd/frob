//! Output-equivalence snapshots: the stack-safe printer, symref pass, scope derivation, free
//! variables and facet streams must reproduce byte-for-byte what the recursive versions produced.
//!
//! The expected digests in `tests/snapshots/equivalence.txt` were taken from the recursive
//! implementation before the conversion (01M3Z8NVCBM9KXN5ZY97QWX8P1). Regenerate deliberately
//! with `GOB_IR_WRITE_SNAPSHOT=1`.
#![allow(clippy::many_single_char_names, reason = "terse generators")]

mod support;

use std::fmt::Write as _;

use gob_ir::{Digest, Facet, GroupOrder, Model, NodeId, Operator, PrintOpts, Term};
use support::B;

/// A tiny deterministic generator (xorshift64*), so the corpus never changes.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

const VARS: [&str; 4] = ["v0", "v1", "v2", "v3"];

fn var(r: &mut Rng) -> &'static str {
    VARS[r.below(4) as usize]
}

fn kids(r: &mut Rng, b: &mut B, depth: u32, max: u64) -> Vec<NodeId> {
    let n = r.below(max + 1);
    (0..n).map(|_| gen_node(r, b, depth - 1)).collect()
}

fn gen_node(r: &mut Rng, b: &mut B, depth: u32) -> NodeId {
    let pick = if depth == 0 { r.below(5) } else { r.below(14) };
    match pick {
        0 | 1 => b.reference(if r.below(5) == 0 { "free0" } else { var(r) }),
        2 => b.lit(&format!("l{}", r.below(50))),
        3 => b.node(Operator::comment("note"), &[]),
        4 => b.doc("docs"),
        5 | 6 => {
            let ks = kids(r, b, depth, 3);
            let nb = r.below(3) as usize;
            let bs: Vec<&str> = (0..nb).map(|_| var(r)).collect();
            let name = format!("u{}", r.below(4));
            b.unit("function", &name, &bs, &ks)
        }
        7 => {
            let mut all = vec![gen_node(r, b, depth - 1)];
            if r.below(2) == 0 {
                all.push(gen_node(r, b, depth - 1));
            }
            let spec = b.spec(Operator::bind("let", "val")).binders(&[var(r)]);
            b.add(spec, &all)
        }
        8 | 9 => {
            let ks = kids(r, b, depth, 3);
            let h = b.reference(var(r));
            let mut all = vec![h];
            all.extend(ks);
            b.node(Operator::apply("call"), &all)
        }
        10 => {
            let ks = kids(r, b, depth, 2);
            b.sig(Operator::group(GroupOrder::Sequence), &ks)
        }
        11 => {
            let ks = kids(r, b, depth, 2);
            b.node(Operator::anon("closure"), &ks)
        }
        12 => b.node(Operator::hole("todo"), &[]),
        _ => b.node(Operator::opaque("macro", b"\x00\"x"), &[]),
    }
}

fn gen_term(seed: u64) -> Term {
    let mut r = Rng(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1);
    let mut b = B::new("gen.rs", "rust");
    let ks = kids(&mut r, &mut b, 5, 4);
    let root = b.file_unit(&ks);
    b.finish(root)
}

/// Everything observable that the conversion must preserve, folded into one digest.
fn fingerprint(term: Term) -> String {
    let mut s = String::new();
    let root = term.root();
    for opts in [PrintOpts::ALPHA, PrintOpts::FULL] {
        let _ = writeln!(s, "{}", term.print_with(root, opts));
    }
    for id in term.ids() {
        let _ = writeln!(s, "{id} {}", term.print_alpha(id));
        let _ = writeln!(s, "{:?}", term.symref_of(id));
        let _ = writeln!(s, "{:?}", term.free_vars(id));
        if term.node(id).op().is_unit_like() {
            for f in Facet::ALL {
                let _ = writeln!(
                    s,
                    "{f:?} {:?} {:?}",
                    term.facet_stream(id, f),
                    term.facet_digest(id, f)
                );
            }
        }
    }
    let model = Model::lexical(term);
    let _ = writeln!(s, "{}", model.graph_digest());
    let _ = writeln!(s, "{}", model.scopes().canonical_stream());
    for id in model.term().ids() {
        let _ = writeln!(s, "{id} {:?}", model.resolve_node(id));
    }
    Digest::of("equivalence", s.as_bytes()).to_hex()
}

#[test]
fn outputs_match_the_recursive_implementation() {
    let got: String = (0..200u64)
        .map(|seed| format!("{}\n", fingerprint(gen_term(seed))))
        .collect();
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/snapshots/equivalence.txt"
    );
    if std::env::var_os("GOB_IR_WRITE_SNAPSHOT").is_some() {
        std::fs::write(path, &got).unwrap();
        return;
    }
    let want = std::fs::read_to_string(path).unwrap();
    assert_eq!(
        got, want,
        "printer/symref/scope output drifted from the recorded snapshot"
    );
}
