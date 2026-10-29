ThisBuild / scalaVersion     := "3.3.4"
ThisBuild / version          := "0.1.0-SNAPSHOT"
ThisBuild / organization     := "com.unibac"
ThisBuild / organizationName := "Unibac"

val http4sVersion   = "0.23.28"
val circeVersion    = "0.14.10"
val catsEffectVer   = "3.5.4"
val doobieVersion   = "1.0.0-RC5"
val logbackVersion  = "1.5.12"
val munitVersion    = "1.0.3"
val munitCEVersion  = "2.0.0"

lazy val root = (project in file("."))
  .settings(
    name := "lbi-backend",
    libraryDependencies ++= Seq(
      "org.http4s"      %% "http4s-ember-server" % http4sVersion,
      "org.http4s"      %% "http4s-ember-client" % http4sVersion,
      "org.http4s"      %% "http4s-dsl"          % http4sVersion,
      "org.http4s"      %% "http4s-circe"        % http4sVersion,
      "io.circe"        %% "circe-core"          % circeVersion,
      "io.circe"        %% "circe-generic"       % circeVersion,
      "io.circe"        %% "circe-parser"        % circeVersion,
      "org.typelevel"   %% "cats-effect"         % catsEffectVer,
      "org.tpolecat"    %% "doobie-core"         % doobieVersion,
      "org.tpolecat"    %% "doobie-postgres"     % doobieVersion,
      "org.tpolecat"    %% "doobie-hikari"       % doobieVersion,
      "ch.qos.logback"  %  "logback-classic"     % logbackVersion,
      "org.scalameta"   %% "munit"                   % munitVersion    % Test,
      "org.typelevel"   %% "munit-cats-effect"       % munitCEVersion  % Test
    ),
    scalacOptions ++= Seq(
      "-deprecation",
      "-feature",
      "-Wunused:all"
    )
  )
