import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# === Carregar dados do Excel ===
file_path = "relatorio_facebook_ads_2025-09-25.xlsx"
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

# === Detectar a coluna de impressões (o cabeçalho pode vir com acento corrompido) ===
col_impressoes = next((c for c in df.columns if str(c).lower().startswith("impress")), None)

if col_impressoes is None:
    raise ValueError("❌ Não encontrei nenhuma coluna de Impressões na planilha.")


def calcular_ctr(cliques, impressoes):
    # CTR do período = total de cliques / total de impressões (e não a média dos CTRs diários)
    return cliques / impressoes * 100 if impressoes else 0


def calcular_cpc(gasto, cliques):
    # CPC do período = gasto total / total de cliques (e não a média dos CPCs diários)
    return gasto / cliques if cliques else 0


# === Criar app ===
app = dash.Dash(__name__)
server = app.server  # usado por servidores de produção (ex.: gunicorn)
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
    total_impressoes = df_filtrado[col_impressoes].sum()
    ctr_medio = calcular_ctr(total_cliques, total_impressoes)
    cpc_medio = calcular_cpc(total_gasto, total_cliques)

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
    # Soma os totais por campanha e só depois calcula as taxas
    df_comp = df_comparativo.groupby(col_nome, as_index=False).agg({
        col_impressoes: "sum",
        "Cliques": "sum",
        "Gasto (R$)": "sum"
    })
    df_comp["CTR (%)"] = [calcular_ctr(c, i) for c, i in zip(df_comp["Cliques"], df_comp[col_impressoes])]
    df_comp["CPC (R$)"] = [calcular_cpc(g, c) for g, c in zip(df_comp["Gasto (R$)"], df_comp["Cliques"])]
    df_comp[metrica] = df_comp[metrica].round(2)

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
    debug = os.environ.get("DASH_DEBUG", "false").lower() == "true"  # desligado em produção
    app.run(host="0.0.0.0", port=port, debug=debug)



