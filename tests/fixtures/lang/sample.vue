<!-- frob:tests test_lang_html_js_jsx_vue.py::test_parse_vue_sample -->
<template>
  <div class="app">
    <p>{{ message }}</p>
  </div>
</template>

<script>
export default {
  name: "App",
  data() {
    return { message: "hello" };
  },
};
</script>

<style scoped>
.app {
  color: red;
}
</style>
