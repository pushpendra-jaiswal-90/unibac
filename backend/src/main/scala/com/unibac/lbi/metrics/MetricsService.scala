package com.unibac.lbi.metrics

import cats.Applicative
import cats.syntax.all.*
import com.unibac.lbi.domain.*

trait MetricsService[F[_]]:
  def worklist(tenant: TenantId, branch: Option[BranchId], limit: Int): F[List[WorklistItem]]
  def dashboard(tenant: TenantId): F[Map[String, BigDecimal]]

object MetricsService:
  /** Stub — the real implementation shells out to the Rust `lbi-core` CLI.
   *  Seeded with representative items so the two reference frontends have
   *  something to render while the real pipeline is being wired up.
   */
  def stub[F[_]: Applicative]: MetricsService[F] =
    new MetricsService[F]:
      private val demo: List[WorklistItem] = List(
        WorklistItem(LoanId("APP003"), 92, List("NPA bucket", "8 cheque bounces", "CIBIL 548"),
          BigDecimal(185432), 94, "FIELD_VISIT"),
        WorklistItem(LoanId("APP002"), 71, List("30+ DPD", "GST filing 83%"),
          BigDecimal(42150), 37, "TELECALL"),
        WorklistItem(LoanId("APP007"), 64, List("Broken PTP", "Collector reassigned"),
          BigDecimal(28900), 21, "TELECALL"),
        WorklistItem(LoanId("APP011"), 58, List("Early DPD", "Low balance"),
          BigDecimal(12750), 9, "SMS"),
        WorklistItem(LoanId("APP001"), 18, List("Current", "CIBIL 782"),
          BigDecimal(0), 0, "NONE")
      )

      def worklist(tenant: TenantId, branch: Option[BranchId], limit: Int): F[List[WorklistItem]] =
        demo.take(limit).pure[F]

      def dashboard(tenant: TenantId): F[Map[String, BigDecimal]] =
        Map(
          "collection_efficiency_pct" -> BigDecimal("87.4"),
          "cure_rate_pct"             -> BigDecimal("23.1"),
          "roll_forward_rate_pct"     -> BigDecimal("11.6")
        ).pure[F]
