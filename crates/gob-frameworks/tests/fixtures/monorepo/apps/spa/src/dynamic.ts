declare function fetchRoutes(): never[];
declare function computePath(): string;
export const dynamicRoutes = fetchRoutes();
export const runtimePath = computePath();
