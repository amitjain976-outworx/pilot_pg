module.exports = {
  style: {
    postcss: {
      // "file" mode: let postcss-loader read postcss.config.js directly
      // instead of craco merging plugins in via its own array-append logic.
      mode: "file",
    },
  },
};
