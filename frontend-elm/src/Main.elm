module Main exposing (main)

{-| Elm counterpart to the Scala.js frontend. Same endpoints, same layout,
same interactions — meant for side-by-side comparison with Laminar.

Backend:
  GET http://localhost:8080/v1/worklist?tenant=<t>  -> [WorklistItem]
  GET http://localhost:8080/v1/dashboard?tenant=<t> -> { metric: Number, ... }
-}

import Browser
import Dict exposing (Dict)
import Html exposing (..)
import Html.Attributes exposing (class, classList, type_, value)
import Html.Events exposing (onClick, onInput)
import Http
import Json.Decode as D exposing (Decoder)


apiBase : String
apiBase =
    "http://localhost:8080"



-- MODEL -----------------------------------------------------------------------


type alias WorklistItem =
    { loan : String
    , score : Int
    , reasons : List String
    , overdueAmount : Float
    , dpd : Int
    , nextAction : String
    }


type alias Model =
    { tenant : String
    , worklist : List WorklistItem
    , dashboard : Dict String Float
    , selected : Maybe WorklistItem
    , error : Maybe String
    }


init : () -> ( Model, Cmd Msg )
init _ =
    ( { tenant = "demo"
      , worklist = []
      , dashboard = Dict.empty
      , selected = Nothing
      , error = Nothing
      }
    , Cmd.batch [ fetchWorklist "demo", fetchDashboard "demo" ]
    )



-- UPDATE ----------------------------------------------------------------------


type Msg
    = TenantChanged String
    | Reload
    | GotWorklist (Result Http.Error (List WorklistItem))
    | GotDashboard (Result Http.Error (Dict String Float))
    | Selected WorklistItem


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        TenantChanged t ->
            ( { model | tenant = t }, Cmd.none )

        Reload ->
            ( { model | error = Nothing }
            , Cmd.batch [ fetchWorklist model.tenant, fetchDashboard model.tenant ]
            )

        GotWorklist (Ok xs) ->
            ( { model | worklist = xs }, Cmd.none )

        GotWorklist (Err e) ->
            ( { model | error = Just (httpErr e) }, Cmd.none )

        GotDashboard (Ok m) ->
            ( { model | dashboard = m }, Cmd.none )

        GotDashboard (Err e) ->
            ( { model | error = Just (httpErr e) }, Cmd.none )

        Selected it ->
            ( { model | selected = Just it }, Cmd.none )


httpErr : Http.Error -> String
httpErr e =
    case e of
        Http.BadUrl u ->
            "bad url: " ++ u

        Http.Timeout ->
            "timeout"

        Http.NetworkError ->
            "network error (is the backend on :8080? CORS?)"

        Http.BadStatus s ->
            "status " ++ String.fromInt s

        Http.BadBody b ->
            "bad body: " ++ b



-- HTTP ------------------------------------------------------------------------


fetchWorklist : String -> Cmd Msg
fetchWorklist t =
    Http.get
        { url = apiBase ++ "/v1/worklist?tenant=" ++ t
        , expect = Http.expectJson GotWorklist (D.list worklistItemDecoder)
        }


fetchDashboard : String -> Cmd Msg
fetchDashboard t =
    Http.get
        { url = apiBase ++ "/v1/dashboard?tenant=" ++ t
        , expect = Http.expectJson GotDashboard (D.dict D.float)
        }


worklistItemDecoder : Decoder WorklistItem
worklistItemDecoder =
    D.map6 WorklistItem
        (D.field "loan" D.string)
        (D.field "score" D.int)
        (D.field "reasons" (D.list D.string))
        (D.field "overdueAmount" D.float)
        (D.field "dpd" D.int)
        (D.field "nextAction" D.string)



-- VIEW ------------------------------------------------------------------------


view : Model -> Html Msg
view model =
    div [ class "wrap" ]
        [ viewHeader model
        , viewError model.error
        , viewDashboard model.dashboard
        , div [ class "cols" ]
            [ viewWorklist model
            , viewDetail model.selected
            ]
        ]


viewHeader : Model -> Html Msg
viewHeader model =
    header []
        [ h1 [] [ text "LBI Collections — Elm" ]
        , div [ class "tenant" ]
            [ label [] [ text "Tenant " ]
            , input [ type_ "text", value model.tenant, onInput TenantChanged ] []
            , button [ onClick Reload ] [ text "Load" ]
            ]
        ]


viewError : Maybe String -> Html Msg
viewError e =
    case e of
        Nothing ->
            text ""

        Just m ->
            div [ class "err" ] [ text m ]


viewDashboard : Dict String Float -> Html Msg
viewDashboard d =
    div [ class "cards" ]
        (d
            |> Dict.toList
            |> List.sortBy Tuple.first
            |> List.map
                (\( k, v ) ->
                    div [ class "card" ]
                        [ div [ class "k" ] [ text k ]
                        , div [ class "v" ] [ text (fmtFloat v ++ "%") ]
                        ]
                )
        )


viewWorklist : Model -> Html Msg
viewWorklist model =
    table [ class "worklist" ]
        [ thead []
            [ tr []
                [ th [] [ text "Loan" ]
                , th [] [ text "Score" ]
                , th [] [ text "DPD" ]
                , th [] [ text "Overdue" ]
                , th [] [ text "Action" ]
                ]
            ]
        , tbody [] (List.map (viewRow model.selected) model.worklist)
        ]


viewRow : Maybe WorklistItem -> WorklistItem -> Html Msg
viewRow sel it =
    tr
        [ classList
            [ ( "row", True )
            , ( "selected", Maybe.map .loan sel == Just it.loan )
            ]
        , onClick (Selected it)
        ]
        [ td [] [ text it.loan ]
        , td [] [ text (String.fromInt it.score) ]
        , td [] [ text (String.fromInt it.dpd) ]
        , td [] [ text ("₹" ++ fmtFloat it.overdueAmount) ]
        , td [] [ text it.nextAction ]
        ]


viewDetail : Maybe WorklistItem -> Html Msg
viewDetail sel =
    div [ class "detail" ]
        [ case sel of
            Nothing ->
                div [ class "muted" ] [ text "Select a loan to see rationale." ]

            Just it ->
                div []
                    [ h3 [] [ text it.loan ]
                    , p [] [ em [] [ text it.nextAction ], text " · score ", strong [] [ text (String.fromInt it.score) ] ]
                    , p [] [ text ("Overdue ₹" ++ fmtFloat it.overdueAmount ++ " · " ++ String.fromInt it.dpd ++ " DPD") ]
                    , h4 [] [ text "Reasons" ]
                    , ul [] (List.map (\r -> li [] [ text r ]) it.reasons)
                    ]
        ]


fmtFloat : Float -> String
fmtFloat f =
    let
        rounded =
            toFloat (round (f * 100)) / 100
    in
    String.fromFloat rounded



-- MAIN ------------------------------------------------------------------------


main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , view = view
        , subscriptions = \_ -> Sub.none
        }
