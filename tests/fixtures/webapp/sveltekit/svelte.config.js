// minimal SvelteKit marker fixture for frob.webapp detection tests.
import adapter from "@sveltejs/kit/vite";

export default {
  kit: { adapter: adapter() },
};
