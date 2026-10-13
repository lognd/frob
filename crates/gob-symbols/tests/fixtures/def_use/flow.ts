function f(a: number, b: number) {
  const x = a + 1;
  let y = b;
  y = x;
  this.v = x;
  const z = this.v;
  const c = () => x + y;
  if (x) {
    y = 2;
  }
  for (let i = 0; i < a; i++) {
    y = y + i;
  }
  return y + z + c();
}
