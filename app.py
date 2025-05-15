import json
import random
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

###############################################################################
# 1) LOAD DATA
###############################################################################
with open("meere_meeresteile_und_seen.json", "r", encoding="utf-8") as f:
    meere_data = json.load(f)
with open("fluesse.json", "r", encoding="utf-8") as f:
    fluesse_data = json.load(f)
with open("inseln_inselgruppen.json", "r", encoding="utf-8") as f:
    inseln_data = json.load(f)
with open("gebirge.json", "r", encoding="utf-8") as f:
    gebirge_data = json.load(f)

# Already existing "forgotten.json"
with open("forgotten.json", "r", encoding="utf-8") as f:
    forgotten_data = json.load(f)

# NEW: Load forgotten2.json
with open("forgotten2.json", "r", encoding="utf-8") as f:
    forgotten2_data = json.load(f)

territory_data = {
    "gewässer": {
        "meere_meeresteile_und_seen": meere_data,
        "fluesse": fluesse_data,
        "inseln_inselgruppen": inseln_data,
        "gebirge": gebirge_data,
        "forgotten": forgotten_data,
        "forgotten2": forgotten2_data
    }
}

###############################################################################
# 2) BUILD DATAFRAME
###############################################################################
data_rows = []

def add_category(cat_name, cat_data):
    feats = cat_data.get("data", [])
    coords = cat_data.get("coords", {})
    for feat in feats:
        info = coords.get(feat, {})
        geom_type = info.get("type", "point")
        points = info.get("points", [])
        data_rows.append({
            "category": cat_name,
            "feature": feat,
            "geometry_type": geom_type,
            "geometry_points": points
        })

# Add each group
add_category("Meere, Meeresteile und Seen", territory_data["gewässer"]["meere_meeresteile_und_seen"])
add_category("Flüsse", territory_data["gewässer"]["fluesse"])
add_category("Inseln/Inselgruppen", territory_data["gewässer"]["inseln_inselgruppen"])
add_category("Gebirge", territory_data["gewässer"]["gebirge"])
add_category("Vergessenes", territory_data["gewässer"]["forgotten"])

# NEW: Extra category for forgotten2.json
add_category("Vergessenes2", territory_data["gewässer"]["forgotten2"])

df = pd.DataFrame(data_rows)

###############################################################################
# 3) DASH APP LAYOUT
###############################################################################
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])

app.layout = dbc.Container([
    dcc.Store(id="store-mode", data=None),
    dcc.Store(id="store-selected-category", data=None),
    dcc.Store(id="store-remaining-features", data=[]),
    dcc.Store(id="store-selected-feature", data=None),
    dcc.Store(id="store-correct-count", data=0),
    dcc.Store(id="store-wrong-count", data=0),
    dcc.Store(id="store-done-features", data=[]),
    dcc.Store(id="store-start-time", data=None),

    dbc.NavbarSimple(
        brand="Geographisches Ratespiel - Blind Map",
        brand_href="#",
        color="primary",
        dark=True,
        className="mb-4"
    ),

    # SCREEN 0: Mode Selection
    dbc.Card(
        [
            dbc.CardHeader("Modus auswählen", className="bg-secondary text-white"),
            dbc.CardBody([
                dbc.Button("Learning", id="mode-learning-button", n_clicks=0, color="primary", className="me-2"),
                dbc.Button("Quiz", id="mode-quiz-button", n_clicks=0, color="secondary")
            ])
        ],
        id="mode-selection-card",
        style={"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "block"}
    ),

    # SCREEN 1: Category Selection
    dbc.Card(
        [
            dbc.CardHeader("Kategorie auswählen", className="bg-secondary text-white"),
            dbc.CardBody([
                dcc.Dropdown(id="category-dropdown", style={"maxWidth": "300px"}),
                dbc.Button("Weiter", id="category-next-button", n_clicks=0, color="success", className="mt-3")
            ])
        ],
        id="category-selection-card",
        style={"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "none"}
    ),

    # SCREEN 2A: Quiz
    dbc.Card(
        [
            dbc.CardHeader("Ratespiel", className="bg-secondary text-white"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Welches Feature ist hervorgehoben?", style={"fontWeight": "bold"}),
                        dcc.Dropdown(id="feature-guess-dropdown", style={"maxWidth": "300px"}),
                        dbc.Button("Tipp absenden", id="guess-button", n_clicks=0, color="primary", className="mt-2"),
                        html.Div(id="guess-result", style={"marginTop": "1em", "fontWeight": "bold", "color": "#333"})
                    ], md=4),
                    dbc.Col([
                        dcc.Graph(id="blind-map", style={"height": "500px"})
                    ], md=8)
                ]),
                html.Hr(),
                html.Div(id="score-display", className="mt-3 text-center"),
                html.Div(id="lists-display", className="mt-3 text-center"),
                dbc.Button("Neu starten", id="reset-button", n_clicks=0, color="warning", className="mt-3"),
                dbc.Button("Zurück zum Menü", id="back-button", n_clicks=0, color="info", className="mt-3")
            ])
        ],
        id="quiz-card",
        style={"maxWidth": "900px", "margin": "0 auto 2rem auto", "display": "none"}
    ),

    # SCREEN 2B: Learning
    dbc.Card(
        [
            dbc.CardHeader("Lernmodus", className="bg-secondary text-white"),
            dbc.CardBody([
                dcc.Graph(id="learning-map", style={"height": "500px"}),
                html.Div(id="learning-list", className="mt-3 text-center"),
                dbc.Button("Zurück zum Menü", id="learning-back-button", n_clicks=0, color="info", className="mt-3")
            ])
        ],
        id="learning-card",
        style={"maxWidth": "900px", "margin": "0 auto 2rem auto", "display": "none"}
    )
], fluid=True)

###############################################################################
# 4) SINGLE CALLBACK FOR MODE
###############################################################################
@app.callback(
    Output("store-mode", "data"),
    Input("mode-learning-button", "n_clicks"),
    Input("mode-quiz-button", "n_clicks")
)
def set_mode(n_learn, n_quiz):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig_id == "mode-learning-button" and n_learn:
        return "learning"
    elif trig_id == "mode-quiz-button" and n_quiz:
        return "quiz"
    return no_update

###############################################################################
# 5) POPULATE CATEGORY DROPDOWN
###############################################################################
@app.callback(
    Output("category-dropdown", "options"),
    Input("store-mode", "data")
)
def populate_category(mode):
    if mode == "quiz":
        return [
            {"label": "Alle", "value": "Alle"},
            {"label": "Meere, Meeresteile und Seen", "value": "Meere, Meeresteile und Seen"},
            {"label": "Flüsse", "value": "Flüsse"},
            {"label": "Inseln/Inselgruppen", "value": "Inseln/Inselgruppen"},
            {"label": "Gebirge", "value": "Gebirge"},
            {"label": "Vergessenes", "value": "Vergessenes"},
            {"label": "Vergessenes2", "value": "Vergessenes2"},
        ]
    elif mode == "learning":
        return [
            {"label": "Meere, Meeresteile und Seen", "value": "Meere, Meeresteile und Seen"},
            {"label": "Flüsse", "value": "Flüsse"},
            {"label": "Inseln/Inselgruppen", "value": "Inseln/Inselgruppen"},
            {"label": "Gebirge", "value": "Gebirge"},
            {"label": "Vergessenes", "value": "Vergessenes"},
            {"label": "Vergessenes2", "value": "Vergessenes2"},
        ]
    return []

###############################################################################
# 6) SINGLE CALLBACK TO SET/RESET CATEGORY
###############################################################################
@app.callback(
    Output("store-selected-category", "data"),
    Input("category-next-button", "n_clicks"),
    Input("back-button", "n_clicks"),
    Input("learning-back-button", "n_clicks"),
    State("category-dropdown", "value"),
    State("store-selected-category", "data"),
    prevent_initial_call=True
)
def set_or_reset_category(n_next, n_quiz_back, n_learn_back, chosen_cat, old_cat):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trig_id == "category-next-button":
        if chosen_cat:
            return chosen_cat
        return old_cat
    elif trig_id in ["back-button", "learning-back-button"]:
        # Reset to None
        return None

    return no_update

###############################################################################
# 7) SWITCH SCREENS
###############################################################################
@app.callback(
    Output("mode-selection-card", "style"),
    Output("category-selection-card", "style"),
    Output("quiz-card", "style"),
    Output("learning-card", "style"),
    Input("store-mode", "data"),
    Input("store-selected-category", "data")
)
def switch_screens(mode, selected_cat):
    if mode is None:
        return (
            {"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "block"},
            {"display": "none"},
            {"display": "none"},
            {"display": "none"}
        )
    if selected_cat is None:
        return (
            {"display": "none"},
            {"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "block"},
            {"display": "none"},
            {"display": "none"}
        )
    if mode == "quiz":
        return (
            {"display": "none"},
            {"display": "none"},
            {"maxWidth": "900px", "margin": "0 auto 2rem auto", "display": "block"},
            {"display": "none"}
        )
    elif mode == "learning":
        return (
            {"display": "none"},
            {"display": "none"},
            {"display": "none"},
            {"maxWidth": "900px", "margin": "0 auto 2rem auto", "display": "block"}
        )
    return no_update, no_update, no_update, no_update

###############################################################################
# 8) QUIZ LOGIC
###############################################################################
@app.callback(
    Output("feature-guess-dropdown", "options"),
    Output("store-selected-feature", "data"),
    Output("guess-result", "children"),
    Output("store-correct-count", "data"),
    Output("store-wrong-count", "data"),
    Output("store-done-features", "data"),
    Output("store-remaining-features", "data"),
    Output("score-display", "children"),
    Output("lists-display", "children"),
    Output("feature-guess-dropdown", "value"),
    Output("store-start-time", "data"),
    Input("store-selected-category", "data"),
    Input("reset-button", "n_clicks"),
    Input("guess-button", "n_clicks"),
    State("store-selected-feature", "data"),
    State("store-correct-count", "data"),
    State("store-wrong-count", "data"),
    State("store-done-features", "data"),
    State("store-remaining-features", "data"),
    State("feature-guess-dropdown", "value"),
    State("store-start-time", "data")
)
def quiz_logic(selected_cat,
               reset_click,
               guess_click,
               current_feature,
               correct_count,
               wrong_count,
               done_features,
               remaining_features,
               user_guess,
               start_time):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, "", no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    now = time.time()
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]
    message = ""

    # If no category set, do nothing special
    if selected_cat is None:
        return no_update, no_update, "", correct_count, wrong_count, done_features, remaining_features, no_update, no_update, no_update, start_time

    # If "Alle" => gather all features
    if selected_cat == "Alle":
        cat_feats = df["feature"].tolist()
    else:
        cat_feats = df[df["category"] == selected_cat]["feature"].tolist()

    # Reset scenario
    if not remaining_features or trig_id == "reset-button":
        remaining_features = cat_feats.copy()
        current_feature = random.choice(remaining_features) if remaining_features else None
        done_features = []
        correct_count = 0
        wrong_count = 0
        start_time = now
        if trig_id == "reset-button":
            message = "Ratespiel neu gestartet!"

    # Guess scenario
    elif trig_id == "guess-button":
        if not current_feature:
            message = "Keine Features übrig oder Ratespiel nicht gestartet."
        else:
            if not user_guess:
                message = "Bitte wähle ein Feature aus dem Dropdown!"
            else:
                if start_time is None:
                    start_time = now
                if user_guess == current_feature:
                    message = "Richtig! Neues Feature wird geladen."
                    correct_count += 1
                else:
                    message = f"Falsch! Richtig war: {current_feature}"
                    wrong_count += 1
                if current_feature not in done_features:
                    done_features.append(current_feature)
                remaining_features = [f for f in remaining_features if f != current_feature]
                if remaining_features:
                    current_feature = random.choice(remaining_features)
                else:
                    message += " Ratespiel beendet!"
                    current_feature = None

    dropdown_options = [{"label": f, "value": f} for f in remaining_features]
    elapsed = now - start_time if start_time else 0
    elapsed_str = f"{int(elapsed)} s" if elapsed < 120 else f"{int(elapsed//60)} min {int(elapsed%60)} s"

    score_display = dbc.Card(
        dbc.CardBody([
            html.H5("Aktueller Punktestand", className="card-title"),
            html.P(f"Korrekt: {correct_count}", style={"margin": 0}),
            html.P(f"Falsch: {wrong_count}", style={"margin": 0}),
            html.P(f"Zeit: {elapsed_str}", style={"margin": 0, "marginTop": 8, "fontStyle": "italic"})
        ]),
        className="border p-2 d-inline-block"
    )

    lists_display = dbc.Card(
        dbc.CardBody([
            html.H6("Verbleibende Features:"),
            html.P(", ".join(remaining_features) if remaining_features else "Keine mehr"),
            html.H6("Bereits gemacht:"),
            html.P(", ".join(done_features) if done_features else "Noch keine")
        ]),
        className="border p-2 mt-2"
    )

    return (
        dropdown_options,
        current_feature,
        message,
        correct_count,
        wrong_count,
        done_features,
        remaining_features,
        score_display,
        lists_display,
        None,
        start_time
    )

###############################################################################
# 9) QUIZ MAP (NO-FILL FOR POLYGONS)
###############################################################################
@app.callback(
    Output("blind-map", "figure"),
    Input("store-selected-feature", "data")
)
def update_quiz_map(selected_feature):
    fig = go.Figure()
    fig.update_layout(
        title="Blind Map - Ratespiel",
        geo=dict(scope="world"),
        height=500
    )
    if not selected_feature:
        return fig

    row = df[df["feature"] == selected_feature]
    if row.empty:
        return fig

    geom_type = row.iloc[0]["geometry_type"]
    points = row.iloc[0]["geometry_points"]

    # color for quiz
    color_quiz = "red"

    if geom_type == "point":
        lat, lon = points[0]
        fig.add_trace(go.Scattergeo(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=12, color=color_quiz)
        ))
    elif geom_type == "line":
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        fig.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=6, color=color_quiz)
        ))
    elif geom_type == "polygon":
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        # close polygon if not closed
        if points[0] != points[-1]:
            lats.append(points[0][0])
            lons.append(points[0][1])

        # Outline only
        fig.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=3, color=color_quiz)
        ))

        # If you'd like to fill smaller polygons, use fill="toself":
        # fig.add_trace(go.Scattergeo(
        #     lat=lats,
        #     lon=lons,
        #     mode="lines",
        #     fill="toself",
        #     line=dict(width=3, color=color_quiz),
        #     fillcolor=color_quiz,
        #     opacity=0.3
        # ))

    return fig

###############################################################################
# 10) LEARNING MAP (NO-FILL FOR POLYGONS)
###############################################################################
@app.callback(
    Output("learning-map", "figure"),
    Output("learning-list", "children"),
    Input("store-selected-category", "data")
)
def update_learning_map(selected_category):
    if not selected_category:
        fig = px.scatter(x=[0], y=[0], title="Bitte Kategorie auswählen")
        fig.update_layout(height=400)
        return fig, "Bitte Kategorie auswählen."

    sub_df = df[df["category"] == selected_category]
    fig = go.Figure()
    fig.update_layout(
        title=f"Lernmodus: {selected_category}",
        geo=dict(scope="world"),
        height=500
    )

    color_learn = "blue"

    for _, row_data in sub_df.iterrows():
        feat = row_data["feature"]
        gtype = row_data["geometry_type"]
        pts = row_data["geometry_points"]

        if gtype == "point":
            lat, lon = pts[0]
            fig.add_trace(go.Scattergeo(
                lat=[lat],
                lon=[lon],
                mode="markers+text",
                text=[feat],
                textposition="top center",
                marker=dict(size=12, color=color_learn)
            ))
        elif gtype == "line":
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=4, color=color_learn)
            ))
            # Label near midpoint
            mid_i = len(lats)//2
            fig.add_trace(go.Scattergeo(
                lat=[lats[mid_i]],
                lon=[lons[mid_i]],
                mode="text",
                text=[feat],
                textposition="top center"
            ))
        elif gtype == "polygon":
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]
            if pts[0] != pts[-1]:
                lats.append(pts[0][0])
                lons.append(pts[0][1])

            # Outline only:
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=3, color=color_learn)
            ))
            # Optionally fill:
            # fig.add_trace(go.Scattergeo(
            #     lat=lats,
            #     lon=lons,
            #     mode="lines",
            #     fill="toself",
            #     line=dict(width=3, color=color_learn),
            #     fillcolor=color_learn,
            #     opacity=0.3
            # ))

            # Label near centroid
            avg_lat = sum(lats)/len(lats)
            avg_lon = sum(lons)/len(lons)
            fig.add_trace(go.Scattergeo(
                lat=[avg_lat],
                lon=[avg_lon],
                mode="text",
                text=[feat],
                textposition="top center"
            ))

    list_text = "Features: " + ", ".join(sub_df["feature"].tolist())
    return fig, list_text

###############################################################################
# RUN
###############################################################################
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
