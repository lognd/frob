//! [`RuleSet`]: a product's declared rules (`RuleDef`s), bound to its host and ready to run.
//!
//! A product builds one from its `product_rules!` list with [`RuleSet::bind`]; the pipeline runs
//! exactly that set (D107, `rule-authoring.md` section 4), so a listed rule is run by
//! construction and nothing is wired into groups by hand. The set erases the host type: each
//! body is closed over a function from the product and its snapshot to the host the rule judges.

use gob_rules::{Body, BoundRule, Emitted, FileInterner, Finding, RuleDef};

use crate::product::{Product, Snapshot};

/// A file rule's runner: product, snapshot and file text in, emissions out.
pub(crate) type FileRun<P> = Box<dyn Fn(&P, &Snapshot<P>, &str) -> Vec<Emitted>>;

/// A repo rule's runner: product and snapshot in, emissions out.
pub(crate) type RepoRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> Vec<Emitted>>;

/// A relay rule's runner: product, snapshot and path interner in, whole findings out.
pub(crate) type RelayRun<P> = Box<dyn Fn(&P, &Snapshot<P>, &mut FileInterner) -> Vec<Finding>>;

/// A rule's product-fact applicability: the reason it cannot apply to this product, if any.
pub(crate) type InapplicableRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> Option<String>>;

/// A repo rule's subject counter; `None` when the rule reports no count.
pub(crate) type SubjectsRun<P> = Box<dyn Fn(&P, &Snapshot<P>) -> Option<usize>>;

/// How a declared rule runs.
pub(crate) enum Run<P: Product> {
    /// Judges one file at a time.
    File(FileRun<P>),
    /// Judges the repository.
    Repo(RepoRun<P>),
    /// Relays findings a sibling stage already computed (`body = relay`).
    Relay(RelayRun<P>),
    /// Emitted by a pipeline stage the product already runs; the pipeline only knows the declaration.
    Stage,
}

/// One declared rule of a product, with its erased runner.
pub(crate) struct RuleEntry<P: Product> {
    /// The static declaration.
    pub def: &'static RuleDef,
    /// The rule's own product-fact applicability: why it cannot apply to this product, if so.
    pub inapplicable: InapplicableRun<P>,
    /// Subject counter of a repo, relay or stage rule.
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
                Body::Relay(f) => Run::Relay(Box::new(move |p, s, files| f(host(p, s), files))),
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
    pub fn stage(self, def: &'static RuleDef) -> Self {
        self.push_stage(def, Box::new(|_, _| None), None)
    }

    /// Like [`RuleSet::stage`], with the product fact `inapplicable` reports when the rule cannot apply.
    ///
    /// The reason lands in the report's fidelity section as `not_applicable`, and the stage's
    /// findings for the rule are not requested (`wanted` filtering is unchanged).
    #[must_use]
    pub fn stage_when(
        self,
        def: &'static RuleDef,
        inapplicable: impl Fn(&P, &Snapshot<P>) -> Option<String> + 'static,
    ) -> Self {
        self.push_stage(def, Box::new(inapplicable), None)
    }

    /// Like [`RuleSet::stage`], with a `subjects` counter so a `must_measure` stage rule that
    /// examined zero subjects is reported Unresolved instead of passing silently.
    #[must_use]
    pub fn stage_counted(
        self,
        def: &'static RuleDef,
        subjects: impl Fn(&P, &Snapshot<P>) -> usize + 'static,
    ) -> Self {
        self.push_stage(
            def,
            Box::new(|_, _| None),
            Some(Box::new(move |p, s| Some(subjects(p, s)))),
        )
    }

    fn push_stage(
        mut self,
        def: &'static RuleDef,
        inapplicable: InapplicableRun<P>,
        subjects: Option<SubjectsRun<P>>,
    ) -> Self {
        tracing::debug!(rule = def.id, "stage-emitted rule joins the product's set");
        self.entries.push(RuleEntry {
            def,
            inapplicable,
            subjects,
            run: Run::Stage,
        });
        self
    }

    /// The declaration of every rule in the set.
    pub fn defs(&self) -> impl Iterator<Item = &'static RuleDef> + '_ {
        self.entries.iter().map(|e| e.def)
    }
}
