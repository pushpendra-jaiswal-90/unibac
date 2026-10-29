# LBI frontend — Elm

The Elm reference frontend. Mirrors `../frontend-scalajs/` 1:1 so you can
compare the two architectures side by side.

Stack:
- Elm 0.19.1
- `elm/browser` (The Elm Architecture: Model / Msg / update / view)
- `elm/http` + `elm/json` for the API client

Install the compiler if needed:

    brew install elm   # or: npm i -g elm

Run:

    make build         # elm make src/Main.elm --output=app.js
    make serve         # static server on :5174
    # open http://localhost:5174

Backend must be running on :8080 with CORS enabled (`sbt run` in `../backend`).
