package com.unibac.lbi.audit

import cats.effect.{Ref, Sync}
import cats.syntax.all.*
import java.time.Instant

final case class AuditEvent(
    at: Instant,
    actor: String,
    action: String,
    target: String,
    detail: Map[String, String]
)

trait AuditLog[F[_]]:
  def record(actor: String, action: String, target: String, detail: Map[String, String] = Map.empty): F[Unit]
  def recent(n: Int): F[List[AuditEvent]]

object AuditLog:
  def inMemory[F[_]: Sync]: F[AuditLog[F]] =
    Ref.of[F, Vector[AuditEvent]](Vector.empty).map: ref =>
      new AuditLog[F]:
        def record(actor: String, action: String, target: String, detail: Map[String, String]): F[Unit] =
          Sync[F].delay(Instant.now()).flatMap: now =>
            ref.update(_ :+ AuditEvent(now, actor, action, target, detail))

        def recent(n: Int): F[List[AuditEvent]] =
          ref.get.map(_.takeRight(n).toList.reverse)
