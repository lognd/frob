# Compliant Rails session-store fixture (T-5349): secure cookie store.
Rails.application.config.session_store :cookie_store,
  key: "_app_session",
  secure: true,
  httponly: true,
  same_site: :strict,
  expire_after: 1800
