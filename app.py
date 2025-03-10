import json
import random
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

###############################################################################
# 1) LOAD DATA FROM JSON
###############################################################################
with open("territory.json", "r", encoding="utf-8") as f:
    territory_data = json.load(f)

# Build a unified DataFrame from the JSON data
data_rows = []

# Category: Meere, Meeresteile und Seen
cat_name = "Meere, Meeresteile und Seen"
data = territory_data["gewässer"]["meere_meeresteile_und_seen"]["data"]
coords = territory_data["gewässer"]["meere_meeresteile_und_seen"]["coords"]
for feature in data:
    lat = coords.get(feature, {}).get("lat", None)
    lon = coords.get(feature, {}).get("lon", None)
    data_rows.append({"category": cat_name, "feature": feature, "lat": lat, "lon": lon})

# Category: Flüsse
cat_name = "Flüsse"
data = territory_data["gewässer"]["fluesse"]["data"]
coords = territory_data["gewässer"]["fluesse"]["coords"]
for feature in data:
    lat = coords.get(feature, {}).get("lat", None)
    lon = coords.get(feature, {}).get("lon", None)
    data_rows.append({"category": cat_name, "feature": feature, "lat": lat, "lon": lon})

# Category: Inseln/Inselgruppen
cat_name = "Inseln/Inselgruppen"
data = territory_data["inseln_inselgruppen"]["data"]
coords = territory_data["inseln_inselgruppen"]["coords"]
for feature in data:
    lat = coords.get(feature, {}).get("lat", None)
    lon = coords.get(feature, {}).get("lon", None)
    data_rows.append({"category": cat_name, "feature": feature, "lat": lat, "lon": lon})

# Category: Gebirge
cat_name = "Gebirge"
data = territory_data["gebirge"]["data"]
coords = territory_data["gebirge"]["coords"]
for feature in data:
    lat = coords.get(feature, {}).get("lat", None)
    lon = coords.get(feature, {}).get("lon", None)
    data_rows.append({"category": cat_name, "feature": feature, "lat": lat, "lon": lon})

df = pd.DataFrame(data_rows)

###############################################################################
# 2) DASH APP SETUP (MODERN THEME, LAYOUT)
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

    # Screen 1: Category selection
    dbc.Card(
        [
            dbc.CardHeader("Kategorie auswählen", className="bg-secondary text-white"),
            dbc.CardBody([
                html.P("Wähle eine Kategorie:", className="card-text"),
                dcc.Dropdown(
                    id="category-dropdown",
                    options=[
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
                        html.Label("Welches Feature ist rot markiert?", style={"fontWeight": "bold"}),
                        dcc.Dropdown(id="feature-guess-dropdown", style={"width": "100%", "maxWidth": "300px"}),
                        dbc.Button("Tipp absenden", id="guess-button", n_clicks=0, color="primary", className="mt-2"),
                        html.Div(id="guess-result", style={"marginTop": "1em", "fontWeight": "bold", "color": "#333"}),
                    ], md=4),
                    dbc.Col([
                        dcc.Graph(id="blind-map", style={"height": "500px"})
                    ], md=8),
                ]),
                html.Hr(),
                html.Div(id="score-display", className="mt-3 text-center"),
                html.Div(id="lists-display", className="mt-3 text-center"),
                dbc.Button("Neu starten", id="reset-button", n_clicks=0, color="warning", className="mt-3")
            ])
        ],
        id="quiz-card",
        style={"maxWidth": "900px", "margin": "0 auto 2rem auto", "display": "none"}
    )
], fluid=True)

###############################################################################
# 3) SCREEN SWITCHING
###############################################################################
@app.callback(
    Output("category-selection-card", "style"),
    Output("quiz-card", "style"),
    Input("store-selected-category", "data")
)
def switch_screens(selected_category):
    """
    Show the category menu if no category is chosen.
    Otherwise, show the quiz screen.
    """
    if selected_category is None:
        return (
            {"maxWidth": "600px", "margin": "0 auto 2rem auto"},
            {"display": "none"}
        )
    else:
        return (
            {"display": "none"},
            {"maxWidth": "900px", "margin": "0 auto 2rem auto"}
        )

###############################################################################
# 4) SET CATEGORY (start-button callback)
###############################################################################
@app.callback(
    Output("store-selected-category", "data"),
    Input("start-button", "n_clicks"),
    State("category-dropdown", "value")
)
def start_game(n_clicks, selected_category):
    """
    When user clicks 'Spiel starten', store the selected category.
    The quiz logic callback will handle the rest.
    """
    if n_clicks and selected_category:
        return selected_category
    return no_update

###############################################################################
# 5) QUIZ LOGIC (guess-button, reset-button, and category changes)
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
    """
    Main quiz logic. Triggered by:
      - Category chosen (store-selected-category)
      - Neu starten
      - Tipp absenden
    """

    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, "", no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    now = time.time()
    trig_id = ctx.triggered[0]["prop_id"].split(".")[0]
    message = ""

    # If category is not selected, do nothing
    if selected_category is None:
        return no_update, no_update, "", correct_count, wrong_count, done_features, remaining_features, no_update, no_update, no_update, start_time

    # If we haven't initialized the quiz yet (remaining_features is empty),
    # or the user clicks "Neu starten," do the initialization.
    if (not remaining_features) or (trig_id == "reset-button"):
        remaining_features = df[df["category"] == selected_category]["feature"].tolist()
        current_feature = random.choice(remaining_features) if remaining_features else None
        done_features = []
        correct_count = 0
        wrong_count = 0
        start_time = now
        if trig_id == "reset-button":
            message = "Ratespiel neu gestartet!"

    # If user clicked "Tipp absenden"
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

    # Build new dropdown options
    dropdown_options = [{"label": f, "value": f} for f in remaining_features]

    # Calculate elapsed time
    if start_time is None:
        elapsed = 0
    else:
        elapsed = now - start_time

    if elapsed < 120:
        elapsed_str = f"{int(elapsed)} s"
    else:
        elapsed_str = f"{int(elapsed // 60)} min {int(elapsed % 60)} s"

    # Build score display
    score_display = dbc.Card(
        dbc.CardBody([
            html.H5("Aktueller Punktestand", className="card-title"),
            html.P(f"Korrekt: {correct_count}", style={"margin": 0}),
            html.P(f"Falsch: {wrong_count}", style={"margin": 0}),
            html.P(f"Zeit: {elapsed_str}", style={"margin": 0, "marginTop": 8, "fontStyle": "italic"})
        ]),
        className="border p-2 d-inline-block"
    )

    # Build lists display
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
        dropdown_options,          # feature-guess-dropdown.options
        current_feature,           # store-selected-feature.data
        message,                   # guess-result.children
        correct_count,             # store-correct-count.data
        wrong_count,               # store-wrong-count.data
        done_features,             # store-done-features.data
        remaining_features,        # store-remaining-features.data
        score_display,             # score-display.children
        lists_display,             # lists-display.children
        None,                      # feature-guess-dropdown.value (reset selection)
        start_time                 # store-start-time.data
    )

###############################################################################
# 6) UPDATE MAP
###############################################################################
@app.callback(
    Output("blind-map", "figure"),
    Input("store-selected-feature", "data")
)
def update_map(selected_feature):
    """
    Plot the currently selected feature on a world map in red.
    """
    if not selected_feature:
        # Show an empty map with a note
        fig = px.scatter(
            x=[0], y=[0],
            title="Bitte wähle ein Feature und starte das Ratespiel."
        )
        fig.update_layout(height=400)
        return fig

    row = df[df["feature"] == selected_feature]
    if row.empty:
        coords = {"lat": 0, "lon": 0}
    else:
        coords = {"lat": row.iloc[0]["lat"], "lon": row.iloc[0]["lon"]}

    fig = px.scatter_geo(
        lat=[coords["lat"]],
        lon=[coords["lon"]],
        scope="world",
        title="Blind Map - Ratespiel",
        height=500
    )
    fig.update_traces(marker=dict(size=20, color="red"))
    return fig

###############################################################################
# 7) RUN SERVER
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)
