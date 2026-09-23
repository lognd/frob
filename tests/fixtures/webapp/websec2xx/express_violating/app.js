// Violating Express app fixture (T-5349): insecure session cookie, no CSRF middleware.
const express = require("express");
const session = require("express-session");

const app = express();

app.use(session({
  secret: "keyboard-cat",
  cookie: {
    secure: false,
    httpOnly: false,
  },
}));

module.exports = app;
