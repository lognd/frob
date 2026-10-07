//! Per-crate rule indexes and their compile-time uniqueness check (D107, section 4).
//!
//! Each rule crate's generated `src/rules/mod.rs` exports an [`RuleIndex`]; a product lists its
//! crates with `gob_check::product_rules!`, and [`assert_unique`] runs in `const` context at the
//! crate, the product and the all-products level, so a duplicate id, slug, renamed id or retired
//! id is a compile error that names both declarations.

use crate::decl::{Emitted, FileRule, RepoRule, RuleDef, run_file, run_repo};

/// One crate's rules: the generated list plus its renamed and retired ids.
#[derive(Debug)]
pub struct RuleIndex {
    /// Name of the crate that owns the rules (`CARGO_PKG_NAME`).
    pub krate: &'static str,
    /// Every rule the crate declares, sorted by file stem.
    pub metas: &'static [&'static RuleDef],
    /// `(old id, new id)` pairs of rules renamed; the old id may never be reused.
    pub renamed: &'static [(&'static str, &'static str)],
    /// Ids of deleted rules; they may never be reused.
    pub retired: &'static [&'static str],
}

/// Which namespace and role a name has inside an index.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Kind {
    Id,
    Slug,
    Renamed,
    Retired,
}

impl Kind {
    const fn label(self) -> &'static str {
        match self {
            Kind::Id => "rule id",
            Kind::Slug => "rule slug",
            Kind::Renamed => "renamed id (old name)",
            Kind::Retired => "retired id",
        }
    }

    /// Ids, renamed and retired ids share one namespace; slugs have their own.
    const fn is_id_space(self) -> bool {
        !matches!(self, Kind::Slug)
    }
}

/// One name to compare, with where it was declared.
#[derive(Clone, Copy)]
struct Entry<'a> {
    kind: Kind,
    text: &'a str,
    krate: &'a str,
    file: &'a str,
    line: u32,
}

const fn slots(ix: &RuleIndex) -> usize {
    ix.metas.len() * 2 + ix.renamed.len() + ix.retired.len()
}

const fn entry(ix: &RuleIndex, n: usize) -> Entry<'_> {
    let m = ix.metas.len() * 2;
    if n < m {
        let def = ix.metas[n / 2];
        let kind = if n.is_multiple_of(2) {
            Kind::Id
        } else {
            Kind::Slug
        };
        let text = if n.is_multiple_of(2) {
            def.id
        } else {
            def.slug
        };
        return Entry {
            kind,
            text,
            krate: ix.krate,
            file: def.file,
            line: def.line,
        };
    }
    let n = n - m;
    if n < ix.renamed.len() {
        return Entry {
            kind: Kind::Renamed,
            text: ix.renamed[n].0,
            krate: ix.krate,
            file: "retired.rs",
            line: 0,
        };
    }
    Entry {
        kind: Kind::Retired,
        text: ix.retired[n - ix.renamed.len()],
        krate: ix.krate,
        file: "retired.rs",
        line: 0,
    }
}

const fn str_eq(a: &str, b: &str) -> bool {
    let (a, b) = (a.as_bytes(), b.as_bytes());
    if a.len() != b.len() {
        return false;
    }
    let mut i = 0;
    while i < a.len() {
        if a[i] != b[i] {
            return false;
        }
        i += 1;
    }
    true
}

const fn clash(a: &Entry<'_>, b: &Entry<'_>) -> bool {
    a.kind.is_id_space() == b.kind.is_id_space() && str_eq(a.text, b.text)
}

/// Fixed-size message builder: `panic!` in `const` takes one `&str`, so the text is assembled here.
struct Msg {
    bytes: [u8; 768],
    len: usize,
}

impl Msg {
    const fn new() -> Self {
        Self {
            bytes: [0; 768],
            len: 0,
        }
    }

    const fn push(mut self, s: &str) -> Self {
        let s = s.as_bytes();
        let mut i = 0;
        while i < s.len() && self.len < self.bytes.len() {
            self.bytes[self.len] = s[i];
            self.len += 1;
            i += 1;
        }
        self
    }

    const fn push_u32(mut self, mut n: u32) -> Self {
        let mut digits = [0u8; 10];
        let mut count = 0;
        loop {
            digits[count] = b'0' + (n % 10) as u8;
            count += 1;
            n /= 10;
            if n == 0 {
                break;
            }
        }
        while count > 0 && self.len < self.bytes.len() {
            count -= 1;
            self.bytes[self.len] = digits[count];
            self.len += 1;
        }
        self
    }

    const fn fail(self) -> ! {
        let (head, _) = self.bytes.split_at(self.len);
        match core::str::from_utf8(head) {
            Ok(text) => panic!("{}", text),
            Err(_) => panic!("duplicate rule name (message was not valid UTF-8)"),
        }
    }
}

const fn describe(msg: Msg, e: &Entry<'_>) -> Msg {
    let msg = msg
        .push(e.kind.label())
        .push(" in crate `")
        .push(e.krate)
        .push("` (")
        .push(e.file);
    if e.line == 0 {
        msg.push(")")
    } else {
        msg.push(":").push_u32(e.line).push(")")
    }
}

/// Fail compilation (or panic at run time) when two names in `groups` collide.
///
/// Names are rule ids, slugs, renamed ids and retired ids; ids, renamed and retired ids share one
/// namespace, slugs another. `scope` ("crate", "product Frob", "all products") is printed in the
/// message, which names both declarations.
///
/// # Panics
/// Panics (a compile error when evaluated in a `const`) on the first collision found.
pub const fn assert_unique(scope: &str, groups: &[&[&RuleIndex]]) {
    let mut ga = 0;
    while ga < groups.len() {
        let mut ia = 0;
        while ia < groups[ga].len() {
            let a_ix = groups[ga][ia];
            let mut sa = 0;
            while sa < slots(a_ix) {
                let a = entry(a_ix, sa);
                let mut gb = ga;
                while gb < groups.len() {
                    let mut ib = if gb == ga { ia } else { 0 };
                    while ib < groups[gb].len() {
                        let b_ix = groups[gb][ib];
                        let mut sb = if gb == ga && ib == ia { sa + 1 } else { 0 };
                        while sb < slots(b_ix) {
                            let b = entry(b_ix, sb);
                            if clash(&a, &b) {
                                let msg = Msg::new()
                                    .push("duplicate `")
                                    .push(a.text)
                                    .push("` within ")
                                    .push(scope)
                                    .push(": ");
                                let msg = describe(msg, &a).push(" and ");
                                describe(msg, &b).fail();
                            }
                            sb += 1;
                        }
                        ib += 1;
                    }
                    gb += 1;
                }
                sa += 1;
            }
            ia += 1;
        }
        ga += 1;
    }
}

/// A bound file rule: host and file text in, findings out.
pub type FileFn<P> = dyn Fn(&P, &str) -> Vec<Emitted> + Send + Sync;

/// A bound repo rule: host in, findings out.
pub type RepoFn<P> = dyn Fn(&P) -> Vec<Emitted> + Send + Sync;

/// Evaluation body of a bound rule, generic over the product host `P`.
pub enum Body<P: ?Sized> {
    /// Judges one file: `(host, file text)`.
    File(Box<FileFn<P>>),
    /// Judges the repository.
    Repo(Box<RepoFn<P>>),
}

/// A rule bound to a product host: its declaration plus a runnable body.
pub struct BoundRule<P: ?Sized> {
    /// The rule's static description.
    pub def: &'static RuleDef,
    /// What to run.
    pub body: Body<P>,
}

impl<P: ?Sized + 'static> BoundRule<P> {
    /// Bind a `scope = File` rule; compiles only when the host implements what the rule needs.
    pub fn file<R: FileRule<P> + Send + Sync + 'static>(rule: R) -> Self {
        tracing::trace!(rule = R::DEF.id, "bound file rule");
        Self {
            def: R::DEF,
            body: Body::File(Box::new(move |host, text| run_file(&rule, host, text))),
        }
    }

    /// Bind a `scope = Repo` rule; compiles only when the host implements what the rule needs.
    pub fn repo<R: RepoRule<P> + Send + Sync + 'static>(rule: R) -> Self {
        tracing::trace!(rule = R::DEF.id, "bound repo rule");
        Self {
            def: R::DEF,
            body: Body::Repo(Box::new(move |host| run_repo(&rule, host))),
        }
    }
}

impl<P: ?Sized> std::fmt::Debug for BoundRule<P> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BoundRule")
            .field("def", &self.def.id)
            .finish_non_exhaustive()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const fn def(id: &'static str, slug: &'static str, file: &'static str, line: u32) -> RuleDef {
        RuleDef {
            id,
            slug,
            file,
            line,
            ..RuleDef::POISONED
        }
    }

    const A1: RuleDef = def("COV001", "untested", "src/rules/cov001.rs", 4);
    const A2: RuleDef = def("COV002", "orphan", "src/rules/cov002.rs", 9);
    const B1: RuleDef = def("NEAT001", "tidy", "src/rules/neat001.rs", 5);
    const SAME_ID: RuleDef = def("COV001", "elsewhere", "src/rules/cov001.rs", 3);
    const SAME_SLUG: RuleDef = def("NEAT002", "untested", "src/rules/neat002.rs", 6);

    const fn ix(
        krate: &'static str,
        metas: &'static [&'static RuleDef],
        renamed: &'static [(&'static str, &'static str)],
        retired: &'static [&'static str],
    ) -> RuleIndex {
        RuleIndex {
            krate,
            metas,
            renamed,
            retired,
        }
    }

    static ALPHA: RuleIndex = ix("alpha", &[&A1, &A2], &[], &[]);
    static BETA: RuleIndex = ix("beta", &[&B1], &[("COV009", "COV002")], &["OLD001"]);

    #[test]
    fn distinct_names_pass_in_one_group_and_across_groups() {
        assert_unique("crate", &[&[&ALPHA, &BETA]]);
        assert_unique("all products", &[&[&ALPHA], &[&BETA]]);
    }

    #[test]
    fn the_same_text_as_slug_and_as_retired_id_is_not_a_clash() {
        static GAMMA: RuleIndex = ix("gamma", &[&B1], &[], &["tidy"]);
        assert_unique("crate", &[&[&GAMMA]]);
    }

    #[test]
    #[should_panic(expected = "duplicate `COV001` within crate: rule id in crate `solo`")]
    fn a_duplicate_id_inside_one_crate_panics() {
        static SOLO: RuleIndex = ix("solo", &[&A1, &SAME_ID], &[], &[]);
        assert_unique("crate", &[&[&SOLO]]);
    }

    #[test]
    #[should_panic(
        expected = "duplicate `untested` within product Demo: rule slug in crate `alpha`"
    )]
    fn a_duplicate_slug_across_crates_of_a_product_names_both() {
        static OTHER: RuleIndex = ix("other", &[&SAME_SLUG], &[], &[]);
        assert_unique("product Demo", &[&[&ALPHA, &OTHER]]);
    }

    #[test]
    #[should_panic(expected = "and rule id in crate `second` (src/rules/cov001.rs:3)")]
    fn the_message_names_the_second_declaration_with_its_line() {
        static FIRST: RuleIndex = ix("first", &[&A1], &[], &[]);
        static SECOND: RuleIndex = ix("second", &[&SAME_ID], &[], &[]);
        assert_unique("product Demo", &[&[&FIRST, &SECOND]]);
    }

    #[test]
    #[should_panic(expected = "renamed id (old name) in crate `ren`")]
    fn a_renamed_old_id_may_not_be_reused() {
        static REN: RuleIndex = ix("ren", &[&A1], &[("COV001", "COV009")], &[]);
        assert_unique("crate", &[&[&REN]]);
    }

    #[test]
    #[should_panic(expected = "retired id in crate `gone`")]
    fn a_retired_id_may_not_be_reused_in_another_crate() {
        static GONE: RuleIndex = ix("gone", &[], &[], &["COV002"]);
        assert_unique("all products", &[&[&ALPHA], &[&GONE]]);
    }

    #[test]
    #[should_panic(expected = "all products")]
    fn a_duplicate_across_products_panics() {
        static COPY: RuleIndex = ix("copy", &[&A2], &[], &[]);
        assert_unique("all products", &[&[&ALPHA], &[&COPY]]);
    }
}
