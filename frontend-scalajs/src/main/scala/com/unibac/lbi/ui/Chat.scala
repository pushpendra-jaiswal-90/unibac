package com.unibac.lbi.ui

import com.raquo.laminar.api.L.*
import io.circe.parser.parse
import io.circe.{Json, JsonObject}
import org.scalajs.dom

sealed trait ChatEvent
object ChatEvent:
  final case class Text(text: String)                                  extends ChatEvent
  final case class ToolCall(id: String, name: String, input: Json)     extends ChatEvent
  final case class ToolResult(id: String, output: Json, isError: Boolean) extends ChatEvent
  final case class TurnEnd(stopReason: String)                         extends ChatEvent
  final case class User(text: String)                                  extends ChatEvent
  final case class ErrorEv(message: String)                            extends ChatEvent

final class Chat:
  val backend  = Var("ollama")
  val token    = Var("")
  val events   = Var(List.empty[ChatEvent])
  val draft    = Var("")
  val status   = Var("disconnected")
  private var sock: Option[dom.WebSocket] = None

  def connect(): Unit =
    sock.foreach(_.close())
    status.set("connecting")
    events.set(Nil)
    val tokenParam =
      if backend.now() == "anthropic" && token.now().nonEmpty
      then s"&token=${scala.scalajs.js.URIUtils.encodeURIComponent(token.now())}"
      else ""
    val url = s"ws://localhost:8001/ws?backend=${backend.now()}$tokenParam"
    val s = new dom.WebSocket(url)
    sock = Some(s)
    s.onopen    = _ => status.set("ready")
    s.onclose   = e =>
      status.set("disconnected")
      val reason = e.reason
      if reason != null && reason.nonEmpty then push(ChatEvent.ErrorEv(reason))
    s.onerror   = _ => status.set("error")
    s.onmessage = e =>
      parse(e.data.toString).toOption.flatMap(_.asObject).foreach(handleFrame)

  private def handleFrame(o: JsonObject): Unit =
    o("type").flatMap(_.asString).foreach {
      case "text"        => o("text").flatMap(_.asString).foreach(t => push(ChatEvent.Text(t)))
      case "tool_call"   =>
        for
          id   <- o("id").flatMap(_.asString)
          name <- o("name").flatMap(_.asString)
          in   <- o("input")
        yield push(ChatEvent.ToolCall(id, name, in))
      case "tool_result" =>
        for
          id   <- o("id").flatMap(_.asString)
          out  <- o("output")
        yield push(ChatEvent.ToolResult(id, out, o("is_error").flatMap(_.asBoolean).contains(true)))
      case "turn_end"    => o("stop_reason").flatMap(_.asString).foreach(r => push(ChatEvent.TurnEnd(r)))
      case "error"       => o("message").flatMap(_.asString).foreach(m => push(ChatEvent.ErrorEv(m)))
      case "ready"       => () // bookkeeping only
      case _             => ()
    }

  private def push(ev: ChatEvent): Unit =
    events.update(_ :+ ev)

  def send(): Unit =
    val txt = draft.now().trim
    if txt.nonEmpty && sock.exists(_.readyState == 1) then
      push(ChatEvent.User(txt))
      sock.get.send(s"""{"type":"message","text":${io.circe.Json.fromString(txt).noSpaces}}""")
      draft.set("")

  def view: HtmlElement =
    div(
      cls := "chat",
      div(
        cls := "chat-head",
        strong("Agent"),
        select(
          value <-- backend,
          onChange.mapToValue --> backend,
          option(value := "ollama", "Local (Ollama)"),
          option(value := "anthropic", "Frontier (Anthropic)")
        ),
        input(
          typ := "password",
          placeholder := "token (frontier only)",
          cls := "token",
          value <-- token,
          onInput.mapToValue --> token,
          display <-- backend.signal.map(b => if b == "anthropic" then "" else "none")
        ),
        button("Connect", onClick --> (_ => connect())),
        span(cls := "status", child.text <-- status.signal)
      ),
      div(
        cls := "chat-log",
        children <-- events.signal.map(_.map(renderEvent))
      ),
      div(
        cls := "chat-input",
        input(
          typ := "text",
          placeholder := "e.g. underwrite sample/applicants/APP002",
          value <-- draft,
          onInput.mapToValue --> draft,
          onKeyDown.filter(_.key == "Enter") --> (_ => send())
        ),
        button("Send", onClick --> (_ => send()))
      )
    )

  private def renderEvent(ev: ChatEvent): HtmlElement = ev match
    case ChatEvent.User(t)        => div(cls := "ev user",   div(cls := "role", "you"), p(t))
    case ChatEvent.Text(t)        => div(cls := "ev text",   div(cls := "role", "assistant"), p(t))
    case ChatEvent.ToolCall(_, n, in) =>
      div(cls := "ev tool-call",
        div(cls := "role", s"→ $n"),
        pre(in.spaces2))
    case ChatEvent.ToolResult(_, out, err) =>
      div(cls := s"ev tool-result${if err then " err" else ""}",
        div(cls := "role", if err then "✗ tool_result" else "✓ tool_result"),
        pre(out.spaces2.take(600)))
    case ChatEvent.TurnEnd(r)     => div(cls := "ev turn-end", em(s"— turn end ($r) —"))
    case ChatEvent.ErrorEv(m)     => div(cls := "ev err", div(cls := "role", "error"), p(m))
