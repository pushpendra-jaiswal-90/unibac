package com.unibac.lbi.ui

import com.raquo.laminar.api.L.*
import org.scalajs.dom

import scala.concurrent.ExecutionContext.Implicits.global

object Main:

  private val tenant     = Var("demo")
  private val worklist   = Var(List.empty[WorklistItem])
  private val dashboard  = Var(Map.empty[String, BigDecimal])
  private val selected   = Var(Option.empty[WorklistItem])
  private val errorMsg   = Var(Option.empty[String])
  private val chat       = new Chat()

  private def refresh(t: String): Unit =
    errorMsg.set(None)
    Api.worklist(t).onComplete:
      case scala.util.Success(xs)  => worklist.set(xs)
      case scala.util.Failure(err) => errorMsg.set(Some(err.getMessage))
    Api.dashboard(t).onComplete:
      case scala.util.Success(m)   => dashboard.set(m)
      case scala.util.Failure(err) => errorMsg.set(Some(err.getMessage))

  def main(args: Array[String]): Unit =
    renderOnDomContentLoaded(dom.document.getElementById("app"), app())
    refresh(tenant.now())

  private def app(): HtmlElement =
    div(
      cls := "wrap",
      headerTag(
        h1("LBI Collections — Scala.js / Laminar"),
        div(
          cls := "tenant",
          label("Tenant "),
          input(
            typ := "text",
            value <-- tenant,
            onInput.mapToValue --> tenant
          ),
          button("Load", onClick --> (_ => refresh(tenant.now())))
        )
      ),
      child.maybe <-- errorMsg.signal.map(_.map(m => div(cls := "err", m))),
      dashboardPanel(),
      div(
        cls := "cols",
        worklistTable(),
        detailPanel()
      ),
      chat.view
    )

  private def dashboardPanel(): HtmlElement =
    div(
      cls := "cards",
      children <-- dashboard.signal.map { m =>
        m.toList.sortBy(_._1).map { case (k, v) =>
          div(cls := "card", div(cls := "k", k), div(cls := "v", v.toString + "%"))
        }
      }
    )

  private def worklistTable(): HtmlElement =
    table(
      cls := "worklist",
      thead(tr(th("Loan"), th("Score"), th("DPD"), th("Overdue"), th("Action"))),
      tbody(
        children <-- worklist.signal.map { items =>
          items.map { it =>
            tr(
              cls := "row",
              cls.toggle("selected") <-- selected.signal.map(_.exists(_.loan == it.loan)),
              onClick --> (_ => selected.set(Some(it))),
              td(it.loan),
              td(it.score.toString),
              td(it.dpd.toString),
              td("₹" + it.overdueAmount.toString),
              td(it.nextAction)
            )
          }
        }
      )
    )

  private def detailPanel(): HtmlElement =
    div(
      cls := "detail",
      child <-- selected.signal.map {
        case None     => div(cls := "muted", "Select a loan to see rationale.")
        case Some(it) =>
          div(
            h3(it.loan),
            p(em(it.nextAction), " · score ", strong(it.score.toString)),
            p("Overdue ₹", it.overdueAmount.toString, " · ", it.dpd.toString, " DPD"),
            h4("Reasons"),
            ul(it.reasons.map(r => li(r)))
          )
      }
    )
