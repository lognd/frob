fn f(a: i32, b: i32, p: &mut S, q: &S) -> i32 {
    let t = a + 1;
    p.v = t * 2;
    let u = b + 1;
    let y = q.v + u;
    y
}
