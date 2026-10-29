package com.unibac.lbi.metrics

import cats.Applicative
import cats.syntax.all.*
import com.unibac.lbi.domain.*

trait MetricsService[F[_]]:
  def worklist(tenant: TenantId, branch: Option[BranchId], limit: Int): F[List[WorklistItem]]
  def dashboard(tenant: TenantId): F[Map[String, BigDecimal]]

object MetricsService:
  /** Stub — the real implementation shells out to the Rust `lbi-core` CLI. */
  def stub[F[_]: Applicative]: MetricsService[F] =
    new MetricsService[F]:
      def worklist(tenant: TenantId, branch: Option[BranchId], limit: Int): F[List[WorklistItem]] =
        List.empty[WorklistItem].pure[F]

      def dashboard(tenant: TenantId): F[Map[String, BigDecimal]] =
        Map(
          "collection_efficiency_pct" -> BigDecimal(0),
          "cure_rate_pct"             -> BigDecimal(0),
          "roll_forward_rate_pct"     -> BigDecimal(0)
        ).pure[F]
