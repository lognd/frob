//! Scratch.
use grimble_model::dump::{dump, u_signature};
use grimble_model::fold::fold_file;
use grimble_model::parse::parse_file;
use grimble_model::fmt::format_file;
#[test]
fn scratch() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus/example");
    for n in ["frob.grmb", "vmodel.grmb"] {
        let bytes = std::fs::read(dir.join(n)).unwrap();
        let p = parse_file(n, &bytes);
        let f = fold_file(&p, "").unwrap();
        if n == "vmodel.grmb" { println!("{}", dump(&f)); }
        let out = format_file(&p).unwrap();
        let p2 = parse_file(n, out.as_bytes());
        let f2 = fold_file(&p2, "").unwrap();
        assert_eq!(u_signature(&f), u_signature(&f2));
        assert_eq!(format_file(&p2).unwrap(), out);
        if n == "frob.grmb" { println!("{out}"); }
    }
}
