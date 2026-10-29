# LBI frontend — Scala.js / Laminar

The Scala.js reference frontend. Mirrors `../frontend-elm/` 1:1 so you can
compare the two architectures side by side.

Stack:
- Scala 3 → Scala.js 1.17 (`sbt-scalajs`)
- Laminar 17 for reactive views (`Var`/`Signal` streams)
- Circe for JSON decode
- `scalajs-dom` Fetch for HTTP

Run:

    make build         # produces target/scala-3.3.4/lbi-frontend-scalajs-fastopt/main.js
    make serve         # static server on :5173
    # open http://localhost:5173

Backend must be running on :8080 with CORS enabled (`sbt run` in `../backend`).
