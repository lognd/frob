fn f(a: i32, sink: Sink) -> i32 {
    if a > 3 {
        sink.send(a);
    }
    let x = compute(a);
    if x > 3 {
        log(x);
    }
    x
}
