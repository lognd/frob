//! The SYS rule declarations of the binding family (binding.md section 6), one derived struct each.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

#[rustfmt::skip]
macro_rules! sys_rule {
    ($name:ident, $id:literal, $slug:literal, $sev:ident, $pol:ident, $measure:literal, $summary:literal, $explain:literal) => {
        #[doc = $summary]
        #[doc = ""]
        #[doc = $explain]
        #[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
        #[rule(
                    id = $id,
                    slug = $slug,
                    family = "SYS",
                    product = "grimble",
                    severity = $sev,
                    tier = Lang,
                    scope = Repo,
                    fix = Manual,
                    polarity = $pol,
                    must_measure = $measure,
                    version = 1,
                    since = "2.0.0"
                )]
        pub struct $name;
    };
}

sys_rule!(
    Sys001,
    "SYS001",
    "sys-unowned",
    Warn,
    Pminus,
    false,
    "An artifact in the walk that no node owns.",
    "Fires when no unit of the artifact has an owner and the artifact hides nothing a selector could claim; reported once per directory. Unresolved when an owner is May only, the artifact has an unseen remainder, or only a symbol selector could own an F0 file. An artifact under a `modeled` selector is SYS005's. Error under `[grimble] strict`."
);
sys_rule!(
    Sys002,
    "SYS002",
    "sys-ambiguous-owner",
    Error,
    Pplus,
    false,
    "Two nodes own one identity at the same specificity.",
    "Fires when two Must rows of the owns selectors tie at the maximal specificity vector and no directive names one of the tied nodes; the owner is Unknown. A tie that includes a May row is Unresolved: it may not be a tie. A tie is never broken by file order or name."
);
sys_rule!(
    Sys003,
    "SYS003",
    "sys-binding-conflict",
    Error,
    Pplus,
    false,
    "Bindings contradict each other or an operand does not resolve.",
    "One rule with a kind in each message: directive-directive (two directives give one identity two nodes), directive-selector (a directive's node is not among the most specific Must selectors), ambiguous-singleton (a shape, runnable or ref names several identities), end-owner (a flow end's code is owned by a node other than the flow's endpoint), dangling-operand and ambiguous-operand (a grimble:binds operand names nothing or several things). Unresolved for end-owner when the owner is only May."
);
sys_rule!(
    Sys004,
    "SYS004",
    "sys-entity-without-code",
    Warn,
    Pminus,
    false,
    "A binding clause matches no code.",
    "Fires per owns, shape or evidence clause (and once per flow whose ends are both empty) when the clause's selector matches no unit and hides none. Suppressed when the selector's path matches no file (MDL005 says so). Unresolved when only May rows or hidden placeholders are found."
);
sys_rule!(
    Sys005,
    "SYS005",
    "sys-unmodeled",
    Warn,
    Pplus,
    true,
    "A public unit in a modeled selector that no node owns.",
    "Opt-in through `[grimble] modeled`: fires for a public unit selected at Must that is foreign. Effects are not consulted yet (no effects query exists). Unresolved when visibility is unknown (F0 and F1 languages) or the owner is May only; with every selected unit unmeasurable the rule examined nothing and is required-Unresolved (vacuous). Error under `[grimble] strict`."
);
sys_rule!(
    Sys009,
    "SYS009",
    "sys-flow-end-unbound",
    Warn,
    Pminus,
    false,
    "One end of a flow binds no code while the other does.",
    "Fires when a flow's producer or consumer end has no row at all, the endpoint node owns code and the other end is not empty too (then it is SYS004). Unresolved when the end holds only May rows or hidden placeholders, or asked for pack inference that cannot run yet."
);
sys_rule!(
    Sys010,
    "SYS010",
    "sys-claim-without-evidence",
    Warn,
    Pminus,
    false,
    "A claim above proof level L1 has no test evidence.",
    "Fires when the evidence rows of a non-assumed claim at L2 or above are empty or none is a test unit. Test units are recognised by path and qualified name (no `test_items` query exists yet). Unresolved when the evidence is May only or hidden."
);
sys_rule!(
    Sys011,
    "SYS011",
    "sys-vmodel-link-broken",
    Error,
    Pminus,
    false,
    "A vmodel ref or runnable resolves to nothing.",
    "Fires when a `ref` or `runnable` of a vmodel matches no unit although its target file is in the walk; a runnable that selects no test unit fires too. Several matches are SYS003 ambiguous-singleton. Unresolved when the target hides units or the match is May only."
);
sys_rule!(
    Sys012,
    "SYS012",
    "sys-excuse-grant",
    Error,
    Pplus,
    false,
    "A node excuses an atom it is also granted.",
    "Reading chosen by binding.md 6.12 and NOT yet confirmed by the owner (binding.md 11.2.1: the ticket title says excuse without matching grant): fires when a node holds both `excuses A` and `may A'` with A and A' equal or one an ancestor of the other in the atom hierarchy. Both are model facts, so the rule is never Unresolved."
);
