package com.unibac.lbi.domain

import java.time.{Instant, LocalDate}
import java.util.UUID

opaque type TenantId  = String
opaque type LoanId    = String
opaque type RunId     = UUID
opaque type BranchId  = String

object TenantId:
  def apply(s: String): TenantId = s
  extension (t: TenantId) def value: String = t

object LoanId:
  def apply(s: String): LoanId = s
  extension (l: LoanId) def value: String = l

object RunId:
  def apply(u: UUID): RunId = u
  def random: RunId         = UUID.randomUUID()
  extension (r: RunId) def value: UUID = r

object BranchId:
  def apply(s: String): BranchId = s
  extension (b: BranchId) def value: String = b

final case class LoanSnapshot(
    loan: LoanId,
    tenant: TenantId,
    snapshotDate: LocalDate,
    branch: BranchId,
    productType: String,
    loanStatus: String,
    emiAmount: BigDecimal,
    nextDueDate: LocalDate,
    overdueAmount: BigDecimal,
    dpd: Option[Int],
    outstandingPrincipal: BigDecimal,
    collectorId: Option[String],
    loanStartDate: Option[LocalDate]
)

final case class WorklistItem(
    loan: LoanId,
    score: Int,
    reasons: List[String],
    overdueAmount: BigDecimal,
    dpd: Int,
    nextAction: String
)

final case class IngestionRun(
    id: RunId,
    tenant: TenantId,
    sourceFileId: String,
    startedAt: Instant,
    finishedAt: Option[Instant],
    rowsAccepted: Long,
    rowsQuarantined: Long
)
