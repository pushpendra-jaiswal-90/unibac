package com.unibac.lbi.ingestion

import cats.Applicative
import cats.syntax.all.*
import com.unibac.lbi.audit.AuditLog
import com.unibac.lbi.domain.*

final case class IngestionResult(
    runId: RunId,
    rowsAccepted: Long,
    rowsQuarantined: Long,
    errors: List[String]
)

trait IngestionService[F[_]]:
  def ingestLoanSnapshot(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult]
  def ingestRepayments(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult]
  def ingestCollectionActivity(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult]

object IngestionService:
  def stub[F[_]: Applicative](audit: AuditLog[F]): IngestionService[F] =
    new IngestionService[F]:
      private def noop(tenant: TenantId, sourceFileId: String, kind: String): F[IngestionResult] =
        val runId = RunId.random
        audit
          .record(
            actor  = tenant.value,
            action = s"ingest.$kind",
            target = sourceFileId,
            detail = Map("run_id" -> runId.value.toString)
          )
          .as(IngestionResult(runId, 0L, 0L, Nil))

      def ingestLoanSnapshot(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult] =
        noop(tenant, sourceFileId, "loan_snapshot")

      def ingestRepayments(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult] =
        noop(tenant, sourceFileId, "repayments")

      def ingestCollectionActivity(tenant: TenantId, sourceFileId: String, csvBytes: Array[Byte]): F[IngestionResult] =
        noop(tenant, sourceFileId, "collection_activity")
