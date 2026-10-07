//! [`RuleSet`]: a product's declared rules (`RuleDef`s), bound to its host and ready to run.
//!
//! A product builds one from its `product_rules!` list with [`RuleSet::bind`]; the pipeline runs
//! exactly that set (D107, `rule-authoring.md` section 4), so a listed rule is run by
//! construction and nothing is wired into groups by hand. The set erases the host type: each
//! body is closed over a function from the product and its snapshot to the host the rule judges.

use gob_rules::{Body, BoundRule, Emitted, RuleDef};

use crate::product::{Product, Snapshot};

/// A file rule's runner: product, snapshot and file text in, emissions out.
pub(crate) type FileRun<P> = Box<dyn Fn(&P, &Snapshot<P>, &str) -> Vec<Emitted>>;

/// A repo rule's runner: product and snapshot in, emissions out.
pub(crate) type RepoRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> Vec<Emitted>>;

/// A rule's product-fact applicability: the reason it cannot apply to this product, if any.
pub(crate) type InapplicableRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> Option<String>>;

/// A `must_measure` repo rule's subject counter.
pub(crate) type SubjectsRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> usize>;

/// How a declared rule runs.
pub(crate) enum Run<P: Product> {
    /// Judges one file at a time.
    File(FileRun<P>),
    /// Judges the repository.
    Repo(RepoRun<P>),
    /// Emitted by a pipeline stage the product already runs; the pipeline only knows the declaration.
    Stage,
}

/// One declared rule of a product, with its erased runner.
pub(crate) struct RuleEntry<P: Product> {
    /// The static declaration.
    pub def: &'static RuleDef,
    /// The rule's own product-fact applicability: why it cannot apply to this product, if so.
    pub inapplicable: InapplicableRun<P>,
    /// Subject counter of a `must_measure` repo rule.
    pub subjects: Option<SubjectsRun<P>>,
    /// What to run.
    pub run: Run<P>,
}

/// The declared rules of one product; empty until its rule crates are migrated.
pub struct RuleSet<P: Product> {
    pub(crate) entries: Vec<RuleEntry<P>>,
}

impl<P: Product> Default for RuleSet<P> {
    fn default() -> Self {
        Self::new()
    }
}

impl<P: Product> RuleSet<P> {
    /// A set that holds no declared rule.
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
        }
    }

    /// Add the rules `bound` (usually `product_rules!`'s `rules()`), judging the host `host` yields.
    ///
    /// `host` maps the product and its snapshot to the host the rules were bound against, for
    /// example `|_, snap| &snap.inputs as &dyn ObligationHost`.
    #[must_use]
    pub fn bind<H: ?Sized + 'static>(
        mut self,
        bound: Vec<BoundRule<H>>,
        host: impl for<'a> Fn(&'a P, &'a Snapshot<P>) -> &'a H + Copy + 'static,
    ) -> Self {
        for rule in bound {
            tracing::debug!(rule = rule.def.id, "declared rule joins the product's set");
            let BoundRule {
                def,
                body,
                inapplicable,
                subjects,
            } = rule;
            let run = match body {
                Body::File(f) => Run::File(Box::new(move |p, s, text| f(host(p, s), text))),
                Body::Repo(f) => Run::Repo(Box::new(move |p, s| f(host(p, s)))),
            };
            self.entries.push(RuleEntry {
                def,
                inapplicable: Box::new(move |p, s| inapplicable(host(p, s))),
                subjects: subjects
                    .map(|count| -> SubjectsRun<P> { Box::new(move |p, s| count(host(p, s))) }),
                run,
            });
        }
        self
    }

    /// Add a rule a pipeline stage emits (tool parsers, the sibling model check): declared, not run.
    #[must_use]
    pub fn stage(mut self, def: &'static RuleDef) -> Self {
        tracing::debug!(rule = def.id, "stage-emitted rule joins the product's set");
        self.entries.push(RuleEntry {
            def,
            inapplicable: Box::new(|_, _| None),
            subjects: None,
            run: Run::Stage,
        });
        self
    }

    /// The declaration of every rule in the set.
    pub fn defs(&self) -> impl Iterator<Item = &'static RuleDef> + '_ {
        self.entries.iter().map(|e| e.def)
    }
}
