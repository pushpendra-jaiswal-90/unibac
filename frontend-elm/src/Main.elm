port module Main exposing (main)

{-| Elm counterpart to the Scala.js frontend. Same endpoints, same layout.

Backend REST:
  GET http://localhost:8080/v1/worklist?tenant=<t>  -> [WorklistItem]
  GET http://localhost:8080/v1/dashboard?tenant=<t> -> { metric: Number, ... }

Agent WebSocket (via JS port shim, see index.html):
  ws://localhost:8001/ws?backend=ollama|anthropic
-}

import Browser
import Dict exposing (Dict)
import Html exposing (..)
import Html.Attributes exposing (class, classList, placeholder, selected, type_, value)
import Html.Events exposing (on, onClick, onInput)
import Http
import Json.Decode as D exposing (Decoder)
import Json.Encode as E


apiBase : String
apiBase =
    "http://localhost:8080"


wsBase : String
wsBase =
    "ws://localhost:8001/ws"



-- PORTS -----------------------------------------------------------------------
-- Elm 0.19 removed native WebSocket; a tiny JS shim in index.html routes
-- messages. The port keeps the Elm side pure.


port wsConnect : String -> Cmd msg


port wsSend : String -> Cmd msg


port wsRecv : (String -> msg) -> Sub msg



-- MODEL -----------------------------------------------------------------------


type alias WorklistItem =
    { loan : String
    , score : Int
    , reasons : List String
    , overdueAmount : Float
    , dpd : Int
    , nextAction : String
    }


type ChatEvent
    = EvUser String
    | EvText String
    | EvToolCall String String E.Value
    | EvToolResult String E.Value Bool
    | EvTurnEnd String
    | EvError String


type alias Model =
    { tenant : String
    , worklist : List WorklistItem
    , dashboard : Dict String Float
    , selectedLoan : Maybe WorklistItem
    , error : Maybe String
    , chatBackend : String
    , chatStatus : String
    , chatEvents : List ChatEvent
    , chatDraft : String
    }


init : () -> ( Model, Cmd Msg )
init _ =
    ( { tenant = "demo"
      , worklist = []
      , dashboard = Dict.empty
      , selectedLoan = Nothing
      , error = Nothing
      , chatBackend = "ollama"
      , chatStatus = "disconnected"
      , chatEvents = []
      , chatDraft = ""
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
    | ChatBackendChanged String
    | ChatConnect
    | ChatDraftChanged String
    | ChatSend
    | ChatIncoming String


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
            ( { model | selectedLoan = Just it }, Cmd.none )

        ChatBackendChanged b ->
            ( { model | chatBackend = b }, Cmd.none )

        ChatConnect ->
            ( { model | chatStatus = "connecting", chatEvents = [] }
            , wsConnect (wsBase ++ "?backend=" ++ model.chatBackend)
            )

        ChatDraftChanged s ->
            ( { model | chatDraft = s }, Cmd.none )

        ChatSend ->
            let
                txt =
                    String.trim model.chatDraft
            in
            if txt == "" then
                ( model, Cmd.none )

            else
                ( { model | chatDraft = "", chatEvents = model.chatEvents ++ [ EvUser txt ] }
                , wsSend
                    (E.encode 0
                        (E.object [ ( "type", E.string "message" ), ( "text", E.string txt ) ])
                    )
                )

        ChatIncoming raw ->
            case D.decodeString chatFrameDecoder raw of
                Ok applyFrame ->
                    ( applyFrame model, Cmd.none )

                Err _ ->
                    ( model, Cmd.none )


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



-- WS DECODING -----------------------------------------------------------------
-- The decoder returns a model-transformer so the state update happens in Elm
-- rather than being passed back through Cmd/Msg plumbing.


chatFrameDecoder : Decoder (Model -> Model)
chatFrameDecoder =
    D.field "type" D.string
        |> D.andThen frameByType


frameByType : String -> Decoder (Model -> Model)
frameByType t =
    case t of
        "ready" ->
            D.succeed (\m -> { m | chatStatus = "ready" })

        "text" ->
            D.field "text" D.string
                |> D.map (\s m -> { m | chatEvents = m.chatEvents ++ [ EvText s ] })

        "tool_call" ->
            D.map3 (\id n inp m -> { m | chatEvents = m.chatEvents ++ [ EvToolCall id n inp ] })
                (D.field "id" D.string)
                (D.field "name" D.string)
                (D.field "input" D.value)

        "tool_result" ->
            D.map3
                (\id out err m ->
                    { m | chatEvents = m.chatEvents ++ [ EvToolResult id out err ] }
                )
                (D.field "id" D.string)
                (D.field "output" D.value)
                (D.oneOf [ D.field "is_error" D.bool, D.succeed False ])

        "turn_end" ->
            D.oneOf [ D.field "stop_reason" D.string, D.succeed "end_turn" ]
                |> D.map (\r m -> { m | chatEvents = m.chatEvents ++ [ EvTurnEnd r ] })

        "error" ->
            D.field "message" D.string
                |> D.map (\s m -> { m | chatEvents = m.chatEvents ++ [ EvError s ] })

        _ ->
            D.succeed identity



-- VIEW ------------------------------------------------------------------------


view : Model -> Html Msg
view model =
    div [ class "wrap" ]
        [ viewHeader model
        , viewError model.error
        , viewDashboard model.dashboard
        , div [ class "cols" ]
            [ viewWorklist model
            , viewDetail model.selectedLoan
            ]
        , viewChat model
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
        , tbody [] (List.map (viewRow model.selectedLoan) model.worklist)
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


viewChat : Model -> Html Msg
viewChat model =
    div [ class "chat" ]
        [ div [ class "chat-head" ]
            [ strong [] [ text "Agent" ]
            , select [ onInput ChatBackendChanged ]
                [ option [ value "ollama", selected (model.chatBackend == "ollama") ] [ text "Local (Ollama)" ]
                , option [ value "anthropic", selected (model.chatBackend == "anthropic") ] [ text "Frontier (Anthropic)" ]
                ]
            , button [ onClick ChatConnect ] [ text "Connect" ]
            , span [ class "status" ] [ text model.chatStatus ]
            ]
        , div [ class "chat-log" ] (List.map viewEvent model.chatEvents)
        , div [ class "chat-input" ]
            [ input
                [ type_ "text"
                , placeholder "e.g. underwrite sample/applicants/APP002"
                , value model.chatDraft
                , onInput ChatDraftChanged
                , onEnter ChatSend
                ]
                []
            , button [ onClick ChatSend ] [ text "Send" ]
            ]
        ]


onEnter : msg -> Html.Attribute msg
onEnter msg =
    on "keydown"
        (D.field "key" D.string
            |> D.andThen
                (\k ->
                    if k == "Enter" then
                        D.succeed msg

                    else
                        D.fail "not enter"
                )
        )


viewEvent : ChatEvent -> Html Msg
viewEvent ev =
    case ev of
        EvUser t ->
            div [ class "ev user" ]
                [ div [ class "role" ] [ text "you" ], p [] [ text t ] ]

        EvText t ->
            div [ class "ev text" ]
                [ div [ class "role" ] [ text "assistant" ], p [] [ text t ] ]

        EvToolCall _ n inp ->
            div [ class "ev tool-call" ]
                [ div [ class "role" ] [ text ("→ " ++ n) ]
                , pre [] [ text (E.encode 2 inp) ]
                ]

        EvToolResult _ out err ->
            div
                [ classList
                    [ ( "ev", True )
                    , ( "tool-result", True )
                    , ( "err", err )
                    ]
                ]
                [ div [ class "role" ]
                    [ text
                        (if err then
                            "✗ tool_result"

                         else
                            "✓ tool_result"
                        )
                    ]
                , pre [] [ text (String.left 600 (E.encode 2 out)) ]
                ]

        EvTurnEnd r ->
            div [ class "ev turn-end" ] [ em [] [ text ("— turn end (" ++ r ++ ") —") ] ]

        EvError m ->
            div [ class "ev err" ]
                [ div [ class "role" ] [ text "error" ], p [] [ text m ] ]


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
        , subscriptions = \_ -> wsRecv ChatIncoming
        }
