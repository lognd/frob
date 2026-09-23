# Violating Rails session-store fixture (T-5349): insecure cookie store.
Rails.application.config.session_store :cookie_store,
  key: "_app_session",
  secure: false,
  httponly: false
