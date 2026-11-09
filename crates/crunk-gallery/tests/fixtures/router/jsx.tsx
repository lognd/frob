export const App = () => (
  <Routes>
    <Route path="/" element={<Layout onClick={() => go()} />}>
      <Route index element={<Home />} />
      <Route path="pricing" element={<Pricing />} />
      <Route path={"docs/:slug?"} element={<Docs />}>
        <Route path="api" element={<Api />} />
      </Route>
    </Route>
    <Route path="/login" element={<Login />} />
    <p>Don't break on apostrophes</p>
  </Routes>
);
