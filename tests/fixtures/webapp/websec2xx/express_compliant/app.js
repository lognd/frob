// Compliant Express app fixture (T-5349): secure session cookie + csurf middleware.
const express = require("express");
const session = require("express-session");
const csurf = require("csurf");

const app = express();

app.use(session({
  secret: "keyboard-cat",
  cookie: {
    secure: true,
    httpOnly: true,
    sameSite: "strict",
    maxAge: 1800000,
  },
}));

app.use(csurf());

module.exports = app;
