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

territory_data = {
    "gewässer": {
        "meere_meeresteile_und_seen": meere_data,
        "fluesse": fluesse_data,
        "inseln_inselgruppen": inseln_data,
        "gebirge": gebirge_data
    }
}

###############################################################################
# 2) BUILD DATAFRAME
###############################################################################
data_rows = []

def add_category(cat_name, cat_data):
    features = cat_data.get("data", [])
    coords = cat_data.get("coords", {})
    for feature in features:
        info = coords.get(feature, {})
        geom_type = info.get("type", "point")
        points = info.get("points", [])
        data_rows.append({
            "category": cat_name,
            "feature": feature,
            "geometry_type": geom_type,
            "geometry_points": points
        })

add_category("Meere, Meeresteile und Seen", territory_data["gewässer"]["meere_meeresteile_und_seen"])
add_category("Flüsse", territory_data["gewässer"]["fluesse"])
add_category("Inseln/Inselgruppen", territory_data["gewässer"]["inseln_inselgruppen"])
add_category("Gebirge", territory_data["gewässer"]["gebirge"])

df = pd.DataFrame(data_rows)

###############################################################################
# 3) APP LAYOUT
###############################################################################
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.layout = dbc.Container([
    # Stores
    dcc.Store(id="store-mode", data=None),              # "learning", "quiz", or None
    dcc.Store(id="store-selected-category", data=None), # e.g. "Flüsse" or None
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
# 4) POPULATE CATEGORY DROPDOWN
###############################################################################
@app.callback(
    Output("category-dropdown", "options"),
    Input("store-mode", "data")
)
def populate_category_dropdown(mode):
    """
    As soon as mode changes, set the dropdown options accordingly.
    """
    if mode == "quiz":
        return [
            {"label": "Alle", "value": "Alle"},
            {"label": "Meere, Meeresteile und Seen", "value": "Meere, Meeresteile und Seen"},
            {"label": "Flüsse", "value": "Flüsse"},
            {"label": "Inseln/Inselgruppen", "value": "Inseln/Inselgruppen"},
            {"label": "Gebirge", "value": "Gebirge"}
        ]
    elif mode == "learning":
        return [
            {"label": "Meere, Meeresteile und Seen", "value": "Meere, Meeresteile und Seen"},
            {"label": "Flüsse", "value": "Flüsse"},
            {"label": "Inseln/Inselgruppen", "value": "Inseln/Inselgruppen"},
            {"label": "Gebirge", "value": "Gebirge"}
        ]
    return []

###############################################################################
# 5) COMBINED CALLBACK: SET OR RESET MODE & CATEGORY
###############################################################################
@app.callback(
    Output("store-mode", "data"),
    Output("store-selected-category", "data"),
    Input("mode-learning-button", "n_clicks"),
    Input("mode-quiz-button", "n_clicks"),
    Input("category-next-button", "n_clicks"),
    Input("back-button", "n_clicks"),
    Input("learning-back-button", "n_clicks"),
    State("store-mode", "data"),
    State("category-dropdown", "value")
)
def mode_and_category_callback(n_learn, n_quiz, n_next, n_back_quiz, n_back_learn, current_mode, chosen_category):
    """
    A single callback that sets/clears BOTH store-mode and store-selected-category.
    This avoids the "duplicate callback outputs" error.

    1) If user clicks "Learning" => mode="learning", category=None
    2) If user clicks "Quiz" => mode="quiz", category=None
    3) If user clicks "Weiter" => store-selected-category=chosen_category
    4) If user clicks "Zurück zum Menü" => mode=None, category=None
    """
    ctx = callback_context
    if not ctx.triggered:
        return current_mode, no_update
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # 1) "Learning" button
    if trig_id == "mode-learning-button" and n_learn:
        return "learning", None

    # 2) "Quiz" button
    elif trig_id == "mode-quiz-button" and n_quiz:
        return "quiz", None

    # 3) "Weiter"
    elif trig_id == "category-next-button" and chosen_category:
        return current_mode, chosen_category

    # 4) "Zurück zum Menü" (either from quiz or learning)
    elif trig_id in ["back-button", "learning-back-button"]:
        return None, None

    return current_mode, no_update

###############################################################################
# 6) SWITCH SCREENS
###############################################################################
@app.callback(
    Output("mode-selection-card", "style"),
    Output("category-selection-card", "style"),
    Output("quiz-card", "style"),
    Output("learning-card", "style"),
    Input("store-mode", "data"),
    Input("store-selected-category", "data")
)
def switch_screens(mode, selected_category):
    """
    If mode is None => show mode selection
    If mode chosen but category not => show category selection
    If both => show relevant main screen
    """
    if mode is None:
        return (
            {"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "block"},  # mode sel
            {"display": "none"},  # cat sel
            {"display": "none"},  # quiz
            {"display": "none"}   # learning
        )
    if selected_category is None:
        return (
            {"display": "none"},
            {"maxWidth": "600px", "margin": "0 auto 2rem auto", "display": "block"},
            {"display": "none"},
            {"display": "none"}
        )
    # If both mode & category
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
# 7) QUIZ LOGIC
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
def quiz_logic(selected_category,
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

    if selected_category is None:
        return no_update, no_update, "", correct_count, wrong_count, done_features, remaining_features, no_update, no_update, no_update, start_time

    # Build feature list
    if selected_category == "Alle":
        cat_features = df["feature"].tolist()
    else:
        cat_features = df[df["category"] == selected_category]["feature"].tolist()

    if (not remaining_features) or (trig_id == "reset-button"):
        remaining_features = cat_features.copy()
        current_feature = random.choice(remaining_features) if remaining_features else None
        done_features = []
        correct_count = 0
        wrong_count = 0
        start_time = now
        if trig_id == "reset-button":
            message = "Ratespiel neu gestartet!"
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
# 8) QUIZ MAP
###############################################################################
@app.callback(
    Output("blind-map", "figure"),
    Input("store-selected-feature", "data")
)
def update_quiz_map(selected_feature):
    """
    Always show scope="world". If a feature is selected, highlight it in red.
    """
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

    if geom_type == "point":
        lat, lon = points[0]
        fig.add_trace(go.Scattergeo(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=12, color="red")
        ))
    elif geom_type == "line":
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        fig.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(width=6, color="red")
        ))
    elif geom_type == "polygon":
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        if points[0] != points[-1]:
            lats.append(points[0][0])
            lons.append(points[0][1])
        fig.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode="lines",
            fill="toself",
            line=dict(width=3, color="red"),
            fillcolor="red",
            opacity=0.3
        ))
    return fig

###############################################################################
# 9) LEARNING MODE MAP
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

    # Outline only for large polygons
    no_fill_categories = ["Gebirge", "Meere, Meeresteile und Seen", "Inseln/Inselgruppen"]

    sub_df = df[df["category"] == selected_category]
    fig = go.Figure()
    fig.update_layout(
        title=f"Lernmodus: {selected_category}",
        geo=dict(scope="world"),
        height=500
    )

    for _, row in sub_df.iterrows():
        geom_type = row["geometry_type"]
        points = row["geometry_points"]
        feature = row["feature"]
        category = row["category"]

        if geom_type == "point":
            lat, lon = points[0]
            fig.add_trace(go.Scattergeo(
                lat=[lat],
                lon=[lon],
                mode="markers+text",
                text=[feature],
                textposition="top center",
                marker=dict(size=12, color="blue")
            ))
        elif geom_type == "line":
            lats = [p[0] for p in points]
            lons = [p[1] for p in points]
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=4, color="blue")
            ))
            mid_i = len(lats)//2
            fig.add_trace(go.Scattergeo(
                lat=[lats[mid_i]],
                lon=[lons[mid_i]],
                mode="text",
                text=[feature],
                textposition="top center"
            ))
        elif geom_type == "polygon":
            lats = [p[0] for p in points]
            lons = [p[1] for p in points]
            if points[0] != points[-1]:
                lats.append(points[0][0])
                lons.append(points[0][1])
            if category in no_fill_categories:
                # Outline only
                fig.add_trace(go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    line=dict(width=3, color="blue")
                ))
                avg_lat = sum(lats)/len(lats)
                avg_lon = sum(lons)/len(lons)
                fig.add_trace(go.Scattergeo(
                    lat=[avg_lat],
                    lon=[avg_lon],
                    mode="text",
                    text=[feature],
                    textposition="top center"
                ))
            else:
                # Fill smaller polygons
                fig.add_trace(go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    fill="toself",
                    line=dict(width=3, color="blue"),
                    fillcolor="blue",
                    opacity=0.3
                ))
                avg_lat = sum(lats)/len(lats)
                avg_lon = sum(lons)/len(lons)
                fig.add_trace(go.Scattergeo(
                    lat=[avg_lat],
                    lon=[avg_lon],
                    mode="text",
                    text=[feature],
                    textposition="top center"
                ))

    list_text = "Features: " + ", ".join(sub_df["feature"].tolist())
    return fig, list_text

###############################################################################
# RUN
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)
