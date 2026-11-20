//! `load_comments` reads every review file under `design/review`.

// frob:ticket 01M7TCKMBT95HKXRACWVH5VVDY

use crunk_spec::handoff::load_comments;

// frob:tests crates/crunk-spec/src/handoff.rs::load_comments
#[test]
fn comments_load_sorted_by_file_and_a_missing_directory_yields_none() {
    let dir = tempfile::tempdir().expect("tempdir");
    assert!(load_comments(dir.path()).is_empty(), "no review directory");
    let review = dir.path().join("design/review");
    std::fs::create_dir_all(&review).expect("mkdir");
    std::fs::write(
        review.join("b.toml"),
        "[[comment]]\nid = \"c2\"\nscreen = \"home\"\n",
    )
    .expect("write");
    std::fs::write(
        review.join("a.toml"),
        "[[comment]]\nid = \"c1\"\nscreen = \"home\"\nblocking = true\n",
    )
    .expect("write");
    std::fs::write(review.join("bad.toml"), "not = [valid").expect("write");
    std::fs::write(review.join("note.txt"), "ignored").expect("write");
    let ids: Vec<String> = load_comments(dir.path())
        .into_iter()
        .map(|c| c.id)
        .collect();
    assert_eq!(
        ids,
        ["c1", "c2"],
        "sorted by path; invalid and non-toml skipped"
    );
}
