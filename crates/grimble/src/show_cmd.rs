//! `show --prose` and `trace`: a planning scenario as numbered English steps, and as its derived
//! path from goals to steps with the paired verification status (grmb-spec 17.7, 14.5, C18).
//!
//! Both verbs re-read the `.grmb` models (as `graph --mermaid` does) and walk each scenario's
//! chains in order, so prose and trace can never disagree with the model about an arm or a bound.

// frob:ticket 01M6PYY41NPK1CHN3RZ9C821MB

use std::collections::BTreeSet;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::config::GrimbleTable;
use grimble_check::{read_models, walk_repo};
use grimble_model::ast::{FileStatus, Item, RefPath};
use grimble_model::model::load_roots;
use grimble_model::plan::{Arm, Chain, Elem, Hop, PlanItem, ScMember, Scenario, Tail};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, config_refusal, locate_root};

/// A scenario found in the models, with the steps that have an `impl` anywhere in its model.
struct Found {
    /// Owning system (empty when the scenario sits outside any system).
    system: String,
    scenario: Scenario,
    /// Step paths (`owner.name`) with an `impl` block.
    bound: BTreeSet<String>,
}

/// Collect scenarios and bound steps from `items`, attributing to the nearest system.
fn collect(
    items: &[Item],
    sys: &str,
    scenarios: &mut Vec<(String, Scenario)>,
    bound: &mut BTreeSet<String>,
    systems: &mut Vec<String>,
) {
    for item in items {
        match item {
            Item::Namespace(n) => collect(&n.items, sys, scenarios, bound, systems),
            Item::Plan(p) => match &**p {
                PlanItem::System(s) => {
                    systems.push(s.name.text.clone());
                    collect(&s.items, &s.name.text, scenarios, bound, systems);
                }
                PlanItem::Scenario(sc) => scenarios.push((sys.to_owned(), sc.clone())),
                PlanItem::Impl(i) => {
                    bound.insert(i.step.dotted());
                }
                _ => {}
            },
            _ => {}
        }
    }
}

/// Every scenario of the repository's models, sorted by system and name.
fn load_scenarios(root: &std::path::Path) -> Result<Vec<Found>, CliError> {
    let entries = walk_repo(root).map_err(check_error)?;
    let table = GrimbleTable::load(root).map_err(|e| config_refusal(&e))?;
    let content = gob_walk::ContentSource::locate(root);
    let model = content.with_reader(|r| read_models(root, &entries, &table, &mut |p| r.read(p)));
    let mut out = Vec::new();
    for loaded in load_roots(&model) {
        let mut scenarios = Vec::new();
        let mut bound = BTreeSet::new();
        let mut systems = Vec::new();
        for f in loaded
            .files
            .iter()
            .filter(|f| f.parsed.status == FileStatus::Parsed)
        {
            collect(
                &f.parsed.items,
                "",
                &mut scenarios,
                &mut bound,
                &mut systems,
            );
        }
        // A scenario outside any system block belongs to the model's first declared system.
        let default = systems
            .first()
            .cloned()
            .unwrap_or_else(|| "system".to_owned());
        out.extend(scenarios.into_iter().map(|(system, scenario)| Found {
            system: if system.is_empty() {
                default.clone()
            } else {
                system
            },
            scenario,
            bound: bound.clone(),
        }));
    }
    out.sort_by(|a, b| (&a.system, &a.scenario.name.text).cmp(&(&b.system, &b.scenario.name.text)));
    tracing::debug!(scenarios = out.len(), "scenarios loaded");
    Ok(out)
}

/// Pick the scenario named `name` or `system.name`; refuse an unknown or ambiguous name.
fn pick(mut all: Vec<Found>, name: &str) -> Result<Found, CliError> {
    all.retain(|f| {
        f.scenario.name.text == name || format!("{}.{}", f.system, f.scenario.name.text) == name
    });
    match all.len() {
        1 => Ok(all.remove(0)),
        0 => Err(CliError::Usage(format!("no scenario named `{name}`"))),
        _ => Err(CliError::Usage(format!(
            "scenario `{name}` is ambiguous; qualify it as `system.name`"
        ))),
    }
}

/// A step path as words: `customer.adds_to_cart` becomes `customer adds to cart`.
fn words(path: &str) -> String {
    path.replace(['.', '_'], " ")
}

/// Render the hop that led into a step as a lead-in phrase.
fn lead(hop: Option<Hop>) -> &'static str {
    match hop {
        Some(Hop::Try) => "If that works, ",
        _ => "",
    }
}

/// Uppercase the first character of `s`.
fn capital(s: &str) -> String {
    let mut c = s.chars();
    c.next()
        .map_or_else(String::new, |f| f.to_uppercase().chain(c).collect())
}

/// One elem as a sentence fragment (`include X` reads as "carry out the scenario X").
fn elem_text(e: &Elem) -> String {
    match e {
        Elem::Step(p) => words(&p.dotted()),
        Elem::Include(p) => format!("carry out the scenario {}", words(&p.dotted())),
    }
}

/// Number one line at `depth` (two spaces per level).
fn line(out: &mut Vec<String>, depth: usize, n: usize, text: &str) {
    out.push(format!("{}{n}. {text}", "  ".repeat(depth)));
}

/// Render the bound `max N [within Q]` as words.
fn bound_words(max: Option<&str>, within: Option<String>) -> String {
    let mut s = match max {
        Some(m) => format!("up to {m} times"),
        None => "an unbounded number of times".to_owned(),
    };
    if let Some(w) = within {
        use std::fmt::Write as _;
        let _ = write!(s, " within {w}");
    }
    s
}

/// Append the numbered prose of `chain` at `depth`.
fn chain_prose(chain: &Chain, depth: usize, out: &mut Vec<String>) {
    let mut n = 0;
    let mut hop = None;
    let step = |out: &mut Vec<String>, e: &Elem, hop: Option<Hop>, n: &mut usize| {
        *n += 1;
        let text = format!("{}{}.", lead(hop), elem_text(e));
        line(out, depth, *n, &capital(&text));
    };
    for (elem, next) in &chain.links {
        step(out, elem, hop, &mut n);
        hop = Some(*next);
    }
    match &chain.tail {
        Tail::Match { elem, arms } => {
            step(out, elem, hop, &mut n);
            arms_prose(arms, depth, n + 1, out);
        }
        Tail::Open(elem) => step(out, elem, hop, &mut n),
        Tail::EndOk(_) => line(out, depth, n + 1, "The scenario ends successfully."),
        Tail::EndErr(v) => line(
            out,
            depth,
            n + 1,
            &format!("The scenario ends with the error {}.", words(&v.text)),
        ),
        Tail::Sorry(_) => line(out, depth, n + 1, "This part is not yet decided (sorry)."),
        Tail::Retry {
            step,
            max,
            within,
            otherwise,
            ..
        } => {
            let bound = bound_words(
                max.as_ref().map(|m| m.value.as_str()),
                within.as_ref().map(|q| format!("{}{}", q.number, q.unit)),
            );
            line(
                out,
                depth,
                n + 1,
                &format!("Retry {} {bound}.", words(&step.dotted())),
            );
            if let Some(c) = otherwise {
                line(out, depth, n + 2, "If it still fails:");
                chain_prose(c, depth + 1, out);
            }
        }
    }
}

/// Append one "If ..." line per arm, each followed by its nested chain.
fn arms_prose(arms: &[Arm], depth: usize, mut n: usize, out: &mut Vec<String>) {
    for arm in arms {
        let pat = arm.pattern.written();
        let cond = if pat == "_" {
            "In any other case:".to_owned()
        } else {
            format!("If {}:", words(&pat))
        };
        line(out, depth, n, &cond);
        chain_prose(&arm.chain, depth + 1, out);
        n += 1;
    }
}

/// The numbered English steps of a scenario.
fn scenario_prose(sc: &Scenario) -> Vec<String> {
    let mut out = Vec::new();
    for m in &sc.members {
        match m {
            ScMember::Chain(_, c) => chain_prose(c, 0, &mut out),
            ScMember::Handle(h) => {
                out.push("Whenever a step fails:".to_owned());
                arms_prose(&h.arms, 1, 1, &mut out);
            }
            ScMember::Clause(_) => {}
        }
    }
    out
}

/// Step paths used by `chain`, in order, nested arms and `else` chains included.
fn chain_steps(chain: &Chain, out: &mut Vec<String>) {
    let mut push = |e: &Elem| {
        let p = e.path().dotted();
        if !out.contains(&p) {
            out.push(p);
        }
    };
    chain.links.iter().for_each(|(e, _)| push(e));
    match &chain.tail {
        Tail::Match { elem, arms } => {
            push(elem);
            for a in arms {
                chain_steps(&a.chain, out);
            }
        }
        Tail::Open(e) => push(e),
        Tail::Retry {
            otherwise: Some(c), ..
        } => chain_steps(c, out),
        _ => {}
    }
}

/// The steps a scenario uses, in first-use order.
fn scenario_steps(sc: &Scenario) -> Vec<String> {
    let mut out = Vec::new();
    for m in &sc.members {
        match m {
            ScMember::Chain(_, c) => chain_steps(c, &mut out),
            ScMember::Handle(h) => h.arms.iter().for_each(|a| chain_steps(&a.chain, &mut out)),
            ScMember::Clause(_) => {}
        }
    }
    out
}

/// `show` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ShowArgs {
    #[arg(
        long,
        required = true,
        help = "Render the scenario as numbered English steps"
    )]
    prose: bool,
    #[arg(help = "A scenario `name` or `system.name`")]
    scenario: String,
}

/// Render a planning scenario as prose for PMs and designers.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "show",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Show {
    scenario: String,
}

/// The prose of one scenario.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ShowData {
    /// The scenario as qualified (`system.name`).
    pub scenario: String,
    /// The numbered English steps, one line each (nested arms indented).
    pub prose: Vec<String>,
}

impl Command for Show {
    type Data = ShowData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ShowArgs>(cmd)
    }

    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ShowArgs>(matches)?;
        Ok(Self {
            scenario: a.scenario,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ShowData> {
        let found = pick(load_scenarios(&locate_root(&ctx.cwd))?, &self.scenario)?;
        let prose = scenario_prose(&found.scenario);
        tracing::info!(scenario = %self.scenario, lines = prose.len(), "scenario prose rendered");
        let data = ShowData {
            scenario: format!("{}.{}", found.system, found.scenario.name.text),
            prose: prose.clone(),
        };
        Ok(Payload::new(data).with_rendered(prose))
    }
}

/// `trace` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TraceArgs {
    #[arg(help = "A scenario `name` or `system.name`")]
    scenario: String,
}

/// Show a scenario's derived path from goals to steps with verification status.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "trace",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Trace {
    scenario: String,
}

/// One step on a scenario's path.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TraceStep {
    /// The step path (`owner.name`).
    pub step: String,
    /// True when an `impl` block binds the step to code.
    pub bound: bool,
}

/// The derived path of one scenario.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TraceData {
    /// The scenario as qualified (`system.name`).
    pub scenario: String,
    /// The goals the scenario realizes.
    pub goals: Vec<String>,
    /// The steps in first-use order, each with its binding.
    pub steps: Vec<TraceStep>,
    /// Number of `verified_by` clauses on the scenario.
    pub verified_by: usize,
    /// `verified` (tests and every step bound), `partial` or `unverified`.
    pub status: String,
}

/// Build the trace of `found`.
fn trace_of(found: &Found) -> TraceData {
    let sc = &found.scenario;
    let steps: Vec<TraceStep> = scenario_steps(sc)
        .into_iter()
        .map(|step| TraceStep {
            bound: found.bound.contains(&step),
            step,
        })
        .collect();
    let verified_by = sc
        .members
        .iter()
        .filter(|m| {
            matches!(m, ScMember::Clause(c)
                if matches!(c.kind, grimble_model::plan::PClauseKind::Verified(_)))
        })
        .count();
    let all_bound = steps.iter().all(|s| s.bound);
    let status = match (verified_by > 0, all_bound) {
        (true, true) => "verified",
        (false, false) => "unverified",
        _ => "partial",
    };
    TraceData {
        scenario: format!("{}.{}", found.system, sc.name.text),
        goals: sc.realizes.iter().map(RefPath::dotted).collect(),
        steps,
        verified_by,
        status: status.to_owned(),
    }
}

impl Command for Trace {
    type Data = TraceData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<TraceArgs>(cmd)
    }

    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TraceArgs>(matches)?;
        Ok(Self {
            scenario: a.scenario,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<TraceData> {
        let found = pick(load_scenarios(&locate_root(&ctx.cwd))?, &self.scenario)?;
        let data = trace_of(&found);
        tracing::info!(scenario = %data.scenario, status = %data.status, "scenario traced");
        let mut lines = vec![format!("{} [{}]", data.scenario, data.status)];
        lines.extend(data.goals.iter().map(|g| format!("  goal {g}")));
        lines.extend(data.steps.iter().map(|s| {
            format!(
                "    step {} {}",
                s.step,
                if s.bound { "(bound)" } else { "(unbound)" }
            )
        }));
        lines.push(format!("  verified_by clauses: {}", data.verified_by));
        Ok(Payload::new(data).with_rendered(lines))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MODEL: &str = "grimble = \"2\";\nmodule m;\nsystem s {\n  actor customer : human;\n}\n\
step customer.pays : { ok, declined };\nstep system.confirms;\n\
scenario checkout {\n  customer.pays => {\n    declined => retry customer.pays max 3;\n    ok => system.confirms -> end ok;\n  }\n  verified_by \"t.py::t\";\n}\n";

    fn found() -> Found {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(
            dir.path().join("grimble.toml"),
            "[grimble]\nmodels = [\"m.grmb\"]\n",
        )
        .unwrap();
        std::fs::write(dir.path().join("m.grmb"), MODEL).unwrap();
        pick(load_scenarios(dir.path()).expect("load"), "checkout").expect("pick")
    }

    // frob:ticket 01M6PYY41NPK1CHN3RZ9C821MB
    // frob:tests crates/grimble/src/show_cmd.rs::Show
    #[test]
    fn prose_numbers_steps_and_arms() {
        let prose = scenario_prose(&found().scenario);
        assert_eq!(prose[0], "1. Customer pays.");
        assert!(prose.iter().any(|l| l == "2. If declined:"), "{prose:?}");
        assert!(
            prose
                .iter()
                .any(|l| l.contains("Retry customer pays up to 3 times."))
        );
        assert!(
            prose
                .iter()
                .any(|l| l.contains("The scenario ends successfully."))
        );
    }

    // frob:ticket 01M6PYY41NPK1CHN3RZ9C821MB
    // frob:tests crates/grimble/src/show_cmd.rs::Trace
    #[test]
    fn trace_reports_steps_and_status() {
        let t = trace_of(&found());
        assert_eq!(t.scenario, "s.checkout");
        assert_eq!(t.verified_by, 1);
        assert_eq!(t.status, "partial");
        assert_eq!(t.steps.len(), 2);
    }
}
