//! The D120 admission table: why each registered claim or accounting verb exists (cohesion.md 4).

/// One verb's answers to the three admission tests.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Admission {
    /// `namespace:verb`.
    pub verb: &'static str,
    /// Test 1: the fact the tools cannot compute from code, config or the model.
    pub not_derivable: &'static str,
    /// Test 2: why it is not just an `accept` exception on one rule at one place.
    pub not_an_exception: &'static str,
    /// Test 3: the rules or products that consume it, or the claim a rule verifies.
    pub consumers: &'static str,
}

const fn row(
    verb: &'static str,
    not_derivable: &'static str,
    not_an_exception: &'static str,
    consumers: &'static str,
) -> Admission {
    Admission {
        verb,
        not_derivable,
        not_an_exception,
        consumers,
    }
}

/// Every registered `frob:` and `grimble:` verb with its admission row.
pub const ADMISSION: &[Admission] = &[
    row(
        "frob:ticket",
        "which work item justifies this hunk is intent",
        "binds work to code; silences nothing",
        "TICK and COV rules, frob ticket close, frob land",
    ),
    row(
        "frob:todo",
        "that a debt is owed, and to whom, is intent",
        "tracks a debt; silences nothing",
        "TODO001 and the ticket graph",
    ),
    row(
        "frob:doc",
        "which section documents this symbol is authorial",
        "binds documentation; silences nothing",
        "DOC drift rules and frob ack",
    ),
    row(
        "frob:describes",
        "which symbol a prose section describes is authorial",
        "binds documentation; silences nothing",
        "DOC drift rules and frob ack",
    ),
    row(
        "frob:tests",
        "which test covers which symbol is not computable",
        "binds evidence; silences nothing",
        "COV rules, frob test, ticket evidence",
    ),
    row(
        "frob:invariant",
        "the stated property is intent no tool can derive",
        "states a property; silences nothing",
        "INV rules and test binding checks",
    ),
    row(
        "frob:accept",
        "the reason a finding stays is owner judgment",
        "it is the exception: reason, owner, expiry, counted",
        "every rule's suppression and the exception ledger",
    ),
    row(
        "frob:defer",
        "that a ticket will pay a finding is owner judgment",
        "it is the exception form that names a paying ticket",
        "every rule's suppression and the ticket graph",
    ),
    row(
        "grimble:binds",
        "which model entity a unit implements is design intent",
        "binds a unit to the model; silences nothing",
        "SYS and binding rules",
    ),
    row(
        "grimble:effects",
        "an effect claim on an unanalysable body (FFI, reflection) cannot be inferred",
        "states a verifiable claim; silences nothing",
        "NEAT effects rules (VERIFIED, CONTRADICTED or UNVERIFIED)",
    ),
    row(
        "grimble:core",
        "the role a unit plays in the design is a claim",
        "states a role; silences nothing",
        "NEAT014-016, COH002, effects rules",
    ),
    row(
        "grimble:shell",
        "the role a unit plays in the design is a claim",
        "states a role; silences nothing",
        "NEAT014-016, COH002, effects rules",
    ),
    row(
        "grimble:calls",
        "dynamic call targets are invisible to resolution",
        "adds call edges; silences nothing",
        "gob-ir resolution for every rule that reads call edges",
    ),
];

/// The admission row of `qualified` (`namespace:verb`), when it has one.
pub fn admission_for(qualified: &str) -> Option<&'static Admission> {
    ADMISSION.iter().find(|a| a.verb == qualified)
}
