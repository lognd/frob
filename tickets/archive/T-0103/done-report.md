## Done report

_infra.py::_elaborate_store now maps StoreDecl.capacity to the kernel
Capacity exactly as _elaborate.py does for nodes (import aliased to
KernelCapacity to avoid the surface-model clash). One regression test;
all strata tests green; ruff/ty clean.
