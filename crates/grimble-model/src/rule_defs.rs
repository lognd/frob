//! The MDL rule family declarations (grmb-spec 11), one `#[derive(Rule)]` struct each.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

#[rustfmt::skip]
macro_rules! mdl_rule {
    ($name:ident, $id:literal, $slug:literal, $sev:ident, $summary:literal, $explain:literal) => {
        #[doc = $summary]
        #[doc = ""]
        #[doc = $explain]
        #[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
        #[rule(
                    id = $id,
                    slug = $slug,
                    family = "MDL",
                    product = "grimble",
                    severity = $sev,
                    tier = Lang,
                    scope = Repo,
                    fix = Manual,
                    version = 1,
                    since = "2.0.0"
                )]
        pub struct $name;
    };
}

mdl_rule!(
    Mdl000,
    "MDL000",
    "mdl-syntax",
    Error,
    "Lexical or syntax error, bad encoding, or a forbidden construct.",
    "Covers invalid UTF-8, a byte-order mark, NUL, a bare CR, an unknown token, a keyword used as a name, a hand-written `baseline`, a bare `because \"...\"` and a slug rule alias. A syntax error becomes a `hole` and the rest of the file is still read."
);
mdl_rule!(
    Mdl001,
    "MDL001",
    "mdl-duplicate-entity",
    Error,
    "Two declarations of one full name.",
    "Entities, aliases and `renamed_from` names share one namespace per model; the first in (path, byte) order is kept. Use `extend` to add to an existing entity."
);
mdl_rule!(
    Mdl002,
    "MDL002",
    "mdl-unresolved-include",
    Error,
    "An include names a missing file, matches nothing, escapes the repository or is not readable.",
    "Includes are structural: a file that is missing is an error, unlike a selector that matches nothing."
);
mdl_rule!(
    Mdl003,
    "MDL003",
    "mdl-include-cycle",
    Error,
    "The include graph has a cycle.",
    "The offending include is skipped so the rest of the model still loads. A diamond is not a cycle."
);
mdl_rule!(
    Mdl004,
    "MDL004",
    "mdl-unknown-pack",
    Error,
    "A pack is not enabled, not under `packs/`, or its version or digest differs from the pin.",
    "Pins are exact so a model and a pack move together."
);
mdl_rule!(
    Mdl005,
    "MDL005",
    "mdl-selector-no-file",
    Warn,
    "A selector's path matches no file in the walk.",
    "A warning by design: a model may describe code that does not exist yet. It suppresses SYS004 for the same selector."
);
mdl_rule!(
    Mdl006,
    "MDL006",
    "mdl-unresolved-ref",
    Error,
    "A reference resolves to no entity, or to an entity of the wrong kind.",
    "Covers flow endpoints, claim operands, contract references, boundary flows, exception targets and `extend` targets."
);
mdl_rule!(
    Mdl007,
    "MDL007",
    "mdl-version",
    Error,
    "Missing version header, unsupported major, or files of one model with different majors.",
    "A file with a missing or unsupported header is refused whole and never parsed on a guess."
);
mdl_rule!(
    Mdl008,
    "MDL008",
    "mdl-field",
    Error,
    "A required field is missing, a scalar clause appears twice, or an `extend` sets a scalar.",
    "Required: node trust, flow label, contract shape, claim what, vmodel kind and level, pack ref and version."
);
mdl_rule!(
    Mdl009,
    "MDL009",
    "mdl-type",
    Error,
    "An ill-typed value.",
    "A unit outside the closed table, a quantity of the wrong dimension, a path with `..` or an empty path, a boundary pair on the wrong lattice, an unknown lattice element or a malformed date."
);
mdl_rule!(
    Mdl010,
    "MDL010",
    "mdl-selector-empty-by-construction",
    Warn,
    "A selector that cannot match anything whatever the repository holds.",
    "For example `lang(rust) & lang(python)` or `a & !a`."
);
mdl_rule!(
    Mdl011,
    "MDL011",
    "mdl-module",
    Error,
    "A `part of` name differs from the root `module`, two roots share a module name, or an included file declares `module`.",
    "One model has exactly one `module` declaration, in its root file."
);
mdl_rule!(
    Mdl012,
    "MDL012",
    "mdl-deprecated-name",
    Warn,
    "A reference uses a `renamed_from` name.",
    "Edit the reference to the new name. The clause itself is reported once no lock entry needs it (that half needs the lock and is evaluated by the binary)."
);
mdl_rule!(
    Mdl013,
    "MDL013",
    "mdl-exception",
    Error,
    "A malformed exception clause.",
    "Wrong attribute set for the kind, `on` inside a body, missing `on` at top level, an unknown rule id, a malformed `ticket` or `until`, or a `grimble:accept` style directive in a .grmb comment."
);
mdl_rule!(
    Mdl014,
    "MDL014",
    "mdl-vmodel",
    Error,
    "A V-model construction error.",
    "Wrong endpoint kinds, unpaired levels on `verifies`, a missing `ref` or `runnable`, a duplicate link, or `supersedes` without `because`."
);
mdl_rule!(
    Mdl015,
    "MDL015",
    "mdl-shadow",
    Advisory,
    "A reference resolved to a nearer entity that shadows an outer one of the same name.",
    "Shadowing is legal and reported; anchor the reference with a leading `::` to name the outer one."
);
mdl_rule!(
    Mdl016,
    "MDL016",
    "mdl-unknown-atom",
    Error,
    "A capability atom is in no registry and no enabled pack.",
    "Atoms resolve against the registry (and, qualified, against the named pack)."
);
mdl_rule!(
    Mdl017,
    "MDL017",
    "mdl-duplicate-clause",
    Advisory,
    "A list clause repeated with identical content.",
    "The formatter removes the duplicate."
);
