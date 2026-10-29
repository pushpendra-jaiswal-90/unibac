package com.unibac.lbi.domain

import java.time.{Instant, LocalDate}
import java.util.UUID

import io.circe.{Decoder, Encoder}

opaque type TenantId  = String
opaque type LoanId    = String
opaque type RunId     = UUID
opaque type BranchId  = String

object TenantId:
  def apply(s: String): TenantId = s
  extension (t: TenantId) def value: String = t
  given Encoder[TenantId] = Encoder.encodeString.contramap(_.value)
  given Decoder[TenantId] = Decoder.decodeString.map(TenantId.apply)

object LoanId:
  def apply(s: String): LoanId = s
  extension (l: LoanId) def value: String = l
  given Encoder[LoanId] = Encoder.encodeString.contramap(_.value)
  given Decoder[LoanId] = Decoder.decodeString.map(LoanId.apply)

object RunId:
  def apply(u: UUID): RunId = u
  def random: RunId         = UUID.randomUUID()
  extension (r: RunId) def value: UUID = r
  given Encoder[RunId] = Encoder.encodeUUID.contramap(_.value)
  given Decoder[RunId] = Decoder.decodeUUID.map(RunId.apply)

object BranchId:
  def apply(s: String): BranchId = s
  extension (b: BranchId) def value: String = b
  given Encoder[BranchId] = Encoder.encodeString.contramap(_.value)
  given Decoder[BranchId] = Decoder.decodeString.map(BranchId.apply)

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
