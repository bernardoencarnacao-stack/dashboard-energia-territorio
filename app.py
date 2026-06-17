import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import seaborn as sns
import json
import unicodedata
from pathlib import Path

try:
    import plotly.express as px
    HAS_PLOTLY = True
except Exception:
    px = None
    HAS_PLOTLY = False

st.set_page_config(page_title="Dashboard Energético Municipal", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* Fundo geral */
    .stApp {
        background: #0d0617;
        color: #f4ecff;
    }

    /* Conteúdo principal */
    .block-container {
        background: #0d0617;
        color: #f4ecff;
        padding-top: 1.4rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #261142 0%, #12071f 100%);
        border-right: 1px solid #3a1b63;
    }
    section[data-testid="stSidebar"] * {
        color: #f4ecff !important;
    }

    /* Títulos e texto */
    h1, h2, h3, h4, h5, h6, p, label, span, div {
        color: #f4ecff;
    }

    /* Métricas/cards */
    div[data-testid="stMetric"] {
        background: #180d27;
        border: 1px solid #3d2360;
        border-left: 5px solid #9b5de5;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0px 2px 12px rgba(0,0,0,0.28);
    }

    /* Widgets principais */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="popover"] div,
    div[data-baseweb="textarea"] textarea {
        background-color: #1b102b !important;
        color: #f4ecff !important;
        border-color: #7b2cbf !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div,
    div[data-baseweb="input"] input {
        color: #f4ecff !important;
    }

    /* Multiselect tags/chips */
    span[data-baseweb="tag"] {
        background-color: #7b2cbf !important;
        color: white !important;
    }

    /* Radio/check */
    div[role="radiogroup"] label {
        background-color: rgba(155, 93, 229, 0.12);
        border: 1px solid rgba(155, 93, 229, 0.25);
        border-radius: 8px;
        padding: 5px 8px;
        margin-right: 4px;
    }
    div[role="radiogroup"] label:hover {
        background-color: rgba(155, 93, 229, 0.25);
    }

    /* Botões */
    .stButton button {
        background-color: #7b2cbf;
        color: white;
        border-radius: 8px;
        border: 0;
    }
    .stButton button:hover {
        background-color: #9b5de5;
        color: white;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: #140b22;
        border-radius: 8px;
    }

    /* Separadores */
    hr {
        border-color: #3d2360;
    }

    /* Alert/info boxes */
    div[data-testid="stAlert"] {
        background-color: #1b102b;
        color: #f4ecff;
        border: 1px solid #7b2cbf;
    }
</style>
""", unsafe_allow_html=True)

sns.set_theme(style="whitegrid")
plt.rcParams["figure.dpi"] = 105

DATA = Path("data")
DATASET = DATA / "dataset_final_unificado.xlsx"
CLUSTERS_CSV = DATA / "concelhos_clusters_portugal.csv"
CLUSTERS_XLSX = DATA / "concelhos_clusters_portugal.xlsx"
UPACS_FILE = DATA / "upacs_tratado.xlsx"
CAOP = DATA / "Continente_CAOP2025.gpkg"

DISTRITOS_ESTUDADOS = ["Faro", "Setúbal", "Aveiro", "Castelo Branco"]
OUTLIERS_PC = {"Faro": [], "Setúbal": ["Sines"], "Aveiro": ["Estarreja"], "Castelo Branco": ["Vila Velha de Ródão"]}

CLUSTER_LABELS = {
    1: "Rurais e Periféricos",
    2: "Urbanos de Perfil Médio",
    3: "Polos Industriais MAT",
    4: "Zona Metropolitana Densa",
    5: "Industrial Extremo"
}
CLUSTER_DESCRICOES = {
    1: "Concelhos de baixa densidade, mais rurais/interiores, com consumo absoluto moderado e forte efeito de escala nas métricas relativas.",
    2: "Concelhos com perfil energético equilibrado, consumo doméstico e urbano relevante, sem valores extremos de MAT ou per capita.",
    3: "Polos industriais onde a energia em Muito Alta Tensão e o consumo per capita se destacam face à dimensão populacional.",
    4: "Concelhos metropolitanos densos, com muitos residentes, muitos CPEs e forte peso do consumo urbano/residencial em BT.",
    5: "Caso singular extremo, dominado por indústria pesada, porto, logística e petroquímica, com valores muito acima dos restantes concelhos."
}
CLUSTER_DETERMINANTES = {
    1: "Determinantes principais: baixa densidade populacional, dispersão territorial, CPEs relativos elevados por efeito de escala e menor intensidade industrial/MAT.",
    2: "Determinantes principais: consumo per capita intermédio, predominância da BT, estrutura municipal equilibrada e adoção de UPAC sem valores extremos.",
    3: "Determinantes principais: Energia_MAT_per_capita muito elevada, consumo per capita alto e presença de grandes consumidores industriais.",
    4: "Determinantes principais: densidade populacional, CPEs totais elevados, consumo urbano em BT e peso residencial/metropolitano.",
    5: "Determinantes principais: Energia_Ativa_Total e Energia_MAT_per_capita extremas, grande atividade industrial/portuária e forte afastamento estatístico dos restantes concelhos."
}
CLUSTER_CORES = {1: "#1f77b4", 2: "#2ca02c", 3: "#9467bd", 4: "#e377c2", 5: "#bcbd22"}

VAR_GROUPS = {
    "Variáveis absolutas": {
        "Energia_Ativa_Total": "Energia Ativa Total",
        "Energia_BT": "Energia BT",
        "Energia_MAT": "Energia MAT",
        "CPEs_Total": "CPEs Total",
        "UPACs_Total": "UPACs Total",
        "Ligacoes_Total": "Ligações à rede",
    },
    "Variáveis relativas": {
        "Consumo_per_capita": "Consumo per capita",
        "Energia_BT_per_capita": "Energia BT per capita",
        "Energia_MAT_per_capita": "Energia MAT per capita",
        "CPEs_por_1000_hab": "CPEs por 1000 habitantes",
        "UPACs_por_1000_hab": "UPACs por 1000 habitantes",
    },
    "Proporções": {
        "Prop_energia_BT": "Proporção Energia BT",
        "Prop_energia_MAT": "Proporção Energia MAT",
        "Prop_CPEs_BT": "Proporção CPEs BT",
        "Prop_CPEs_MAT": "Proporção CPEs MAT",
        "Prop_UPACs_BT": "Proporção UPACs BT",
        "Prop_UPACs_MT": "Proporção UPACs MT",
        "Prop_Domestico": "Proporção CPEs domésticos",
    },
    "Variáveis climáticas": {
        "Temp_Media_Mensal": "Temperatura média mensal",
        "Precipitacao_Total_Mensal": "Precipitação total mensal",
        "Radiacao_Global_Total_Mensal": "Radiação global total mensal",
        "Humidade_Relativa_Media_Mensal": "Humidade relativa média mensal",
    },
    "Qualidade de serviço": {
        "SAIFI_AT": "SAIFI AT", "SAIDI_AT": "SAIDI AT", "MAIFI_AT": "MAIFI AT",
        "SAIFI_MT": "SAIFI MT", "SAIDI_MT": "SAIDI MT", "MAIFI_MT": "MAIFI MT",
        "SAIFI_BT": "SAIFI BT", "SAIDI_BT": "SAIDI BT",
    }
}

MAP_CM = {
    "Energia_Ativa_Total": "YlOrRd", "Consumo_per_capita": "YlOrRd",
    "CPEs_por_1000_hab": "Greens", "UPACs_por_1000_hab": "Purples",
    "Energia_BT_per_capita": "Blues", "Energia_MAT_per_capita": "RdPu",
    "CPEs_Total": "Greens", "UPACs_Total": "Purples", "Energia_BT": "Blues", "Energia_MAT": "RdPu",
}
SUM_VARS = {"Energia_Ativa_Total", "Energia_BT", "Energia_MAT", "Ligacoes_Total"}
CLIMA_VARS = {"Temp_Media_Mensal", "Precipitacao_Total_Mensal", "Radiacao_Global_Total_Mensal", "Humidade_Relativa_Media_Mensal"}
QUALIDADE_VARS = {"SAIFI_AT", "SAIDI_AT", "MAIFI_AT", "SAIFI_MT", "SAIDI_MT", "MAIFI_MT", "SAIFI_BT", "SAIDI_BT"}

CPE_VARS = {
    "CPEs_Total", "CPEs_BT", "CPEs_MAT", "CPEs_Doméstico", "CPEs_Domestico",
    "CPEs_Não_Doméstico", "CPEs_Nao_Domestico", "CPEs_Iluminacao_Publica",
    "CPEs_Outros", "CPEs_por_1000_hab", "Prop_Domestico", "Prop_CPEs_BT", "Prop_CPEs_MAT"
}
UPAC_VARS = {
    "UPACs_Total", "UPACs_BT", "UPACs_MT", "UPACs_por_1000_hab", "UPAC_por_1000_CPEs",
    "Prop_UPACs_BT", "Prop_UPACs_MT", "Potência Total Instalada UPAC (kW)"
}
ABS_STOCK_VARS = {
    "CPEs_Total", "CPEs_BT", "CPEs_MAT", "CPEs_Doméstico", "CPEs_Domestico",
    "CPEs_Não_Doméstico", "CPEs_Nao_Domestico", "CPEs_Iluminacao_Publica", "CPEs_Outros",
    "UPACs_Total", "UPACs_BT", "UPACs_MT", "Potência Total Instalada UPAC (kW)"
}
REL_STOCK_VARS = (CPE_VARS | UPAC_VARS) - ABS_STOCK_VARS
TEMPORAL_COLS = {"Data", "Data_Periodo", "Data_Trimestre", "Mês", "Mes", "Ano", "Trimestre_Num"}


def norm_name(x):
    if pd.isna(x):
        return x
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x)
    return "".join(c for c in x if not unicodedata.combining(c))


def label_var(v):
    for g in VAR_GROUPS.values():
        if v in g:
            return g[v]
    return v


def discrete_palette(names):
    """Paleta categórica com cores discretas e mais distinguíveis do que rainbow/husl."""
    names = list(names)
    base = []
    for pal in ["tab20", "tab20b", "tab20c", "Set3", "Dark2"]:
        base.extend(sns.color_palette(pal))
    if len(names) > len(base):
        base = sns.color_palette("cubehelix", len(names), rot=-.25, light=.75)
    else:
        base = base[:len(names)]
    return dict(zip(names, base))


def mes_labels():
    return {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}


def showfig(fig):
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def read_table(path):
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_excel(path) if path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_df(path):
    df = read_table(path)
    if df is None:
        return None
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    if "Ano" in df.columns:
        df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
    if "Mês" in df.columns:
        df["Mês"] = pd.to_numeric(df["Mês"], errors="coerce").astype("Int64")
    df["Distrito_norm"] = df["Distrito"].apply(norm_name)
    df["Concelho_norm"] = df["Concelho"].apply(norm_name)
    if "Populacao_Residente" in df.columns:
        if "Energia_BT" in df.columns and "Energia_BT_per_capita" not in df.columns:
            df["Energia_BT_per_capita"] = df["Energia_BT"] / df["Populacao_Residente"]
        if "Energia_MAT" in df.columns and "Energia_MAT_per_capita" not in df.columns:
            df["Energia_MAT_per_capita"] = df["Energia_MAT"] / df["Populacao_Residente"]
        if "CPEs_Total" in df.columns and "CPEs_por_1000_hab" not in df.columns:
            df["CPEs_por_1000_hab"] = df["CPEs_Total"] / df["Populacao_Residente"] * 1000
        if "UPACs_Total" in df.columns and "UPACs_por_1000_hab" not in df.columns:
            df["UPACs_por_1000_hab"] = df["UPACs_Total"] / df["Populacao_Residente"] * 1000
    return df


@st.cache_data(show_spinner=False)
def load_upacs(path, df_ref):
    """Carrega o ficheiro trimestral de UPACs.

    Este ficheiro evita a visualização em "escadinha" que aparece quando se usa
    o dataset unificado mensal, onde os valores trimestrais foram replicados por 3 meses.
    """
    up = read_table(path)
    if up is None:
        return None

    up = up.copy()
    up.columns = [str(c).strip() for c in up.columns]
    rename = {
        "Código Distrito": "Codigo_Distrito",
        "Código Concelho": "Codigo_Concelho",
        "Codigo Distrito": "Codigo_Distrito",
        "Codigo Concelho": "Codigo_Concelho",
    }
    up = up.rename(columns={k: v for k, v in rename.items() if k in up.columns})

    if "Distrito" not in up.columns or "Concelho" not in up.columns:
        return None

    up["Distrito_norm"] = up["Distrito"].apply(norm_name)
    up["Concelho_norm"] = up["Concelho"].apply(norm_name)

    if "Trimestre" in up.columns:
        tri = up["Trimestre"].astype(str).str.upper().str.replace(" ", "", regex=False).str.replace("º", "", regex=False)
        ano = tri.str.extract(r"(20\d{2})", expand=False)
        q1 = tri.str.extract(r"[TQ]([1-4])", expand=False)
        q2 = tri.str.extract(r"([1-4])[TQ]", expand=False)
        q = q1.fillna(q2)
        up["Ano"] = pd.to_numeric(up.get("Ano", ano), errors="coerce").fillna(pd.to_numeric(ano, errors="coerce")).astype("Int64")
        up["Trimestre_Num"] = pd.to_numeric(q, errors="coerce").astype("Int64")
    else:
        if "Ano" in up.columns:
            up["Ano"] = pd.to_numeric(up["Ano"], errors="coerce").astype("Int64")
        if "Trimestre_Num" not in up.columns:
            up["Trimestre_Num"] = pd.NA

    up["Periodo_Label"] = up["Ano"].astype("Int64").astype(str) + "T" + up["Trimestre_Num"].astype("Int64").astype(str)
    up.loc[up["Ano"].isna() | up["Trimestre_Num"].isna(), "Periodo_Label"] = pd.NA
    up["Data_Periodo"] = pd.NaT
    ok = up["Ano"].notna() & up["Trimestre_Num"].notna()
    if ok.any():
        up.loc[ok, "Data_Periodo"] = pd.PeriodIndex(
            up.loc[ok, "Ano"].astype(int).astype(str) + "Q" + up.loc[ok, "Trimestre_Num"].astype(int).astype(str),
            freq="Q"
        ).to_timestamp()
    up["Data"] = up["Data_Periodo"]

    # Junta população anual do dataset unificado para calcular UPACs por 1000 habitantes.
    if "UPACs_por_1000_hab" not in up.columns and "UPACs_Total" in up.columns and df_ref is not None and "Populacao_Residente" in df_ref.columns:
        pop_cols = ["Ano", "Distrito_norm", "Concelho_norm", "Populacao_Residente"]
        pop = df_ref[pop_cols].dropna(subset=["Ano", "Populacao_Residente"]).drop_duplicates(subset=["Ano", "Distrito_norm", "Concelho_norm"])
        up = up.merge(pop, on=["Ano", "Distrito_norm", "Concelho_norm"], how="left")
        up["UPACs_por_1000_hab"] = up["UPACs_Total"] / up["Populacao_Residente"] * 1000

    # Garante colunas numéricas para variáveis UPAC.
    for c in UPAC_VARS:
        if c in up.columns:
            up[c] = pd.to_numeric(up[c], errors="coerce")

    return up


def add_quarter_columns(d):
    d = d.copy()
    if "Data" in d.columns and not pd.api.types.is_datetime64_any_dtype(d["Data"]):
        d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    if "Data" in d.columns:
        d["Data_Trimestre"] = d["Data"].dt.to_period("Q").dt.to_timestamp()
        d["Trimestre_Num"] = d["Data"].dt.quarter.astype("Int64")
        d["Periodo_Label"] = d["Data"].dt.to_period("Q").astype(str).str.replace("Q", "T", regex=False)
    return d


def data_for_var(var, df_main, df_upacs):
    if is_upac_var(var) and df_upacs is not None and var in df_upacs.columns:
        return df_upacs.copy(), True
    d = df_main.copy()
    if is_cpe_var(var):
        d = add_quarter_columns(d)
    return d, False


@st.cache_data(show_spinner=False)
def load_clusters(csv_path, xlsx_path):
    cl = read_table(csv_path) if Path(csv_path).exists() else read_table(xlsx_path)
    if cl is None:
        return None
    cl["Distrito_norm"] = cl["Distrito"].apply(norm_name)
    cl["Concelho_norm"] = cl["Concelho"].apply(norm_name)
    cl["Cluster"] = pd.to_numeric(cl["Cluster"], errors="coerce").astype("Int64")
    if "Nome_Cluster" not in cl.columns:
        cl["Nome_Cluster"] = cl["Cluster"].map(CLUSTER_LABELS)
    return cl


@st.cache_data(show_spinner=False)
def load_geo(path):
    if not Path(path).exists():
        return None, None, None
    gd = gpd.read_file(path, layer="cont_distritos")
    gc = gpd.read_file(path, layer="cont_municipios")
    gd["Distrito_norm"] = gd["distrito"].apply(norm_name)
    gc["Distrito_norm"] = gc["distrito_ilha"].apply(norm_name)
    gc["Concelho_norm"] = gc["municipio"].apply(norm_name)
    try:
        gc_wgs = gc.to_crs(epsg=4326)
    except Exception:
        gc_wgs = gc.copy()
    return gd, gc, gc_wgs


def is_cpe_var(v):
    return v in CPE_VARS or v.startswith("CPEs_") or v.startswith("Prop_CPEs") or v == "Prop_Domestico"


def is_upac_var(v):
    return v in UPAC_VARS or v.startswith("UPAC") or v.startswith("Prop_UPAC") or "UPAC" in v


def is_stock_var(v):
    return is_cpe_var(v) or is_upac_var(v)


def is_quality_var(v):
    return v in QUALIDADE_VARS


def is_climate_var(v):
    return v in CLIMA_VARS


def is_abs_stock_var(v):
    return v in ABS_STOCK_VARS


def agg_rule(v):
    if v in SUM_VARS:
        return "sum"
    if v in CLIMA_VARS:
        return "first"
    return "mean"


def _period_col_for_agg(df):
    for c in ["Data_Periodo", "Data_Trimestre", "Data"]:
        if c in df.columns:
            return c
    return None


def agg(df, keys, var):
    keys = list(keys)
    if df is None or df.empty or var not in df.columns:
        return pd.DataFrame(columns=keys + [var])

    # CPEs e UPACs são variáveis de stock/contagem replicadas no tempo.
    # Para evitar valores inflacionados, quando não há dimensão temporal explícita
    # calcula-se primeiro o valor por período e depois a média dos períodos.
    if is_stock_var(var):
        temporal_in_keys = any(k in TEMPORAL_COLS for k in keys)
        if is_abs_stock_var(var):
            if temporal_in_keys:
                return df.groupby(keys, as_index=False)[var].sum(min_count=1)
            pcol = _period_col_for_agg(df)
            if pcol and pcol not in keys:
                tmp = df.groupby(keys + [pcol], as_index=False)[var].sum(min_count=1)
                return tmp.groupby(keys, as_index=False)[var].mean()
            return df.groupby(keys, as_index=False)[var].mean()
        else:
            return df.groupby(keys, as_index=False)[var].mean()

    return df.groupby(keys, as_index=False)[var].agg(agg_rule(var))


def scale_var(s, var):
    mx = s.max(skipna=True)
    if var in ["Energia_Ativa_Total", "Energia_BT", "Energia_MAT"]:
        if mx >= 1_000_000_000:
            return s / 1_000_000_000, "GWh"
        if mx >= 1_000_000:
            return s / 1_000_000, "MWh"
        if mx >= 1_000:
            return s / 1_000, "kWh x10³"
        return s, "kWh"
    if var in ["Consumo_per_capita", "Energia_BT_per_capita", "Energia_MAT_per_capita"]:
        return (s / 1000, "MWh/habitante") if mx >= 1000 else (s, "kWh/habitante")
    if var == "CPEs_por_1000_hab":
        return s, "por 1000 hab."
    if var == "UPACs_por_1000_hab":
        return s, "por 1000 hab."
    if var in ["CPEs_Total", "CPEs_BT", "CPEs_MAT", "UPACs_Total", "UPACs_BT", "UPACs_MT"]:
        if mx >= 1_000_000:
            return s / 1_000_000, "milhões"
        if mx >= 1_000:
            return s / 1_000, "milhares"
        return s, "n.º"
    if var == "Potência Total Instalada UPAC (kW)":
        if mx >= 1_000_000:
            return s / 1_000_000, "GW"
        if mx >= 1_000:
            return s / 1_000, "MW"
        return s, "kW"
    if var == "UPAC_por_1000_CPEs":
        return s, "por 1000 CPEs"
    if var.startswith("Prop_"):
        return s * 100, "%"
    if var == "Temp_Media_Mensal":
        return s, "°C"
    if var == "Precipitacao_Total_Mensal":
        return s, "mm"
    if var == "Radiacao_Global_Total_Mensal":
        return s, "kWh/m²"
    if var == "Humidade_Relativa_Media_Mensal":
        return s, "%"
    return s, ""


def display_label(var, unit=""):
    if var == "CPEs_por_1000_hab":
        return "Nº de CPEs por 1000 habitantes"
    if var == "UPACs_por_1000_hab":
        return "Nº de UPACs por 1000 habitantes"
    return f"{label_var(var)} ({unit})" if unit else label_var(var)


def climate_color(var):
    cores = {
        "Humidade_Relativa_Media_Mensal": "green",
        "Precipitacao_Total_Mensal": "cyan",
        "Radiacao_Global_Total_Mensal": "gold",
        "Temp_Media_Mensal": "tab:red",
    }
    return cores.get(var, "tab:red")


def add_labels(ax, gdf, col, fs=5):
    for _, r in gdf.iterrows():
        if r.geometry is not None and not r.geometry.is_empty:
            p = r.geometry.representative_point()
            ax.text(p.x, p.y, str(r[col]), fontsize=fs, ha="center", va="center", color="#222")


def choose_var(df, key):
    groups = {g: {k: v for k, v in d.items() if k in df.columns} for g, d in VAR_GROUPS.items()}
    groups = {g: d for g, d in groups.items() if d}

    options = []
    labels = {}
    valid_vars = []

    for group_name, vars_dict in groups.items():
        sep = f"──────── {group_name} ────────"
        options.append(sep)
        labels[sep] = sep
        for var, label in vars_dict.items():
            options.append(var)
            labels[var] = label
            valid_vars.append(var)

    default_index = options.index(valid_vars[0]) if valid_vars else 0

    selected = st.selectbox(
        "Variável",
        options,
        index=default_index,
        format_func=lambda x: labels.get(x, x),
        key=f"{key}_var"
    )

    if selected not in valid_vars:
        st.info("Seleciona uma variável concreta abaixo do separador.")
        return valid_vars[0]

    return selected


def choose_years(df, key, var=None):
    anos = sorted([int(x) for x in df["Ano"].dropna().unique()]) if "Ano" in df.columns else []
    if var and (is_cpe_var(var) or is_upac_var(var)):
        anos = [a for a in anos if a >= 2022]
    return st.multiselect("Ano", anos, default=anos, key=key)


def default_districts(options):
    opts = list(options)
    return [d for d in DISTRITOS_ESTUDADOS if d in opts]


def empty_selection_message(kind="distrito"):
    st.info(f"Seleciona pelo menos um {kind} para gerar a visualização.")


def remove_pc_outliers(df):
    out = df.copy()
    for d, cs in OUTLIERS_PC.items():
        dn = norm_name(d)
        cn = [norm_name(c) for c in cs]
        out = out[~((out["Distrito_norm"] == dn) & (out["Concelho_norm"].isin(cn)))].copy()
    return out


def pc_limits(scaled_series):
    vals = pd.Series(scaled_series).dropna()
    if vals.empty:
        return None, None

    # Os valores já estão em MWh/hab. quando o consumo per capita é elevado.
    # Como os outliers extremos ficam a azul, a escala normal fica propositadamente
    # mais curta para evidenciar diferenças entre os restantes concelhos.
    vmin = max(0.0, float(vals.quantile(0.02)) * 0.95)

    # Cap robusto: evita que concelhos altos, mas não marcados como outlier,
    # continuem a comprimir visualmente os restantes.
    robust = float(vals.quantile(0.68))
    vmax = min(0.55, robust)

    # Segurança para casos em que os dados filtrados têm valores muito baixos/iguais.
    if pd.isna(vmax) or vmax <= vmin:
        vmax = min(0.55, float(vals.max()))
    if vmax <= vmin:
        vmax = float(vals.max())
        vmin = float(vals.min())

    return float(vmin), float(vmax)



def format_time_axis(ax):
    """Evita labels temporais encavalitadas no eixo X."""
    try:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%Y"))
    except Exception:
        pass
    ax.tick_params(axis="x", labelrotation=45, labelsize=7)


def temporal_key_for_plot(df, var, saz=False):
    if saz:
        if is_upac_var(var) and "Trimestre_Num" in df.columns:
            return "Trimestre_Num", "Trimestre"
        return "Mês", "Mês"
    if is_upac_var(var) and "Data_Periodo" in df.columns:
        return "Data_Periodo", "Trimestre"
    if is_cpe_var(var) and "Data_Trimestre" in df.columns:
        return "Data_Trimestre", "Trimestre"
    return "Data", "Data"

# ============================================================
# PLOTS
# ============================================================

def climate_axis_label(var):
    _, unit = scale_var(pd.Series([1.0]), var)
    return f"{label_var(var)} ({unit})" if unit else label_var(var)


def climate_vs_consumption_district(df, climate_var, distrito, saz=False):
    d = df[df["Distrito"] == distrito].copy()
    if d.empty:
        st.info("Sem dados para o distrito selecionado."); return
    x = "Mês" if saz else "Data"
    if x not in d.columns:
        st.info("Não existe dimensão temporal adequada para esta comparação."); return

    cons = agg(d, [x, "Distrito"], "Energia_Ativa_Total")
    clim = agg(d, [x, "Distrito"], climate_var)
    t = cons.merge(clim, on=[x, "Distrito"], how="inner")
    if t.empty:
        st.info("Sem dados suficientes para cruzar consumo e clima."); return

    t["Consumo"], cons_unit = scale_var(t["Energia_Ativa_Total"], "Energia_Ativa_Total")
    t["Clima"], clim_unit = scale_var(t[climate_var], climate_var)

    fig, ax1 = plt.subplots(figsize=(9.2, 3.9))
    ax2 = ax1.twinx()
    ax1.plot(t[x], t["Consumo"], marker="o", linewidth=1.7, label="Consumo")
    ax2.plot(t[x], t["Clima"], linestyle="--", linewidth=1.5, color=climate_color(climate_var), label=label_var(climate_var))

    titulo = "Sazonalidade" if saz else "Evolução temporal"
    ax1.set_title(f"{titulo}: Energia Ativa Total vs {label_var(climate_var)} — {distrito}", fontsize=11)
    ax1.set_ylabel(f"Energia Ativa Total ({cons_unit})")
    ax2.set_ylabel(f"{label_var(climate_var)} ({clim_unit})" if clim_unit else label_var(climate_var))
    ax1.set_xlabel("Mês" if saz else "Data")
    if saz:
        ax1.set_xticks(range(1, 13)); ax1.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    else:
        format_time_axis(ax1)
    ax1.grid(True, linestyle="--", alpha=.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    fig.subplots_adjust(bottom=0.22)
    showfig(fig)


def climate_vs_consumption_single_county(df, climate_var, concelho, saz=False):
    d = df[df["Concelho"] == concelho].copy()
    if d.empty:
        st.info("Sem dados para o concelho selecionado."); return
    distrito = d["Distrito"].dropna().iloc[0] if d["Distrito"].notna().any() else "Distrito"
    x = "Mês" if saz else "Data"
    cons = agg(d, [x, "Concelho"], "Energia_Ativa_Total")
    clim = agg(d, [x, "Distrito"], climate_var).drop(columns=["Distrito"], errors="ignore")
    t = cons.merge(clim, on=x, how="inner")
    if t.empty:
        st.info("Sem dados suficientes para cruzar consumo e clima."); return

    t["Consumo"], cons_unit = scale_var(t["Energia_Ativa_Total"], "Energia_Ativa_Total")
    t["Clima"], clim_unit = scale_var(t[climate_var], climate_var)

    fig, ax1 = plt.subplots(figsize=(9.2, 3.9))
    ax2 = ax1.twinx()
    ax1.plot(t[x], t["Consumo"], marker="o", linewidth=1.7, label=f"Consumo — {concelho}")
    ax2.plot(t[x], t["Clima"], linestyle="--", linewidth=1.5, color=climate_color(climate_var), label=f"{label_var(climate_var)} — {distrito}")
    titulo = "Sazonalidade" if saz else "Evolução temporal"
    ax1.set_title(f"{titulo}: Energia Ativa Total vs {label_var(climate_var)} — {concelho}", fontsize=11)
    ax1.set_ylabel(f"Energia Ativa Total ({cons_unit})")
    ax2.set_ylabel(f"{label_var(climate_var)} ({clim_unit})" if clim_unit else label_var(climate_var))
    ax1.set_xlabel("Mês" if saz else "Data")
    if saz:
        ax1.set_xticks(range(1, 13)); ax1.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    else:
        format_time_axis(ax1)
    ax1.grid(True, linestyle="--", alpha=.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    fig.subplots_adjust(bottom=0.22)
    showfig(fig)


def climate_vs_consumption_counties(df, climate_var, distrito, saz=False):
    d = df[df["Distrito"] == distrito].copy()
    if d.empty:
        st.info("Sem dados para o distrito selecionado."); return
    x = "Mês" if saz else "Data"
    cons = agg(d, [x, "Concelho"], "Energia_Ativa_Total")
    clim = agg(d, [x, "Distrito"], climate_var).drop(columns=["Distrito"], errors="ignore")
    if cons.empty or clim.empty:
        st.info("Sem dados suficientes para cruzar consumo e clima."); return
    cons["Consumo"], cons_unit = scale_var(cons["Energia_Ativa_Total"], "Energia_Ativa_Total")
    clim["Clima"], clim_unit = scale_var(clim[climate_var], climate_var)

    fig, ax1 = plt.subplots(figsize=(9.6, 4.2))
    ax2 = ax1.twinx()
    concelhos = sorted(cons["Concelho"].dropna().unique())
    palette = discrete_palette(concelhos)
    for conc in concelhos:
        cc = cons[cons["Concelho"] == conc]
        ax1.plot(cc[x], cc["Consumo"], marker="o", markersize=3.2, linewidth=1.25, label=conc, color=palette.get(conc))
    ax2.plot(clim[x], clim["Clima"], linestyle="--", linewidth=1.7, color=climate_color(climate_var), label=label_var(climate_var))

    titulo = "Sazonalidade" if saz else "Evolução temporal"
    ax1.set_title(f"{titulo}: concelhos vs {label_var(climate_var)} — {distrito}", fontsize=11)
    ax1.set_ylabel(f"Energia Ativa Total ({cons_unit})")
    ax2.set_ylabel(f"{label_var(climate_var)} ({clim_unit})" if clim_unit else label_var(climate_var))
    ax1.set_xlabel("Mês" if saz else "Data")
    if saz:
        ax1.set_xticks(range(1, 13)); ax1.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    else:
        format_time_axis(ax1)
    ax1.grid(True, linestyle="--", alpha=.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, bbox_to_anchor=(1.08, 1), loc="upper left", fontsize=7, borderaxespad=0)
    fig.subplots_adjust(right=0.73, bottom=0.22)
    showfig(fig)


def climate_sensitivity_ranking(df, climate_var, level="Distrito"):
    """Ranking de sensibilidade: correlação absoluta entre consumo e variável climática."""
    if df.empty:
        st.info("Sem dados para os filtros selecionados."); return
    keys = ["Data", level] if level == "Distrito" else ["Data", "Distrito", "Concelho"]
    cons = agg(df, keys, "Energia_Ativa_Total")
    clim_keys = ["Data", "Distrito"] if level != "Distrito" else ["Data", "Distrito"]
    clim = agg(df, clim_keys, climate_var)
    if level == "Distrito":
        t = cons.merge(clim, on=["Data", "Distrito"], how="inner")
        group_cols = ["Distrito"]
    else:
        t = cons.merge(clim, on=["Data", "Distrito"], how="inner")
        group_cols = ["Distrito", "Concelho"]
    if t.empty:
        st.info("Sem dados suficientes para calcular sensibilidade."); return

    rows = []
    for name, g in t.groupby(group_cols):
        if len(g.dropna(subset=["Energia_Ativa_Total", climate_var])) >= 3:
            corr = g["Energia_Ativa_Total"].corr(g[climate_var])
            if pd.notna(corr):
                if level == "Distrito":
                    distrito = name if isinstance(name, str) else name[0]
                    concelho = None
                else:
                    distrito, concelho = name
                rows.append({"Distrito": distrito, "Concelho": concelho, "Correlação": corr, "Sensibilidade": abs(corr)})
    rank = pd.DataFrame(rows)
    if rank.empty:
        st.info("Não foi possível calcular correlações com os dados filtrados."); return
    rank = rank.sort_values("Sensibilidade", ascending=False)
    label_col = "Distrito" if level == "Distrito" else "Concelho"

    fig, ax = plt.subplots(figsize=(7.8, max(3.2, .28 * len(rank))))
    sns.barplot(data=rank, x="Sensibilidade", y=label_col, ax=ax, color="#9b5de5")
    ax.set_title(f"Ranking de sensibilidade ao clima — {label_var(climate_var)}", fontsize=10.5)
    ax.set_xlabel("|correlação consumo–clima|  (0 = fraca; 1 = forte)")
    ax.set_ylabel("")
    ax.grid(True, axis="x", linestyle="--", alpha=.3)
    showfig(fig)
    with st.expander("Ver tabela com correlação assinada"):
        cols = ["Distrito", "Correlação", "Sensibilidade"] if level == "Distrito" else ["Distrito", "Concelho", "Correlação", "Sensibilidade"]
        st.dataframe(rank[cols].round(3), use_container_width=True)


def line_district(df, var, saz=False):
    x, xlabel = temporal_key_for_plot(df, var, saz=saz)
    if x not in df.columns:
        st.info("Não existe dimensão temporal adequada para esta variável."); return
    keys = [x, "Distrito"]
    t = agg(df, keys, var)
    if t.empty:
        st.info("Sem dados para os filtros selecionados."); return
    t["Valor"], unit = scale_var(t[var], var)
    distritos = sorted(t["Distrito"].dropna().unique())
    palette = discrete_palette(distritos)

    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    sns.lineplot(data=t, x=x, y="Valor", hue="Distrito", palette=palette, marker="o", markersize=4, linewidth=1.6, ax=ax)
    titulo = "Sazonalidade média" if saz else ("Evolução trimestral" if xlabel == "Trimestre" else "Evolução temporal")
    ax.set_title(titulo + f" — {label_var(var)}", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))
    if saz and x == "Mês":
        ax.set_xticks(range(1, 13)); ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    elif saz and x == "Trimestre_Num":
        ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["T1", "T2", "T3", "T4"])
    elif not saz:
        format_time_axis(ax)
    ax.grid(True, linestyle="--", alpha=.3)
    ax.legend(title="Distrito", fontsize=8, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    fig.subplots_adjust(right=0.78, bottom=0.22)
    showfig(fig)


def bar_district(df, var):
    t = agg(df, ["Distrito"], var)
    if t.empty:
        st.info("Sem dados para os filtros selecionados."); return
    t["Valor"], unit = scale_var(t[var], var)
    t = t.sort_values("Valor", ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    sns.barplot(data=t, x="Valor", y="Distrito", ax=ax, color="#4C78A8")
    ax.set_title(f"Ranking distrital — {label_var(var)}", fontsize=11)
    ax.set_xlabel(f"{label_var(var)} ({unit})" if unit else label_var(var)); ax.set_ylabel("")
    showfig(fig)


def line_single_county(df, var, concelho, saz=False):
    x, xlabel = temporal_key_for_plot(df, var, saz=saz)
    if x not in df.columns:
        st.info("Não existe dimensão temporal adequada para esta variável."); return
    t = agg(df[df["Concelho"] == concelho], [x], var)
    if t.empty:
        st.info("Sem dados para os filtros selecionados."); return
    t["Valor"], unit = scale_var(t[var], var)
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    sns.lineplot(data=t, x=x, y="Valor", marker="o", markersize=4, linewidth=1.6, ax=ax)
    titulo = "Sazonalidade média" if saz else ("Evolução trimestral" if xlabel == "Trimestre" else "Evolução temporal")
    ax.set_title(titulo + f" — {label_var(var)} | {concelho}", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))
    if saz and x == "Mês":
        ax.set_xticks(range(1, 13)); ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    elif saz and x == "Trimestre_Num":
        ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["T1", "T2", "T3", "T4"])
    elif not saz:
        format_time_axis(ax)
    ax.grid(True, linestyle="--", alpha=.3)
    fig.subplots_adjust(bottom=0.22)
    showfig(fig)


def line_counties_multi(df, var, saz=False):
    key, xlabel = temporal_key_for_plot(df, var, saz=saz)
    if key not in df.columns:
        st.info("Não existe dimensão temporal adequada para esta variável."); return
    t = agg(df, [key, "Concelho"], var)
    if t.empty:
        st.info("Sem dados para os filtros selecionados."); return
    t["Valor"], unit = scale_var(t[var], var)

    concelhos = sorted(t["Concelho"].dropna().unique())
    palette = discrete_palette(concelhos)

    fig, ax = plt.subplots(figsize=(9.4, 4.2))
    sns.lineplot(
        data=t,
        x=key,
        y="Valor",
        hue="Concelho",
        palette=palette,
        marker="o",
        markersize=3.5,
        linewidth=1.35,
        ax=ax
    )

    titulo = "Sazonalidade média" if saz else ("Evolução trimestral" if xlabel == "Trimestre" else "Evolução temporal")
    ax.set_title(titulo + f" por concelho — {label_var(var)}", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))

    if saz and key == "Mês":
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    elif saz and key == "Trimestre_Num":
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xticklabels(["T1", "T2", "T3", "T4"])
    elif not saz:
        format_time_axis(ax)

    ax.grid(True, linestyle="--", alpha=.3)
    ax.legend(title="Concelho", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7, borderaxespad=0)
    fig.subplots_adjust(right=0.76, bottom=0.22)
    showfig(fig)


def bars_counties(df, var, title_extra=""):
    t = agg(df, ["Distrito", "Concelho"], var)
    t["Valor"], unit = scale_var(t[var], var)
    t = t.sort_values("Valor", ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, max(3.4, .26 * len(t))))
    sns.barplot(data=t, x="Valor", y="Concelho", hue="Distrito", dodge=False, ax=ax)
    ax.set_title(f"{label_var(var)} por concelho {title_extra}", fontsize=11)
    ax.set_xlabel(f"{label_var(var)} ({unit})" if unit else label_var(var)); ax.set_ylabel("")
    ax.legend(loc="lower right", fontsize=8)
    showfig(fig)

# ============================================================
# MAPS
# ============================================================

def prepare_map_districts(df, gdf, var, scale_df=None):
    data = agg(df, ["Distrito_norm"], var)
    mp = gdf.merge(data, on="Distrito_norm", how="left")
    mp["Valor"], unit = scale_var(mp[var], var)
    if scale_df is not None:
        sd = agg(scale_df, ["Distrito_norm"], var)
        sv, _ = scale_var(sd[var], var)
        return mp, unit, sv.min(), sv.max()
    return mp, unit, mp["Valor"].min(), mp["Valor"].max()


def prepare_map_counties(df, gdf, var, scale_df=None):
    data = agg(df, ["Distrito_norm", "Concelho_norm"], var)
    mp = gdf.merge(data, on=["Distrito_norm", "Concelho_norm"], how="left")
    mp["Valor"], unit = scale_var(mp[var], var)
    if scale_df is not None:
        sd = agg(scale_df, ["Distrito_norm", "Concelho_norm"], var)
        sv, _ = scale_var(sd[var], var)
        return mp, unit, sv.min(), sv.max()
    return mp, unit, mp["Valor"].min(), mp["Valor"].max()


def map_districts(df, gdf, var, title, scale_df=None, figsize=(5, 5.8)):
    mp, unit, vmin, vmax = prepare_map_districts(df, gdf, var, scale_df)
    fig, ax = plt.subplots(figsize=figsize)
    mp.plot(column="Valor", cmap=MAP_CM.get(var, "viridis"), vmin=vmin, vmax=vmax,
            linewidth=.7, edgecolor="black", legend=True,
            legend_kwds={"label": display_label(var, unit)},
            missing_kwds={"color": "lightgrey"}, ax=ax)
    add_labels(ax, mp, "distrito", fs=4.6)
    ax.set_title(title, fontsize=10.5); ax.axis("off")
    showfig(fig)


def map_counties(df, gdf, var, title, distrito=None, labels=False, scale_df=None, figsize=(5, 5.8), district_context=False):
    mp, unit, vmin, vmax = prepare_map_counties(df, gdf, var, scale_df)
    if distrito and distrito != "Portugal Continental":
        mp = mp[mp["Distrito_norm"] == norm_name(distrito)].copy()
    fig, ax = plt.subplots(figsize=figsize)
    mp.plot(column="Valor", cmap=MAP_CM.get(var, "viridis"), vmin=vmin, vmax=vmax,
            linewidth=.25 if not distrito or distrito == "Portugal Continental" else .7,
            edgecolor="gray" if not distrito or distrito == "Portugal Continental" else "black",
            legend=True, legend_kwds={"label": display_label(var, unit)},
            missing_kwds={"color": "lightgrey"}, ax=ax)
    # Nos mapas nacionais por concelho, acrescenta o contorno e o nome dos distritos
    # para orientar a leitura sem criar um segundo mapa pesado.
    if district_context and distrito == "Portugal Continental" and "gdf_distritos" in globals() and gdf_distritos is not None:
        try:
            gd_ctx = gdf_distritos.to_crs(mp.crs) if gdf_distritos.crs != mp.crs else gdf_distritos
            gd_ctx.boundary.plot(ax=ax, color="#111111", linewidth=.55, zorder=5)
            add_labels(ax, gd_ctx, "distrito", fs=4.2)
        except Exception:
            pass
    if labels and distrito and distrito != "Portugal Continental":
        add_labels(ax, mp, "municipio", fs=4.6)
    ax.set_title(title, fontsize=10.5); ax.axis("off")
    showfig(fig)


def map_pc_outliers(df_full, gdf, distrito, scale_df, title, labels=True, figsize=(5.2, 5.2)):
    full_data = agg(df_full, ["Distrito_norm", "Concelho_norm"], "Consumo_per_capita")
    mp = gdf.merge(full_data, on=["Distrito_norm", "Concelho_norm"], how="left")
    mp["Valor"], unit = scale_var(mp["Consumo_per_capita"], "Consumo_per_capita")
    scale_data = agg(scale_df, ["Distrito_norm", "Concelho_norm"], "Consumo_per_capita")
    sv, _ = scale_var(scale_data["Consumo_per_capita"], "Consumo_per_capita")
    vmin, vmax = pc_limits(sv)
    if distrito:
        mp = mp[mp["Distrito_norm"] == norm_name(distrito)].copy()
    out_norm = [norm_name(c) for c in OUTLIERS_PC.get(distrito, [])] if distrito else []
    mp_out = mp[mp["Concelho_norm"].isin(out_norm)].copy()
    mp_norm = mp[~mp["Concelho_norm"].isin(out_norm)].copy()
    fig, ax = plt.subplots(figsize=figsize)
    mp_norm.plot(column="Valor", cmap="YlOrRd", vmin=vmin, vmax=vmax, linewidth=.7, edgecolor="black",
                 legend=True, legend_kwds={"label": f"Consumo per capita médio ({unit})"}, ax=ax)
    handles = []
    if not mp_out.empty:
        mp_out.plot(color="tab:blue", linewidth=.9, edgecolor="black", ax=ax)
        for _, r in mp_out.iterrows():
            handles.append(mpatches.Patch(facecolor="tab:blue", edgecolor="black", label=f"Outlier: {r['municipio']} ({r['Valor']:.2f} {unit})"))
        ax.legend(handles=handles, loc="lower left", frameon=True, title="Valor fora da escala", fontsize=7, title_fontsize=8)
    if labels:
        add_labels(ax, mp, "municipio", fs=4.6)
    ax.set_title(title, fontsize=10.5); ax.axis("off")
    showfig(fig)

# ============================================================
# CLUSTER MAPS
# ============================================================

def cluster_pydeck_map(gdf_wgs, cl):
    """Mapa interativo leve com PyDeck/GeoJsonLayer e geometrias simplificadas."""
    try:
        import pydeck as pdk
    except Exception:
        st.warning("Para o mapa interativo leve, adiciona `pydeck` ao requirements.txt. A mostrar mapa estático.")
        cluster_static(gdf_concelhos, cl)
        return
    mp = gdf_wgs.merge(
        cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster", "Distrito", "Concelho"]],
        on=["Distrito_norm", "Concelho_norm"],
        how="inner",
        suffixes=("", "_cluster")
    )
    if mp.empty:
        st.info("Sem concelhos para os filtros selecionados."); return
    mp = mp.to_crs(epsg=4326).copy()
    # simplificação em graus: reduz bastante o peso do GeoJSON mantendo a leitura municipal
    mp["geometry"] = mp.geometry.simplify(0.004, preserve_topology=True)

    def hex_to_rgba(h, alpha=170):
        h = h.lstrip("#")
        return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [alpha]
    mp["fill_color"] = mp["Cluster"].astype(int).map(lambda k: hex_to_rgba(CLUSTER_CORES.get(k, "#cccccc")))
    geojson = json.loads(mp.to_json())
    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255, 190],
        line_width_min_pixels=1,
    )
    view_state = pdk.ViewState(latitude=39.65, longitude=-8.0, zoom=6.0)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=None,
        tooltip={
            "html": "<b>{Concelho}</b><br/>{Distrito}<br/>Cluster {Cluster}: {Nome_Cluster}",
            "style": {"backgroundColor": "#180d27", "color": "white"}
        }
    )
    st.pydeck_chart(deck, use_container_width=True, height=560)


def cluster_hover_map(gdf_wgs, cl):
    """Mapa leve com hover usando Plotly, substituindo o Folium pesado."""
    if not HAS_PLOTLY:
        st.warning("Para o mapa com hover, adiciona `plotly` ao requirements.txt. A mostrar mapa estático como alternativa.")
        cluster_static(gdf_concelhos, cl)
        return
    mp = gdf_wgs.merge(
        cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster", "Distrito", "Concelho"]],
        on=["Distrito_norm", "Concelho_norm"],
        how="inner"
    )
    if mp.empty:
        st.info("Sem concelhos para os filtros selecionados."); return
    mp = mp.copy().reset_index(drop=True)
    mp["feature_id"] = mp.index.astype(str)
    mp["Cluster_txt"] = mp["Cluster"].astype(int).astype(str) + " — " + mp["Nome_Cluster"].astype(str)
    geojson = json.loads(mp.to_json())
    color_map = {f"{k} — {CLUSTER_LABELS[k]}": v for k, v in CLUSTER_CORES.items()}
    fig = px.choropleth(
        mp,
        geojson=geojson,
        locations="feature_id",
        featureidkey="properties.feature_id",
        color="Cluster_txt",
        color_discrete_map=color_map,
        hover_name="Concelho",
        hover_data={"Distrito": True, "Cluster": True, "Nome_Cluster": True, "feature_id": False, "Cluster_txt": False},
        projection="mercator"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        height=560,
        margin={"r": 0, "t": 20, "l": 0, "b": 0},
        paper_bgcolor="#0d0617",
        plot_bgcolor="#0d0617",
        legend_title_text="Cluster",
        font=dict(color="#f4ecff")
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def cluster_interactive(gdf_wgs, cl):
    # Mantido como alias para compatibilidade, mas agora usa Plotly em vez de Folium.
    cluster_hover_map(gdf_wgs, cl)


def cluster_static(gdf, cl):
    mp = gdf.merge(cl[["Distrito_norm", "Concelho_norm", "Cluster"]], on=["Distrito_norm", "Concelho_norm"], how="inner")
    if mp.empty:
        st.info("Sem concelhos para os filtros selecionados."); return
    mp["cor"] = mp["Cluster"].map(CLUSTER_CORES).fillna("#eee")
    fig, ax = plt.subplots(figsize=(5.5, 6.5))
    mp.plot(color=mp["cor"], edgecolor="white", linewidth=.35, ax=ax)
    ax.set_title("Mapa de clusters energéticos", fontsize=10.5); ax.axis("off")
    showfig(fig)


def cluster_indicator_explorer(df_main, cl):
    """Interação leve: escolhe indicador e cluster para gerar ranking de concelhos."""
    if cl.empty:
        return
    st.subheader("Ranking interativo por cluster")
    st.caption("Seleciona um indicador e um cluster para ordenar os concelhos filtrados.")

    profile_vars = [
        "Consumo_per_capita",
        "Energia_BT_per_capita",
        "Energia_MAT_per_capita",
        "CPEs_por_1000_hab",
        "UPACs_por_1000_hab",
        "Densidade_Populacional"
    ]
    profile_vars = [v for v in profile_vars if v in df_main.columns]
    if not profile_vars:
        st.info("Não existem variáveis de perfil disponíveis para esta exploração.")
        return

    a, b, c = st.columns([1.15, 1.25, .85])
    with a:
        indicador = st.selectbox("Indicador", profile_vars, format_func=label_var, key="cluster_indicator_select")
    with b:
        cluster_focus = st.selectbox(
            "Cluster",
            sorted([int(x) for x in cl["Cluster"].dropna().unique()]),
            format_func=lambda k: f"{k} — {CLUSTER_LABELS.get(int(k), 'Cluster')}",
            key="cluster_focus_select"
        )
    with c:
        ordem = st.radio("Ordem", ["Descendente", "Ascendente"], horizontal=False, key="cluster_rank_order")

    dc = df_main.merge(
        cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster", "Distrito", "Concelho"]],
        on=["Distrito_norm", "Concelho_norm"],
        how="inner",
        suffixes=("", "_cluster")
    )
    if "Distrito" not in dc.columns and "Distrito_cluster" in dc.columns:
        dc["Distrito"] = dc["Distrito_cluster"]
    if "Concelho" not in dc.columns and "Concelho_cluster" in dc.columns:
        dc["Concelho"] = dc["Concelho_cluster"]
    if dc.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    by_county = dc[dc["Cluster"] == cluster_focus].groupby(["Distrito", "Concelho"], as_index=False)[indicador].mean()
    by_county["Valor"], unit = scale_var(by_county[indicador], indicador)
    by_county = by_county.sort_values("Valor", ascending=(ordem == "Ascendente"))
    titulo = f"Concelhos do cluster {cluster_focus} por {display_label(indicador, unit)}"
    st.markdown(f"**{titulo}**")
    st.dataframe(by_county[["Distrito", "Concelho", "Valor"]].round(3), use_container_width=True, height=360)

# ============================================================
# LOAD
# ============================================================

df = load_df(DATASET)
clusters = load_clusters(CLUSTERS_CSV, CLUSTERS_XLSX)
gdf_distritos, gdf_concelhos, gdf_concelhos_wgs = load_geo(CAOP)
if df is None:
    st.error("Não encontrei data/dataset_final.csv. Coloca o ficheiro na pasta data/."); st.stop()

upacs_df = load_upacs(UPACS_FILE, df)

# ============================================================
# NAV
# ============================================================

st.sidebar.title("⚡ Menu")
sec = st.sidebar.radio("Secção", ["0. Introdução", "1. Visualização Exploratória", "2. Os 4 Distritos Estudados", "3. Clustering Energético"], label_visibility="collapsed")
st.title("Dashboard de Caracterização Energética Municipal")
st.caption("Protótipo de deployment CRISP-DM para apoio à decisão territorial — E-Redes")


# ============================================================
# SEC 1
# ============================================================


if sec == "0. Introdução":
    st.header("0. Introdução")
    st.markdown(
        """
        Esta plataforma funciona como uma proposta de **deployment** para transformar a análise exploratória
        e o clustering num instrumento prático de apoio à decisão territorial.

        O objetivo é permitir que a E-Redes explore indicadores energéticos municipais, observe padrões
        espaciais e temporais, consulte os resultados dos quatro distritos estudados e interprete os perfis
        de clustering energético.
        """
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Linhas", f"{len(df):,}".replace(",", " "))
    m2.metric("Concelhos", df["Concelho"].nunique())
    m3.metric("Distritos", df["Distrito"].nunique())
    m4.metric("Período", f"{int(df['Ano'].min())}–{int(df['Ano'].max())}" if "Ano" in df.columns else "n/d")

    st.divider()

    st.subheader("Como navegar pelo dashboard")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            ### 1. Visualização Exploratória

            Área mais flexível do dashboard.

            Permite escolher:
            - variável;
            - anos;
            - nível de análise;
            - distritos;
            - concelhos;
            - tipo de visualização.

            É a zona ideal para explorar rapidamente os dados e testar padrões.
            """
        )

    with c2:
        st.markdown(
            """
            ### 2. Os 4 Distritos Estudados

            Área dedicada à análise territorial principal.

            Mostra, para cada variável:
            - mapa de Portugal por distritos;
            - mapa de Portugal por concelhos;
            - mapa detalhado de um distrito;
            - gráfico de barras dos concelhos desse distrito.

            Esta secção resume melhor a análise de Faro, Setúbal, Aveiro e Castelo Branco.
            """
        )

    with c3:
        st.markdown(
            """
            ### 3. Clustering Energético

            Área estratégica do deployment.

            Permite:
            - consultar os perfis de cluster;
            - filtrar por cluster, distrito e concelho;
            - observar mapas de clusters, incluindo mapa interativo leve com tooltip;
            - consultar a tabela dos concelhos;
            - usar o ranking interativo por cluster para ordenar concelhos por indicador;
            - comparar perfis médios por cluster.

            Serve para transformar concelhos em perfis operacionais e apoiar decisões por tipo de território.
            """
        )

    st.divider()

    st.subheader("Granularidades disponíveis")

    st.markdown(
        """
        Na **Visualização Exploratória**, existem duas granularidades principais:

        **Nível distrito**  
        A análise é agregada por distrito. Ainda assim, é possível escolher quais os concelhos que entram
        no cálculo da média/soma distrital. Isto permite, por exemplo, perceber como certos concelhos influenciam
        o comportamento global do distrito.

        **Nível concelho**  
        A análise é feita diretamente ao nível municipal. Existem dois modos:
        - **Comparação entre concelhos**: permite comparar concelhos de vários distritos e visualizar Portugal dividido por concelhos;
        - **Detalhe/Singular**: exige a escolha de um único distrito e permite analisar os seus concelhos em mais detalhe, incluindo evolução temporal e sazonalidade.

        Em todas as áreas, as variáveis estão organizadas por secções: absolutas, relativas, proporções, climáticas e qualidade de serviço.
        """
    )

    st.subheader("Leitura operacional")

    st.markdown(
        """
        Este dashboard permite passar de uma análise estática para uma ferramenta prática. Em contexto real,
        a E-Redes poderia usá-lo para:

        - identificar concelhos com consumos anómalos;
        - acompanhar sazonalidade turística;
        - monitorizar polos industriais;
        - observar a penetração de UPACs;
        - comparar consumo absoluto e relativo;
        - apoiar decisões de planeamento e reforço da rede;
        - segmentar estratégias por cluster energético;
        - explorar rankings de concelhos dentro de cada cluster.
        """
    )


elif sec == "1. Visualização Exploratória":
    st.header("1. Visualização Exploratória")
    st.markdown("Exploração dinâmica dos indicadores por distrito e por concelho.")

    c1, c2, c3 = st.columns([1.25, 1.05, 1.2])
    with c1:
        var = choose_var(df, "expl")

    df_var, using_upacs_file = data_for_var(var, df, upacs_df)
    if is_upac_var(var) and not using_upacs_file:
        st.warning("Não encontrei `data/upacs_tratado.xlsx` ou a variável não existe nesse ficheiro. A app está a usar o dataset unificado como fallback.")

    with c2:
        anos = choose_years(df_var, "expl_anos", var=var)
    with c3:
        if is_climate_var(var):
            level = st.radio("Tipo de comparação", ["Consumo do distrito vs clima", "Consumo de concelho vs clima"], horizontal=True)
        else:
            level = st.radio("Granularidade", ["Nível distrito", "Nível concelho"], horizontal=True)

    dbase = df_var[df_var["Ano"].isin(anos)].copy() if anos else df_var.iloc[0:0].copy()
    st.divider()

    if dbase.empty:
        st.info("Seleciona pelo menos um ano para gerar as visualizações.")
        st.stop()

    if is_climate_var(var):
        if level == "Consumo do distrito vs clima":
            st.subheader("Comparação entre consumo distrital e variável climática")
            a, b, c = st.columns([1.2, 1.05, 1.3])
            with a:
                dists = st.multiselect(
                    "Distritos",
                    sorted(dbase["Distrito"].dropna().unique()),
                    default=default_districts(sorted(dbase["Distrito"].dropna().unique())),
                    key="clima_districts"
                )
            dd = dbase[dbase["Distrito"].isin(dists)].copy() if dists else dbase.iloc[0:0].copy()
            with b:
                viz = st.selectbox(
                    "Visualização",
                    ["Evolução consumo vs clima", "Sazonalidade consumo vs clima", "Ranking de sensibilidade dos distritos"],
                    key="clima_district_viz"
                )
            with c:
                dist_plot = st.selectbox("Distrito do gráfico", sorted(dd["Distrito"].dropna().unique()), key="clima_dist_plot") if not dd.empty and viz != "Ranking de sensibilidade dos distritos" else None
            if dd.empty:
                empty_selection_message("distrito")
            elif viz == "Ranking de sensibilidade dos distritos":
                climate_sensitivity_ranking(dd, var, level="Distrito")
            else:
                climate_vs_consumption_district(dd, var, dist_plot, saz=(viz == "Sazonalidade consumo vs clima"))
        else:
            st.subheader("Comparação entre consumo municipal e variável climática distrital")
            a, b = st.columns([1.15, 1.25])
            with a:
                dists = st.multiselect(
                    "Distritos",
                    sorted(dbase["Distrito"].dropna().unique()),
                    default=default_districts(sorted(dbase["Distrito"].dropna().unique())),
                    key="clima_conc_dists"
                )
            dd = dbase[dbase["Distrito"].isin(dists)].copy() if dists else dbase.iloc[0:0].copy()
            with b:
                viz = st.selectbox(
                    "Visualização",
                    ["Evolução consumo vs clima", "Sazonalidade consumo vs clima", "Ranking de sensibilidade dos concelhos"],
                    key="clima_conc_viz"
                )

            if dd.empty:
                empty_selection_message("distrito/concelho")
            elif viz == "Ranking de sensibilidade dos concelhos":
                concs = st.multiselect(
                    "Concelhos incluídos no ranking",
                    sorted(dd["Concelho"].dropna().unique()),
                    default=[],
                    help="Se não escolheres nenhum, entram todos os concelhos dos distritos selecionados.",
                    key="clima_conc_list"
                )
                if concs:
                    dd = dd[dd["Concelho"].isin(concs)].copy()
                climate_sensitivity_ranking(dd, var, level="Concelho")
            else:
                conc_plot = st.selectbox("Concelho do gráfico", sorted(dd["Concelho"].dropna().unique()), key="clima_conc_plot")
                climate_vs_consumption_single_county(dd, var, conc_plot, saz=(viz == "Sazonalidade consumo vs clima"))
        st.stop()

    if level == "Nível distrito":
        st.subheader("Análise ao nível do distrito")
        st.caption("Os concelhos escolhidos influenciam a média/soma distrital apresentada.")

        a, b, c = st.columns([1.05, 1.55, 1.2])
        with a:
            dists = st.multiselect(
                "Distritos",
                sorted(dbase["Distrito"].dropna().unique()),
                default=default_districts(sorted(dbase["Distrito"].dropna().unique())),
                key="expl_dist_level_dists"
            )

        if not dists:
            dtmp = dbase.iloc[0:0].copy()
        else:
            dtmp = dbase[dbase["Distrito"].isin(dists)].copy()

        with b:
            concs = st.multiselect(
                "Concelhos que entram no cálculo",
                sorted(dtmp["Concelho"].dropna().unique()),
                default=[],
                help="Se não escolheres nenhum, entram todos os concelhos dos distritos selecionados.",
                key="expl_dist_level_concs"
            )

        if concs:
            dtmp = dtmp[dtmp["Concelho"].isin(concs)].copy()

        with c:
            viz_options = ["Evolução temporal", "Sazonalidade", "Ranking distrital", "Mapa por distrito", "Tabela agregada"]
            if is_climate_var(var):
                viz_options = ["Evolução consumo vs clima", "Sazonalidade consumo vs clima"]
            elif is_quality_var(var):
                viz_options = ["Ranking distrital", "Mapa por distrito", "Tabela agregada"]
            viz = st.selectbox(
                "Visualização",
                viz_options,
                key="expl_dist_viz"
            )

        if dtmp.empty:
            empty_selection_message("distrito")
        elif viz in ["Evolução consumo vs clima", "Sazonalidade consumo vs clima"]:
            dist_plot = st.selectbox("Distrito do gráfico", sorted(dtmp["Distrito"].dropna().unique()), key="expl_climate_dist_plot")
            climate_vs_consumption_district(dtmp, var, dist_plot, saz=(viz == "Sazonalidade consumo vs clima"))
        elif viz == "Evolução temporal":
            line_district(dtmp, var, False)
        elif viz == "Sazonalidade":
            line_district(dtmp, var, True)
        elif viz == "Ranking distrital":
            bar_district(dtmp, var)
        elif viz == "Mapa por distrito":
            if gdf_distritos is None:
                st.warning("Falta o ficheiro CAOP GeoPackage.")
            else:
                map_districts(dtmp, gdf_distritos, var, f"Mapa distrital — {label_var(var)}")
        else:
            st.dataframe(agg(dtmp, ["Distrito"], var), use_container_width=True)

    else:
        st.subheader("Análise ao nível do concelho")
        mode = st.radio(
            "Modo de análise",
            ["Comparação entre concelhos", "Detalhe/Singular"],
            horizontal=True,
            key="expl_conc_mode"
        )

        if mode == "Comparação entre concelhos":
            st.caption("Permite comparar vários distritos e visualizar Portugal dividido por concelhos.")

            a, b, c = st.columns([1.25, 1.5, 1.15])
            with a:
                dists = st.multiselect(
                    "Distritos",
                    sorted(dbase["Distrito"].dropna().unique()),
                    default=default_districts(sorted(dbase["Distrito"].dropna().unique())),
                    key="expl_conc_comp_dists"
                )

            if not dists:
                dd = dbase.iloc[0:0].copy()
            else:
                dd = dbase[dbase["Distrito"].isin(dists)].copy()

            with b:
                concs = st.multiselect(
                    "Concelhos",
                    sorted(dd["Concelho"].dropna().unique()),
                    default=[],
                    help="Se não escolheres nenhum, entram todos os concelhos dos distritos selecionados.",
                    key="expl_conc_comp_concs"
                )

            if concs:
                dd = dd[dd["Concelho"].isin(concs)].copy()

            with c:
                viz_options = ["Mapa por concelho", "Barras por concelho", "Tabela"]
                if is_climate_var(var):
                    viz_options = ["Evolução consumo vs clima", "Sazonalidade consumo vs clima", "Tabela"]
                viz = st.selectbox(
                    "Visualização",
                    viz_options,
                    key="expl_conc_comp_viz"
                )

            if dd.empty:
                empty_selection_message("distrito")
            elif viz in ["Evolução consumo vs clima", "Sazonalidade consumo vs clima"]:
                conc_plot = st.selectbox("Concelho do gráfico", sorted(dd["Concelho"].dropna().unique()), key="expl_climate_conc_comp_plot")
                climate_vs_consumption_single_county(dd, var, conc_plot, saz=(viz == "Sazonalidade consumo vs clima"))
            elif viz == "Mapa por concelho":
                if gdf_concelhos is None:
                    st.warning("Falta o ficheiro CAOP GeoPackage.")
                else:
                    # Mostra Portugal completo por concelhos; os concelhos fora do filtro ficam a cinzento/sem dados.
                    map_counties(
                        dd,
                        gdf_concelhos,
                        var,
                        f"{label_var(var)} — Portugal por concelhos",
                        distrito="Portugal Continental",
                        labels=False,
                        figsize=(5.2, 6.0),
                        district_context=True
                    )
            elif viz == "Barras por concelho":
                bars_counties(dd, var, "— concelhos selecionados")
            else:
                st.dataframe(agg(dd, ["Distrito", "Concelho"], var), use_container_width=True)

        else:
            st.caption("Escolhe um único distrito para ver o detalhe dos seus concelhos.")

            a, b, c = st.columns([1.05, 1.35, 1.2])
            with a:
                dist = st.selectbox(
                    "Distrito obrigatório",
                    sorted(dbase["Distrito"].dropna().unique()),
                    key="expl_conc_detail_dist"
                )

            dd = dbase[dbase["Distrito"] == dist].copy()

            with b:
                concs_detail = st.multiselect(
                    "Concelhos a incluir",
                    sorted(dd["Concelho"].dropna().unique()),
                    default=sorted(dd["Concelho"].dropna().unique()),
                    key="expl_conc_detail_concs"
                )

            if concs_detail:
                dd = dd[dd["Concelho"].isin(concs_detail)].copy()

            with c:
                viz_options = ["Mapa do distrito", "Barras por concelho", "Evolução temporal dos concelhos", "Sazonalidade dos concelhos", "Tabela"]
                if is_climate_var(var):
                    viz_options = ["Evolução consumo vs clima dos concelhos", "Sazonalidade consumo vs clima dos concelhos", "Tabela"]
                elif is_quality_var(var):
                    viz_options = ["Mapa do distrito", "Barras por concelho", "Tabela"]
                viz = st.selectbox(
                    "Visualização",
                    viz_options,
                    key="expl_conc_detail_viz"
                )

            if viz in ["Evolução consumo vs clima dos concelhos", "Sazonalidade consumo vs clima dos concelhos"]:
                climate_vs_consumption_counties(dd, var, dist, saz=(viz == "Sazonalidade consumo vs clima dos concelhos"))
            elif viz == "Mapa do distrito":
                if gdf_concelhos is None:
                    st.warning("Falta o ficheiro CAOP GeoPackage.")
                else:
                    map_counties(
                        dd,
                        gdf_concelhos,
                        var,
                        f"{label_var(var)} — {dist}",
                        distrito=dist,
                        labels=True,
                        figsize=(5.3, 5.3)
                    )
            elif viz == "Barras por concelho":
                bars_counties(dd, var, f"— {dist}")
            elif viz == "Evolução temporal dos concelhos":
                line_counties_multi(dd, var, saz=False)
            elif viz == "Sazonalidade dos concelhos":
                line_counties_multi(dd, var, saz=True)
            else:
                st.dataframe(agg(dd, ["Distrito", "Concelho"], var), use_container_width=True)


# ============================================================
# SEC 2
# ============================================================

elif sec == "2. Os 4 Distritos Estudados":
    st.header("2. Os 4 Distritos Estudados")
    st.markdown(
        """
        Esta secção reúne as visualizações principais usadas na análise territorial dos quatro distritos.
        Para cada variável, são apresentados mapas gerais e um detalhe por distrito.
        """
    )

    vars_estudo = [
        v for v in [
            "Energia_Ativa_Total",
            "Consumo_per_capita",
            "CPEs_por_1000_hab",
            "UPACs_por_1000_hab",
            "Energia_BT_per_capita",
            "Energia_MAT_per_capita"
        ] if v in df.columns
    ]

    a, b = st.columns([1, 1])

    with a:
        var = st.selectbox(
            "Variável",
            vars_estudo,
            format_func=label_var
        )

    with b:
        dist_det = st.selectbox(
            "Distrito para detalhe",
            DISTRITOS_ESTUDADOS
        )

    df_sec2, using_upacs_sec2 = data_for_var(var, df, upacs_df)
    de = df_sec2[df_sec2["Distrito"].isin(DISTRITOS_ESTUDADOS)].copy()

    if gdf_distritos is None or gdf_concelhos is None:
        st.warning("Falta o ficheiro CAOP GeoPackage.")
    else:
        st.subheader("Visão geral")

        ca, cb = st.columns(2)

        with ca:
            map_districts(
                de,
                gdf_distritos,
                var,
                f"{label_var(var)} — Portugal por distritos",
                figsize=(4.7, 5.5)
            )

        with cb:
            map_counties(
                de,
                gdf_concelhos,
                var,
                f"{label_var(var)} — Portugal por concelhos",
                distrito="Portugal Continental",
                figsize=(4.7, 5.5)
            )

        st.subheader(f"Detalhe — {dist_det}")

        cx, cy = st.columns(2)

        with cx:
            map_counties(
                de[de["Distrito"] == dist_det],
                gdf_concelhos,
                var,
                f"{label_var(var)} — {dist_det}",
                distrito=dist_det,
                labels=True,
                figsize=(5.2, 5.2)
            )

        with cy:
            bars_counties(
                de[de["Distrito"] == dist_det],
                var,
                f"— {dist_det}"
            )

    st.subheader("Narrativas principais e soluções operacionais")

    ANALISE_OPERACIONAL = {
        "Faro": {
            "Energia_Ativa_Total": {
                "narrativa": """
                O consumo absoluto concentra-se sobretudo no litoral algarvio, com destaque para **Loulé, Albufeira, Faro e Portimão**.
                Loulé combina dimensão territorial, turismo e polos de elevado consumo como Vilamoura, Quarteira, Almancil e Quinta do Lago.
                Albufeira apresenta também valores elevados devido ao peso do alojamento, restauração, comércio e vida noturna.
                """,
                "solucoes": """
                - Monitorizar picos de verão nos concelhos turísticos.
                - Cruzar consumo com indicadores de turismo, alojamento e temperatura.
                - Priorizar planeamento de capacidade em zonas costeiras com forte pressão sazonal.
                """
            },
            "Consumo_per_capita": {
                "narrativa": """
                A análise relativa altera a leitura: **Albufeira, Loulé, Castro Marim, Lagoa e Vila do Bispo** ganham maior destaque.
                Isto mostra que parte da pressão energética não é explicada pela população residente, mas por população sazonal,
                turismo, segunda habitação e consumos não domésticos específicos.
                """,
                "solucoes": """
                - Usar consumo per capita como indicador de intensidade territorial, não apenas de dimensão.
                - Separar concelhos turísticos dos restantes em análises comparativas.
                - Investigar Castro Marim como caso específico de consumo elevado face à população.
                """
            },
            "CPEs_por_1000_hab": {
                "narrativa": """
                **Alcoutim** destaca-se por ter muitos CPEs face à população residente, resultado provável da baixa densidade
                e da dispersão territorial. **Castro Marim** e **Vila Real de Santo António** também apresentam valores relevantes,
                possivelmente ligados a habitação sazonal e diferença entre população residente e população efetiva.
                """,
                "solucoes": """
                - Interpretar CPEs relativos com cuidado em concelhos pouco povoados.
                - Monitorizar custos e qualidade de serviço em redes mais dispersas.
                - Cruzar CPEs com habitação secundária, alojamento local e sazonalidade.
                """
            },
            "UPACs_por_1000_hab": {
                "narrativa": """
                **Aljezur, Castro Marim e Vila Real de Santo António** destacam-se na adoção relativa de autoconsumo.
                Em concelhos menos densos, com moradias, cobertura disponível e boa exposição solar, as UPACs tornam-se
                mais viáveis do que em áreas urbanas densas.
                """,
                "solucoes": """
                - Antecipar maior bidirecionalidade da rede em concelhos com elevada penetração de UPACs.
                - Apoiar comunidades de energia em zonas rurais/turísticas.
                - Monitorizar eventuais constrangimentos de baixa tensão associados ao autoconsumo.
                """
            },
            "Energia_BT_per_capita": {
                "narrativa": """
                **Loulé, Albufeira e Vila do Bispo** destacam-se na BT per capita, coerente com consumo residencial,
                comércio, serviços, alojamento turístico e climatização. A BT capta bem a pressão turística e sazonal
                do Algarve.
                """,
                "solucoes": """
                - Reforçar monitorização de transformadores e rede BT em zonas turísticas.
                - Preparar planos sazonais para meses de maior procura.
                - Integrar consumo turístico e temperatura em previsões de curto prazo.
                """
            },
            "Energia_MAT_per_capita": {
                "narrativa": """
                **Castro Marim** surge como principal destaque em MAT per capita, sugerindo consumos específicos de maior escala
                face à população residente. A presença de atividades como salinicultura, infraestruturas e outros consumos
                não domésticos pode explicar parte deste comportamento.
                """,
                "solucoes": """
                - Identificar e acompanhar grandes consumidores locais.
                - Separar consumo MAT de consumo residencial/turístico nas análises.
                - Avaliar se existem necessidades específicas de capacidade ou redundância.
                """
            }
        },

        "Setúbal": {
            "Energia_Ativa_Total": {
                "narrativa": """
                **Setúbal e Seixal** destacam-se pelo peso urbano, populacional e industrial. **Sines** também apresenta consumo
                absoluto elevado, apesar da menor população, devido ao porto, à ZILS e à indústria pesada. **Palmela** surge
                associada ao peso industrial, nomeadamente à Autoeuropa.
                """,
                "solucoes": """
                - Monitorizar separadamente áreas metropolitanas, industriais e portuárias.
                - Priorizar planeamento de capacidade em Sines, Setúbal, Seixal e Palmela.
                - Cruzar consumo com localização de grandes consumidores industriais.
                """
            },
            "Consumo_per_capita": {
                "narrativa": """
                **Sines** torna-se o grande outlier do distrito. O consumo per capita extremo mostra que o consumo não é explicado
                pela população residente, mas pela concentração de atividade portuária, logística, petroquímica e industrial.
                """,
                "solucoes": """
                - Tratar Sines como unidade operacional separada.
                - Criar indicadores específicos para grandes consumidores e indústria pesada.
                - Evitar comparar Sines diretamente com concelhos residenciais/metropolitanos.
                """
            },
            "CPEs_por_1000_hab": {
                "narrativa": """
                **Grândola, Alcácer do Sal, Santiago do Cacém e Sines** destacam-se nos CPEs relativos.
                Em Grândola, o eixo Tróia–Comporta–Melides pode contribuir para mais pontos de consumo ligados a turismo,
                residências secundárias e empreendimentos dispersos.
                """,
                "solucoes": """
                - Acompanhar novas ligações em zonas de expansão turística e residencial.
                - Integrar CPEs relativos em modelos de previsão de procura territorial.
                - Monitorizar concelhos extensos e dispersos com pressão crescente.
                """
            },
            "UPACs_por_1000_hab": {
                "narrativa": """
                **Sesimbra** destaca-se nas UPACs relativas, possivelmente pela presença de habitações unifamiliares e segundas
                habitações. **Alcácer do Sal, Grândola, Palmela e Santiago do Cacém** também apresentam potencial associado
                a maior disponibilidade de área e coberturas.
                """,
                "solucoes": """
                - Preparar a rede para maior produção distribuída em zonas residenciais dispersas.
                - Avaliar capacidade de integração de autoconsumo em baixa tensão.
                - Usar estes concelhos como prioritários para monitorização de UPACs.
                """
            },
            "Energia_BT_per_capita": {
                "narrativa": """
                **Grândola, Alcácer do Sal, Santiago do Cacém e Sines** destacam-se em BT per capita.
                Este padrão sugere consumo residencial/turístico disperso e peso relativo elevado em concelhos de menor densidade.
                """,
                "solucoes": """
                - Monitorizar sazonalidade e expansão urbanística em zonas costeiras/dispersas.
                - Reforçar planeamento BT em áreas turísticas e de segunda habitação.
                - Cruzar BT per capita com CPEs por habitante para identificar pressão territorial.
                """
            },
            "Energia_MAT_per_capita": {
                "narrativa": """
                **Sines** é o caso extremo em MAT per capita, devido à ZILS, porto de águas profundas, terminal petroquímico
                e concentração de indústria/logística pesada. Os restantes concelhos ficam muito abaixo deste perfil.
                """,
                "solucoes": """
                - Criar monitorização dedicada de MAT em Sines.
                - Desenvolver cenários de procura para transição energética industrial.
                - Avaliar redundância, capacidade e risco associado a grandes consumidores.
                """
            }
        },

        "Aveiro": {
            "Energia_Ativa_Total": {
                "narrativa": """
                O distrito apresenta uma estrutura industrial policêntrica. **Aveiro** destaca-se pelo peso urbano, económico
                e portuário. **Santa Maria da Feira** surge associada a tecido industrial diversificado, enquanto **Estarreja,
                Águeda e Oliveira de Azeméis** refletem tradição industrial e empresarial.
                """,
                "solucoes": """
                - Monitorizar vários polos industriais em vez de apenas um centro dominante.
                - Priorizar análises por setor económico e por concelho.
                - Cruzar consumo com CAE dominante e localização empresarial.
                """
            },
            "Consumo_per_capita": {
                "narrativa": """
                **Estarreja** torna-se o principal destaque no consumo per capita, mostrando que a intensidade energética
                está associada ao complexo químico-industrial e não apenas à população residente.
                """,
                "solucoes": """
                - Tratar Estarreja como polo industrial específico.
                - Separar análises industriais das análises urbanas/residenciais.
                - Monitorizar evolução do consumo per capita em concelhos industriais.
                """
            },
            "CPEs_por_1000_hab": {
                "narrativa": """
                **Murtosa, Sever do Vouga, Vale de Cambra, Vagos e Anadia** destacam-se nos CPEs relativos.
                Este padrão está associado a menor população residente, dispersão territorial e maior peso relativo de pontos
                de consumo por habitante.
                """,
                "solucoes": """
                - Usar CPEs relativos para identificar redes dispersas e potenciais custos de serviço.
                - Cruzar CPEs com densidade populacional.
                - Monitorizar qualidade de serviço em concelhos menos densos.
                """
            },
            "UPACs_por_1000_hab": {
                "narrativa": """
                **Castelo de Paiva, Mealhada, Oliveira do Bairro, Águeda e Vagos** destacam-se nas UPACs relativas.
                Em alguns casos, o destaque resulta de baixa população; noutros, de combinação entre tecido residencial,
                empresarial e disponibilidade de coberturas.
                """,
                "solucoes": """
                - Antecipar integração de autoconsumo em concelhos residenciais/empresariais.
                - Monitorizar fluxos inversos e capacidade da rede BT.
                - Avaliar campanhas de autoconsumo em concelhos com bom potencial solar e territorial.
                """
            },
            "Energia_BT_per_capita": {
                "narrativa": """
                **São João da Madeira, Aveiro, Sever do Vouga, Anadia e Arouca** apresentam valores relevantes em BT per capita.
                São João da Madeira é particularmente interessante por combinar pequena dimensão territorial com forte densidade
                económica e industrial.
                """,
                "solucoes": """
                - Monitorizar consumo BT em territórios urbanos/industriais compactos.
                - Avaliar capacidade de postos de transformação em zonas empresariais.
                - Cruzar BT per capita com atividade económica local.
                """
            },
            "Energia_MAT_per_capita": {
                "narrativa": """
                **Estarreja** é o grande outlier de MAT per capita, explicado pelo complexo químico-industrial.
                **Aveiro** também pode apresentar algum peso por causa da atividade portuária e industrial.
                """,
                "solucoes": """
                - Criar acompanhamento específico para MAT em Estarreja.
                - Priorizar fiabilidade e capacidade em zonas industriais críticas.
                - Avaliar potencial de autoconsumo industrial e contratos de flexibilidade.
                """
            }
        },

        "Castelo Branco": {
            "Energia_Ativa_Total": {
                "narrativa": """
                **Castelo Branco e Covilhã** destacam-se no consumo absoluto por serem os principais centros urbanos e económicos.
                **Vila Velha de Ródão** também surge forte apesar da população reduzida, devido à indústria da pasta e papel.
                """,
                "solucoes": """
                - Monitorizar separadamente centros urbanos e polos industriais.
                - Acompanhar consumos industriais em Vila Velha de Ródão.
                - Cruzar consumo com localização empresarial e CAE dominante.
                """
            },
            "Consumo_per_capita": {
                "narrativa": """
                **Vila Velha de Ródão** é o principal outlier do distrito: população reduzida e indústria papeleira tornam
                o consumo per capita muito elevado. Castelo Branco e Covilhã ficam menos extremos porque o consumo é diluído
                por maior população residente.
                """,
                "solucoes": """
                - Tratar Vila Velha de Ródão como caso industrial específico.
                - Evitar que este outlier distorça médias distritais.
                - Monitorizar a evolução do consumo industrial face à população residente.
                """
            },
            "CPEs_por_1000_hab": {
                "narrativa": """
                **Idanha-a-Nova, Penamacor, Oleiros e Vila Velha de Ródão** destacam-se por terem muitos CPEs face à população.
                Isto reflete baixa densidade, extensão territorial, povoamento disperso e muitos pontos de ligação para poucos residentes.
                """,
                "solucoes": """
                - Usar CPEs relativos para avaliar desafios de serviço em territórios rurais.
                - Monitorizar continuidade de serviço em redes dispersas.
                - Considerar soluções locais, autoconsumo coletivo e reforço seletivo.
                """
            },
            "UPACs_por_1000_hab": {
                "narrativa": """
                **Vila Velha de Ródão** volta a destacar-se, seguido por **Proença-a-Nova, Oleiros, Sertã e Penamacor**.
                Em territórios rurais, poucos projetos podem pesar muito por habitante; em Vila Velha de Ródão, a indústria
                pode também incentivar soluções de autoconsumo.
                """,
                "solucoes": """
                - Monitorizar integração de UPACs em concelhos de baixa densidade.
                - Avaliar comunidades de energia e autoconsumo industrial.
                - Garantir capacidade da rede para fluxos bidirecionais.
                """
            },
            "Energia_BT_per_capita": {
                "narrativa": """
                **Idanha-a-Nova** destaca-se na BT per capita, provavelmente devido à baixa população, dispersão territorial
                e peso relativo de pequenos consumos residenciais, agrícolas, serviços locais ou turismo rural.
                """,
                "solucoes": """
                - Avaliar necessidades da rede BT em territórios dispersos.
                - Cruzar BT per capita com CPEs por habitante e densidade populacional.
                - Priorizar qualidade de serviço e resiliência em zonas rurais extensas.
                """
            },
            "Energia_MAT_per_capita": {
                "narrativa": """
                **Vila Velha de Ródão** domina claramente a MAT per capita, consistente com a indústria da pasta e papel
                e necessidades energéticas associadas a processos industriais.
                """,
                "solucoes": """
                - Criar monitorização dedicada de grandes consumidores industriais.
                - Avaliar capacidade, redundância e qualidade de serviço em MAT.
                - Estudar potencial de autoconsumo industrial e eficiência energética.
                """
            }
        }
    }

    analise = ANALISE_OPERACIONAL.get(dist_det, {}).get(var)

    if analise:
        coln, cols = st.columns(2)

        with coln:
            st.markdown("### Narrativas principais")
            st.markdown(analise["narrativa"])

        with cols:
            st.markdown("### Soluções operacionais")
            st.markdown(analise["solucoes"])
    else:
        st.info("Ainda não existe análise operacional específica para esta combinação de distrito e variável.")


# ============================================================
# SEC 3
# ============================================================

else:
    st.header("3. Clustering Energético")
    if clusters is None:
        st.warning("Não encontrei concelhos_clusters_portugal.csv/.xlsx na pasta data/."); st.stop()

    f1, f2, f3 = st.columns([1.05, 1.2, 1.35])
    with f1:
        cluster_opts = sorted([int(x) for x in clusters["Cluster"].dropna().unique()])
        sel_clusters = st.multiselect(
            "Filtrar cluster",
            cluster_opts,
            default=cluster_opts,
            format_func=lambda k: f"{k} — {CLUSTER_LABELS.get(int(k), 'Cluster')}",
            key="cluster_filter_cluster"
        )

    cl = clusters[clusters["Cluster"].astype("Int64").isin(sel_clusters)].copy() if sel_clusters else clusters.iloc[0:0].copy()

    with f2:
        dist_opts = sorted(clusters["Distrito"].dropna().unique())
        dists = st.multiselect(
            "Filtrar distrito",
            dist_opts,
            default=default_districts(dist_opts),
            key="cluster_filter_district"
        )

    if dists:
        cl = cl[cl["Distrito"].isin(dists)].copy()
    else:
        cl = cl.iloc[0:0].copy()

    with f3:
        concs = st.multiselect("Filtrar concelho", sorted(cl["Concelho"].dropna().unique()), default=[], key="cluster_filter_county")
    if concs:
        cl = cl[cl["Concelho"].isin(concs)].copy()

    counts = cl.groupby("Cluster").size().to_dict() if not cl.empty else {}
    st.subheader("Legenda dos clusters")
    cols = st.columns(5)
    for i, k in enumerate(sorted(CLUSTER_LABELS)):
        with cols[i]:
            st.markdown(f"""
            <div style='border:1px solid #3d2360; border-radius:10px; padding:10px; height:285px; overflow-y:auto; background:#180d27; box-sizing:border-box;'>
            <div style='background:{CLUSTER_CORES[k]}; color:white; width:34px; height:34px; display:flex; align-items:center; justify-content:center; border-radius:5px; font-weight:bold; margin-bottom:6px;'>{k}</div>
            <b style='color:#ffffff;'>{CLUSTER_LABELS[k]}</b><br>
            <small style='color:#d8c8f2;'>{counts.get(k,0)} concelhos selecionados</small><br><br>
            <span style='font-size:12px; color:#f4ecff;'>{CLUSTER_DESCRICOES[k]}</span><br><br>
            <span style='font-size:11.5px; color:#d8c8f2;'><b>Variáveis determinantes:</b><br>{CLUSTER_DETERMINANTES[k]}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    if cl.empty:
        st.info("Seleciona pelo menos um cluster e um distrito para gerar o mapa e a tabela.")
    else:
        c1, c2 = st.columns([1.35, 1])
        with c1:
            st.subheader("Mapa de clusters")
            mt = st.radio("Tipo de mapa", ["Interativo", "Estático"], horizontal=True, key="cluster_map_type")
            if gdf_concelhos is None:
                st.warning("Falta o ficheiro CAOP GeoPackage.")
            elif mt == "Interativo" and gdf_concelhos_wgs is not None:
                cluster_pydeck_map(gdf_concelhos_wgs, cl)
            else:
                cluster_static(gdf_concelhos, cl)
        with c2:
            st.subheader("Tabela")
            st.dataframe(
                cl[["Distrito", "Concelho", "Codigo_Concelho", "Cluster", "Nome_Cluster"]].sort_values(["Cluster", "Distrito", "Concelho"]),
                use_container_width=True,
                height=430
            )

        st.divider()
        cluster_indicator_explorer(df, cl)

        st.subheader("Perfil médio por cluster")
        dc = df.merge(cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster"]], on=["Distrito_norm", "Concelho_norm"], how="inner")
        pv = [v for v in ["Consumo_per_capita", "Energia_BT_per_capita", "Energia_MAT_per_capita", "CPEs_por_1000_hab", "UPACs_por_1000_hab", "Densidade_Populacional"] if v in dc.columns]
        if pv:
            prof = dc.groupby(["Cluster", "Nome_Cluster"], as_index=False)[pv].mean().round(2)
            st.dataframe(prof, use_container_width=True)

st.divider()
st.caption("Protótipo académico — Deployment CRISP-DM | Caracterização energética municipal em Portugal")
