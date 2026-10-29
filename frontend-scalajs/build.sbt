enablePlugins(ScalaJSPlugin)

ThisBuild / scalaVersion := "3.3.4"
ThisBuild / organization := "com.unibac"
ThisBuild / version      := "0.1.0-SNAPSHOT"

name := "lbi-frontend-scalajs"

scalaJSUseMainModuleInitializer := true

// Emit a single ES module next to index.html.
scalaJSLinkerConfig ~= { _.withModuleKind(ModuleKind.ESModule) }

libraryDependencies ++= Seq(
  "com.raquo"     %%% "laminar"       % "17.1.0",
  "io.circe"      %%% "circe-core"    % "0.14.10",
  "io.circe"      %%% "circe-generic" % "0.14.10",
  "io.circe"      %%% "circe-parser"  % "0.14.10",
  "org.scala-js"  %%% "scalajs-dom"   % "2.8.0"
)

scalacOptions ++= Seq("-deprecation", "-feature")
