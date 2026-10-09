//! The SYS rule declarations of the binding family (binding.md section 6), one derived struct each.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

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
    Sys006,
    "SYS006",
    "sys-contract-skew",
    Error,
    P0,
    true,
    "The two ends of an acked flow disagree on the Contract facet.",
    "Fires when the producer and consumer end of a flow recorded in grimble.lock have Contract digests that differ from each other now, or either differs from its acked digest (that end is ahead of its ack; the other is behind). Unresolved when either end is F0 or F1, opaque in the Contract facet, or bound only at May. A flow with an end not bound now is SYS009's. The Contract facet of the end symbols stands in for the shape contract until the lock records it; `versioning compat` does not yet lower the severity."
);
sys_rule!(
    Sys007,
    "SYS007",
    "sys-changed-since-ack",
    Error,
    P0,
    true,
    "An acked identity changed since its ack.",
    "One finding per lock entry with a kind in the message: facet (a Sig, Body, Doc or Attr digest differs from the acked one), gone (the anchor is absent and no rename candidate exists) and scheme (the lock was written under another format version or digest scheme; every entry is stale and `ack --all --reason` re-attests it). Unresolved when a facet is not Exact (F0 or F1 language, a parse hole) or a gone anchor may live on in a unit whose Body is hidden. An entry SYS008 reports is not reported here."
);
sys_rule!(
    Sys008,
    "SYS008",
    "sys-renamed",
    Advisory,
    P0,
    false,
    "An acked identity vanished and its Body appears under a new name.",
    "Advisory: a lock entry whose anchor is gone while an unacked identity of the same language has an equal, non-trivial Body digest (at least 12 canonical atoms). The pairing is May even when unique; every candidate is listed and none is picked. Run `grimble ack --rename OLD NEW` to carry the entry. Unresolved, once, when a unit hides its Body and could hold a renamed identity."
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
    Sys013,
    "SYS013",
    "sys-undeclared-flow",
    Error,
    Pplus,
    false,
    "An import or call edge between two owners with no flow between them.",
    "Fires once per ordered pair of nodes when a Must import or call edge (TS, TSX, JSX component use, Python, C#, Rust) runs from code owned at Must by one node to code owned at Must by another and the model declares no flow between the two nodes in either direction. Edges into unowned (foreign) code or outside the repository are not checked. Unresolved when an edge is May or has no known target, or an end is owned only at May."
);

#[rustfmt::skip]
macro_rules! cap_rule {
    ($name:ident, $id:literal, $slug:literal, $sev:ident, $pol:ident, $summary:literal, $explain:literal) => {
        #[doc = $summary]
        #[doc = ""]
        #[doc = $explain]
        #[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
        #[rule(
                    id = $id,
                    slug = $slug,
                    family = "CAP",
                    product = "grimble",
                    severity = $sev,
                    tier = Lang,
                    scope = Repo,
                    fix = Manual,
                    polarity = $pol,
                    must_measure = false,
                    version = 1,
                    since = "2.0.0"
                )]
        pub struct $name;
    };
}

cap_rule!(
    Cap001,
    "CAP001",
    "cap-undeclared",
    Error,
    Pplus,
    "Code a node owns uses a capability atom the node does not grant.",
    "Deny by default (binding.md 7.2 item 3): fires once per node and atom when a call in Must-owned code matches the callee vocabulary of the atom for its language and no `may` of the node covers it (the atom itself or its parent, at the grant's `at` files). One finding per node and atom, anchored at the node, so an `accept CAP001` inside the node suppresses it. Unresolved when the code is owned only at May. An excuse never hides a use (CAP004 is not implemented yet)."
);
cap_rule!(
    Cap002,
    "CAP002",
    "cap-declared-unused",
    Warn,
    Pminus,
    "A node grants a capability atom that no code it owns uses.",
    "Fires per `may` clause when every file the node owns is fully seen, every language present has a detector for the atom and no use is observed in the grant's scope (binding.md 7.2 item 6). Silent, never clean, when a language has no detector, the code is owned only at May or a file hides units: absence is then not Exact."
);
