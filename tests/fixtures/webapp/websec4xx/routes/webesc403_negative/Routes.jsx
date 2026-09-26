export function AppRoutes() {
  return (
    <Routes>
      <Route path="/admin/dashboard" element={<RequireAuth><AdminDashboard /></RequireAuth>} />
    </Routes>
  );
}
