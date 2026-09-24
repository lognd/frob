module.exports = {
  mode: "production",
  entry: "./src/index.js",
  performance: {
    maxAssetSize: 250000,
    maxEntrypointSize: 250000,
  },
};
