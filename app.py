import json
import random
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

###############################################################################
# 1) LOAD DATA FROM SEPARATE JSON FILES AND MERGE INTO territory_data
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
# 2) BUILD A UNIFIED DATAFRAME FROM territory_data
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

# Add water features from the "gewässer" key
add_category("Meere, Meeresteile und Seen", territory_data["gewässer"]["meere_meeresteile_und_seen"])
add_category("Flüsse", territory_data["gewässer"]["fluesse"])
add_category("Inseln/Inselgruppen", territory_data["gewässer"]["inseln_inselgruppen"])
add_category("Gebirge", territory_data["gewässer"]["gebirge"])

df = pd.DataFrame(data_rows)

###############################################################################
# 3) DASH APP SETUP (Modern Design with LUX theme)
###############################################################################
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])

app.layout = dbc.Container([
    # Hidden Stores for State
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

    # Screen 1: Category Selection
    dbc.Card(
        [
            dbc.CardHeader("Kategorie auswählen", className="bg-secondary text-white"),
            dbc.CardBody([
                html.P("Wähle eine Kategorie:", className="card-text"),
                dcc.Dropdown(
                    id="category-dropdown",
                    options=[
                        {"label": "Alle", "value": "Alle"},
                        {"label": "Meere, Meeresteile und Seen", "value": "Meere, Meeresteile und Seen"},
                        {"label": "Flüsse", "value": "Flüsse"},
                        {"label": "Inseln/Inselgruppen", "value": "Inseln/Inselgruppen"},
                        {"label": "Gebirge", "value": "Gebirge"}
                    ],
                    placeholder="Kategorie auswählen...",
                    style={"maxWidth": "300px"}
                ),
                dbc.Button("Spiel starten", id="start-button", n_clicks=0, color="success", className="mt-3")
            ])
        ],
        id="category-selection-card",
        style={"maxWidth": "600px", "margin": "0 auto 2rem auto"}
    ),

    # Screen 2: Quiz
    dbc.Card(
        [
            dbc.CardHeader("Ratespiel", className="bg-secondary text-white"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Welches Feature ist hervorgehoben?", style={"fontWeight": "bold"}),
                        dcc.Dropdown(id="feature-guess-dropdown", style={"width": "100%", "maxWidth": "300px"}),
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
    )
], fluid=True)

###############################################################################
# 4) SCREEN SWITCHING: Show category selection or quiz screen
###############################################################################
@app.callback(
    Output("category-selection-card", "style"),
    Output("quiz-card", "style"),
    Input("store-selected-category", "data")
)
def switch_screens(selected_category):
    if selected_category is None:
        return {"maxWidth": "600px", "margin": "0 auto 2rem auto"}, {"display": "none"}
    else:
        return {"display": "none"}, {"maxWidth": "900px", "margin": "0 auto 2rem auto"}

###############################################################################
# 5) SINGLE CALLBACK FOR "Spiel starten" & "Zurück zum Menü"
###############################################################################
@app.callback(
    Output("store-selected-category", "data"),
    Input("start-button", "n_clicks"),
    Input("back-button", "n_clicks"),
    State("category-dropdown", "value")
)
def set_or_reset_category(n_start, n_back, chosen_category):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig_id == "start-button" and chosen_category:
        return chosen_category
    elif trig_id == "back-button":
        return None
    return no_update

###############################################################################
# 6) QUIZ LOGIC: Initialize quiz, check guesses, update scores, etc.
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
    elapsed = now - start_time if start_time is not None else 0
    elapsed_str = f"{int(elapsed)} s" if elapsed < 120 else f"{int(elapsed // 60)} min {int(elapsed % 60)} s"

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
# 7) UPDATE MAP: Draw feature geometry based on its type.
# For large features (e.g. "Indik (Indischer Ozean)", "Neuguinea", "Grönland", "Island")
# we draw only the outline (no fill) to avoid covering the map.
###############################################################################
@app.callback(
    Output("blind-map", "figure"),
    Input("store-selected-feature", "data")
)
def update_map(selected_feature):
    if not selected_feature:
        fig = px.scatter(x=[0], y=[0], title="Bitte wähle ein Feature und starte das Ratespiel.")
        fig.update_layout(height=400)
        return fig

    row = df[df["feature"] == selected_feature]
    if row.empty:
        geom_type = "point"
        points = []
        category = ""
    else:
        geom_type = row.iloc[0]["geometry_type"]
        points = row.iloc[0]["geometry_points"]
        category = row.iloc[0]["category"]

    fig = go.Figure()
    fig.update_layout(
        title="Blind Map - Ratespiel",
        geo=dict(scope="world"),
        height=500
    )

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
        # For "Gebirge" and for large features that would cover the map,
        # we want to draw only the outline.
        no_fill_features = ["Indik (Indischer Ozean)", "Neuguinea", "Grönland", "Island"]
        if (category == "Gebirge") or (selected_feature in no_fill_features):
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=3, color="red")
            ))
        else:
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
# 8) RUN SERVER
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)
