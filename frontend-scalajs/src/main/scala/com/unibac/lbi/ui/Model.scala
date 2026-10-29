package com.unibac.lbi.ui

import io.circe.Decoder
import io.circe.generic.semiauto.deriveDecoder

final case class WorklistItem(
    loan: String,
    score: Int,
    reasons: List[String],
    overdueAmount: BigDecimal,
    dpd: Int,
    nextAction: String
)

object WorklistItem:
  given Decoder[WorklistItem] = deriveDecoder
