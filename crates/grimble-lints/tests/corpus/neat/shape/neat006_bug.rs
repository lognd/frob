fn f(xs: Vec<u8>) {
    for x in xs {
        let a = x;
        let b = a;
        let c = b;
        use_it(c);
    }
}
