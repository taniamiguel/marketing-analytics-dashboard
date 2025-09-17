import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# === Carregar dados do Excel ===
file_path = "relatorio_facebook_ads_2025-09-17.xlsx"
df = pd.read_excel(file_path, sheet_name="Campanhas")

# Garantir que a coluna Data é datetime
df["Data"] = pd.to_datetime(df["Data"])

# === Detectar automaticamente a coluna de campanha ===
col_nome = None
for nome in ["Campanha", "Campaign", "campaign_name"]:
    if nome in df.columns:
        col_nome = nome
        break

if col_nome is None:
    raise ValueError("❌ Não encontrei nenhuma coluna de Campanha na planilha.")

# === Criar app ===
app = dash.Dash(__name__)
app.title = "Dashboard Facebook Ads"

# === Layout ===
app.layout = html.Div([
    html.H1("📊 Dashboard Facebook Ads", style={"textAlign": "center"}),

    # Filtros
    html.Div([
        html.Label("Selecione a Campanha:"),
        dcc.Dropdown(
            id="filtro-campanha",
            options=[{"label": camp, "value": camp} for camp in df[col_nome].unique()],
            value=df[col_nome].unique()[0],
            clearable=False
        ),

        html.Label("Selecione o Período:"),
        dcc.DatePickerRange(
            id="filtro-data",
            min_date_allowed=df["Data"].min(),
            max_date_allowed=df["Data"].max(),
            start_date=df["Data"].min(),
            end_date=df["Data"].max()
        ),
    ], style={"width": "40%", "margin": "auto"}),

    html.Br(),

    # KPIs
    html.Div(id="kpis", style={
        "display": "flex",
        "justifyContent": "space-around",
        "marginBottom": "30px"
    }),

    # Gráficos individuais
    html.Div([
        dcc.Graph(id="grafico-cliques"),
        dcc.Graph(id="grafico-gasto")
    ]),

    html.Br(),

    # Gráfico comparativo entre campanhas
    html.Div([
        html.H2("📊 Comparativo Entre Campanhas", style={"textAlign": "center"}),

        # Dropdown de métricas
        html.Label("Selecione a Métrica para Comparação:"),
        dcc.Dropdown(
            id="filtro-metrica",
            options=[
                {"label": "🖱️ Cliques", "value": "Cliques"},
                {"label": "💰 Gasto (R$)", "value": "Gasto (R$)"},
                {"label": "📈 CTR (%)", "value": "CTR (%)"},
                {"label": "🎯 CPC (R$)", "value": "CPC (R$)"}
            ],
            value="Cliques",
            clearable=False
        ),

        dcc.Graph(id="grafico-comparativo")
    ])
])

# === Callbacks ===
@app.callback(
    [Output("grafico-cliques", "figure"),
     Output("grafico-gasto", "figure"),
     Output("grafico-comparativo", "figure"),
     Output("kpis", "children")],
    [Input("filtro-campanha", "value"),
     Input("filtro-data", "start_date"),
     Input("filtro-data", "end_date"),
     Input("filtro-metrica", "value")]
)
def atualizar_dashboard(campanha, start_date, end_date, metrica):
    # Filtrar dados para campanha escolhida
    df_filtrado = df[
        (df[col_nome] == campanha) &
        (df["Data"] >= start_date) &
        (df["Data"] <= end_date)
    ]

    # Filtrar dados para todas as campanhas no mesmo período (comparativo)
    df_comparativo = df[
        (df["Data"] >= start_date) &
        (df["Data"] <= end_date)
    ]

    # === KPIs ===
    total_gasto = df_filtrado["Gasto (R$)"].sum()
    total_cliques = df_filtrado["Cliques"].sum()
    ctr_medio = df_filtrado["CTR (%)"].mean()
    cpc_medio = df_filtrado["CPC (R$)"].mean()

    kpis = [
        html.Div([
            html.H3("💰 Total Gasto"),
            html.P(f"R$ {total_gasto:.2f}")
        ], style={"textAlign": "center"}),

        html.Div([
            html.H3("🖱️ Total Cliques"),
            html.P(f"{total_cliques}")
        ], style={"textAlign": "center"}),

        html.Div([
            html.H3("📈 CTR Médio"),
            html.P(f"{ctr_medio:.2f}%")
        ], style={"textAlign": "center"}),

        html.Div([
            html.H3("🎯 CPC Médio"),
            html.P(f"R$ {cpc_medio:.2f}")
        ], style={"textAlign": "center"}),
    ]

    # === Gráficos individuais ===
    fig_cliques = px.line(
        df_filtrado, x="Data", y="Cliques",
        title=f"📈 Cliques por Dia - {campanha}",
        markers=True
    )

    fig_gasto = px.bar(
        df_filtrado, x="Data", y="Gasto (R$)",
        title=f"💰 Gasto por Dia - {campanha}"
    )

    # === Gráfico comparativo entre campanhas (métrica escolhida) ===
    df_comp = df_comparativo.groupby(col_nome, as_index=False).agg({
        metrica: "mean" if "CTR" in metrica or "CPC" in metrica else "sum"
    })

    fig_comparativo = px.bar(
        df_comp,
        x=col_nome,
        y=metrica,
        title=f"📊 Comparativo Entre Campanhas ({metrica})",
        text=metrica
    )
    fig_comparativo.update_traces(textposition="outside")

    return fig_cliques, fig_gasto, fig_comparativo, kpis


# === Rodar servidor ===
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))  # Render define a porta automaticamente
    app.run(host="0.0.0.0", port=port, debug=True)


