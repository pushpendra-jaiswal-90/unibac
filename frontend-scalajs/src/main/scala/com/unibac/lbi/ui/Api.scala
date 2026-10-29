package com.unibac.lbi.ui

import io.circe.parser.decode
import org.scalajs.dom
import org.scalajs.dom.{Fetch, RequestInit}

import scala.concurrent.{ExecutionContext, Future}
import scala.scalajs.js.Thenable.Implicits.*

object Api:
  val base: String = "http://localhost:8080"

  def worklist(tenant: String)(using ExecutionContext): Future[List[WorklistItem]] =
    get(s"$base/v1/worklist?tenant=$tenant").map { body =>
      decode[List[WorklistItem]](body) match
        case Right(xs) => xs
        case Left(err) => throw new RuntimeException(s"worklist decode: $err")
    }

  def dashboard(tenant: String)(using ExecutionContext): Future[Map[String, BigDecimal]] =
    get(s"$base/v1/dashboard?tenant=$tenant").map { body =>
      decode[Map[String, BigDecimal]](body) match
        case Right(m)  => m
        case Left(err) => throw new RuntimeException(s"dashboard decode: $err")
    }

  private def get(url: String)(using ExecutionContext): Future[String] =
    Fetch.fetch(url).flatMap(_.text())
