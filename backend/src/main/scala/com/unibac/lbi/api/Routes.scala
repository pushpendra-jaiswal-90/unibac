package com.unibac.lbi.api

import cats.effect.Concurrent
import cats.syntax.all.*
import io.circe.generic.auto.*
import io.circe.syntax.*
import org.http4s.*
import org.http4s.circe.*
import org.http4s.circe.CirceEntityCodec.*
import org.http4s.dsl.Http4sDsl

import com.unibac.lbi.audit.{AuditEvent, AuditLog}
import com.unibac.lbi.domain.*
import com.unibac.lbi.ingestion.{IngestionResult, IngestionService}
import com.unibac.lbi.metrics.MetricsService

final class Routes[F[_]: Concurrent](
    ingest: IngestionService[F],
    metrics: MetricsService[F],
    audit: AuditLog[F]
) extends Http4sDsl[F]:

  private object TenantQ extends QueryParamDecoderMatcher[String]("tenant")
  private object BranchQ extends OptionalQueryParamDecoderMatcher[String]("branch")
  private object LimitQ  extends OptionalQueryParamDecoderMatcher[Int]("limit")

  private val health: HttpRoutes[F] = HttpRoutes.of[F]:
    case GET -> Root / "healthz" => Ok(Map("status" -> "ok").asJson)

  private val ingestion: HttpRoutes[F] = HttpRoutes.of[F]:
    case req @ POST -> Root / "v1" / "ingest" / kind :? TenantQ(tenant) =>
      req.as[Array[Byte]].flatMap: bytes =>
        val t  = TenantId(tenant)
        val sf = req.headers.get(ci"X-Source-File-Id").map(_.head.value).getOrElse("unknown")
        val fx: F[IngestionResult] = kind match
          case "loan_snapshot"       => ingest.ingestLoanSnapshot(t, sf, bytes)
          case "repayments"          => ingest.ingestRepayments(t, sf, bytes)
          case "collection_activity" => ingest.ingestCollectionActivity(t, sf, bytes)
          case other                 =>
            Concurrent[F].raiseError(new IllegalArgumentException(s"unknown ingest kind: $other"))
        fx.flatMap(r => Ok(r.asJson))

  private val worklist: HttpRoutes[F] = HttpRoutes.of[F]:
    case GET -> Root / "v1" / "worklist" :? TenantQ(tenant) +& BranchQ(branch) +& LimitQ(limit) =>
      metrics
        .worklist(TenantId(tenant), branch.map(BranchId.apply), limit.getOrElse(100))
        .flatMap(items => Ok(items.asJson))

  private val dashboard: HttpRoutes[F] = HttpRoutes.of[F]:
    case GET -> Root / "v1" / "dashboard" :? TenantQ(tenant) =>
      metrics.dashboard(TenantId(tenant)).flatMap(d => Ok(d.asJson))

  private val auditRoutes: HttpRoutes[F] = HttpRoutes.of[F]:
    case GET -> Root / "v1" / "audit" :? LimitQ(limit) =>
      audit.recent(limit.getOrElse(100)).flatMap(ev => Ok(ev.asJson))

  val all: HttpRoutes[F] = health <+> ingestion <+> worklist <+> dashboard <+> auditRoutes

  import org.typelevel.ci.CIStringSyntax
  private given [F2[_]]: Conversion[String, org.typelevel.ci.CIString] = s => org.typelevel.ci.CIString(s)

object Routes:
  def apply[F[_]: Concurrent](
      ingest: IngestionService[F],
      metrics: MetricsService[F],
      audit: AuditLog[F]
  ): Routes[F] = new Routes[F](ingest, metrics, audit)
