<template>
  <div v-html="sanitize(userComment)"></div>
</template>
<script>
export default { props: ["userComment"] };
</script>
