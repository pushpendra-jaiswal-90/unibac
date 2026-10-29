package com.unibac.lbi

import cats.effect.{IO, IOApp, Resource}
import com.comcast.ip4s.*
import org.http4s.ember.server.EmberServerBuilder
import org.http4s.server.middleware.{Logger, RequestId}
import org.slf4j.LoggerFactory

import com.unibac.lbi.api.Routes
import com.unibac.lbi.ingestion.IngestionService
import com.unibac.lbi.metrics.MetricsService
import com.unibac.lbi.audit.AuditLog

object Main extends IOApp.Simple:

  private val log = LoggerFactory.getLogger(getClass)

  def run: IO[Unit] =
    val resource =
      for
        audit    <- Resource.eval(AuditLog.inMemory[IO])
        ingest   <- Resource.eval(IO.pure(IngestionService.stub[IO](audit)))
        metrics  <- Resource.eval(IO.pure(MetricsService.stub[IO]))
        routes    = Routes(ingest, metrics, audit).all
        app       = Logger.httpApp(logHeaders = true, logBody = false)(
                      RequestId.httpApp(routes.orNotFound)
                    )
        server   <- EmberServerBuilder
                      .default[IO]
                      .withHost(host"0.0.0.0")
                      .withPort(port"8080")
                      .withHttpApp(app)
                      .build
      yield server

    resource.use: server =>
      IO(log.info(s"LBI backend listening on ${server.address}")) *> IO.never
