//! The MDL rule pages of `src/rules/*.md` as an mdtest corpus: every example runs `check_model`
//! over a small model assembled from the page's `config` words and keeps the page's rule.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use grimble_model::{ModelFiles, PackPin, check_model};

/// A part-of file that joins module `m`.
const PART: &str = "grimble = \"2\";\npart of m;\n";

/// The case file's directory (`design/` for every page).
fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// Parse `pack=ID,VERSION,DIGEST,ATOMS` into the pin it declares.
fn pack_of(spec: &str) -> Option<(String, PackPin)> {
    let mut it = spec.split(',');
    let id = it.next()?.to_owned();
    let version = it.next()?.to_owned();
    let digest = it.next().map(str::to_owned);
    let atoms = it.map(str::to_owned).collect();
    Some((
        id,
        PackPin {
            version,
            digest,
            atoms,
        },
    ))
}

/// The model one example describes: the case file plus the fixtures its config words ask for.
fn model_of(case: &gob_mdtest::Case) -> ModelFiles {
    let me = case.file_name.as_str();
    let dir = dir_of(me);
    let sibling = |name: &str| {
        if dir.is_empty() {
            name.to_owned()
        } else {
            format!("{dir}/{name}")
        }
    };
    // SYS rules live in grimble-bind; the exception pages name one of them.
    let mut model = ModelFiles::new()
        .with_file(me, case.text.as_bytes())
        .with_rule("SYS004");
    let mut root = me.to_owned();
    let mut walk = vec![me.to_owned(), "crates/a/lib.rs".to_owned()];
    let mut declared_none = false;
    for word in case.config.as_deref().unwrap_or("").split_whitespace() {
        match word {
            "cycle" => {
                model = model.with_file(
                    &sibling("b.grmb"),
                    format!(
                        "{PART}include \"{}\";\n",
                        me.rsplit('/').next().unwrap_or(me)
                    ),
                );
            }
            "shared" => model = model.with_file(&sibling("shared.grmb"), PART),
            "shared-up" => model = model.with_file("shared.grmb", PART),
            "included" => {
                root = sibling("root.grmb");
                model = model.with_file(
                    &root,
                    format!(
                        "grimble = \"2\";\nmodule m;\ninclude \"{}\";\n",
                        me.rsplit('/').next().unwrap_or(me)
                    ),
                );
            }
            "orphan" => {
                root = sibling("root.grmb");
                model = model.with_file(&root, "grimble = \"2\";\nmodule m;\n");
            }
            "no-roots" => declared_none = true,
            "walk" => {}
            other => {
                if let Some((id, pin)) = other.strip_prefix("pack=").and_then(pack_of) {
                    model = model.with_pack(&id, pin);
                }
            }
        }
    }
    model = if declared_none {
        model.with_declared_roots(Vec::new())
    } else {
        model.with_root(&root)
    };
    if case.config.as_deref().is_some_and(|c| c.contains("walk")) {
        model = model.with_walk(std::mem::take(&mut walk));
    }
    model
}

/// Run the model check over one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/grimble-model/src/rules/mdl000.rs::Mdl000
    // frob:tests crates/grimble-model/src/rules/mdl001.rs::Mdl001
    // frob:tests crates/grimble-model/src/rules/mdl002.rs::Mdl002
    // frob:tests crates/grimble-model/src/rules/mdl003.rs::Mdl003
    // frob:tests crates/grimble-model/src/rules/mdl004.rs::Mdl004
    // frob:tests crates/grimble-model/src/rules/mdl005.rs::Mdl005
    // frob:tests crates/grimble-model/src/rules/mdl006.rs::Mdl006
    // frob:tests crates/grimble-model/src/rules/mdl007.rs::Mdl007
    // frob:tests crates/grimble-model/src/rules/mdl008.rs::Mdl008
    // frob:tests crates/grimble-model/src/rules/mdl009.rs::Mdl009
    // frob:tests crates/grimble-model/src/rules/mdl010.rs::Mdl010
    // frob:tests crates/grimble-model/src/rules/mdl011.rs::Mdl011
    // frob:tests crates/grimble-model/src/rules/mdl012.rs::Mdl012
    // frob:tests crates/grimble-model/src/rules/mdl013.rs::Mdl013
    // frob:tests crates/grimble-model/src/rules/mdl014.rs::Mdl014
    // frob:tests crates/grimble-model/src/rules/mdl015.rs::Mdl015
    // frob:tests crates/grimble-model/src/rules/mdl016.rs::Mdl016
    // frob:tests crates/grimble-model/src/rules/mdl017.rs::Mdl017
    // frob:tests crates/grimble-model/src/rules/mdl019.rs::Mdl019
    // frob:tests crates/grimble-model/src/rules/mdl020.rs::Mdl020
    // frob:tests crates/grimble-model/src/rules/mdl021.rs::Mdl021
    check_model(&model_of(case))
        .into_iter()
        .filter(|f| f.rule == case.rule)
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);
