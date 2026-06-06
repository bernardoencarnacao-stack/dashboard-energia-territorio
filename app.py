import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import unicodedata
from pathlib import Path

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
    1: "Baixa densidade, consumo moderado e fraca penetração de produção solar distribuída.",
    2: "Perfil equilibrado com consumo doméstico dominante e adoção crescente de UPAC.",
    3: "Indústria pesada com consumo em MAT muito acima da média.",
    4: "Concelhos metropolitanos densos com forte peso do consumo urbano/residencial.",
    5: "Consumo extremo singular dominado por indústria pesada, logística e petroquímica."
}
CLUSTER_CORES = {1: "#1f77b4", 2: "#2ca02c", 3: "#9467bd", 4: "#e377c2", 5: "#bcbd22"}

VAR_GROUPS = {
    "Variáveis absolutas": {
        "Energia_Ativa_Total": "Energia Ativa Total",
        "Energia_BT": "Energia BT",
        "Energia_MAT": "Energia MAT",
        "Ligacoes_Total": "Ligações à rede",
    },
    "Variáveis relativas": {
        "Consumo_per_capita": "Consumo per capita",
        "Energia_BT_per_capita": "Energia BT per capita",
        "Energia_MAT_per_capita": "Energia MAT per capita",
        "CPEs_por_1000_hab": "CPEs por 1000 habitantes",
        "UPACs_por_1000_hab": "UPACs por 1000 habitantes",
        "Prop_energia_BT": "Proporção Energia BT",
        "Prop_energia_MAT": "Proporção Energia MAT",
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
SUM_VARS = {"Energia_Ativa_Total", "Energia_BT", "Energia_MAT", "CPEs_Total", "UPACs_Total", "Ligacoes_Total"}
CLIMA_VARS = {"Temp_Media_Mensal", "Precipitacao_Total_Mensal", "Radiacao_Global_Total_Mensal", "Humidade_Relativa_Media_Mensal"}


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


def agg_rule(v):
    if v in SUM_VARS:
        return "sum"
    if v in CLIMA_VARS:
        return "first"
    return "mean"


def agg(df, keys, var):
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
        return s, "CPEs por 1000 habitantes"
    if var == "UPACs_por_1000_hab":
        return s, "UPACs por 1000 habitantes"
    if var in ["CPEs_Total", "UPACs_Total"]:
        if mx >= 1_000_000:
            return s / 1_000_000, "milhões"
        if mx >= 1_000:
            return s / 1_000, "milhares"
        return s, "n.º"
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


def choose_years(df, key):
    anos = sorted([int(x) for x in df["Ano"].dropna().unique()]) if "Ano" in df.columns else []
    return st.multiselect("Ano", anos, default=anos, key=key)


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

# ============================================================
# PLOTS
# ============================================================

def line_district(df, var, saz=False):
    keys = ["Mês", "Distrito"] if saz else ["Data", "Distrito"]
    t = agg(df, keys, var)
    t["Valor"], unit = scale_var(t[var], var)
    distritos = sorted(t["Distrito"].dropna().unique())
    palette = discrete_palette(distritos)

    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    x = "Mês" if saz else "Data"
    sns.lineplot(data=t, x=x, y="Valor", hue="Distrito", palette=palette, marker="o", markersize=4, linewidth=1.6, ax=ax)
    ax.set_title(("Sazonalidade média" if saz else "Evolução temporal") + f" — {label_var(var)}", fontsize=11)
    ax.set_xlabel("Mês" if saz else "Data")
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))
    if saz:
        ax.set_xticks(range(1, 13)); ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    ax.grid(True, linestyle="--", alpha=.3)
    ax.legend(title="Distrito", fontsize=8, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    fig.subplots_adjust(right=0.78)
    showfig(fig)


def bar_district(df, var):
    t = agg(df, ["Distrito"], var)
    t["Valor"], unit = scale_var(t[var], var)
    t = t.sort_values("Valor", ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    sns.barplot(data=t, x="Valor", y="Distrito", ax=ax, color="#4C78A8")
    ax.set_title(f"Ranking distrital — {label_var(var)}", fontsize=11)
    ax.set_xlabel(f"{label_var(var)} ({unit})" if unit else label_var(var)); ax.set_ylabel("")
    showfig(fig)


def line_single_county(df, var, concelho, saz=False):
    t = agg(df[df["Concelho"] == concelho], ["Mês" if saz else "Data"], var)
    t["Valor"], unit = scale_var(t[var], var)
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    x = "Mês" if saz else "Data"
    sns.lineplot(data=t, x=x, y="Valor", marker="o", markersize=4, linewidth=1.6, ax=ax)
    ax.set_title(("Sazonalidade média" if saz else "Evolução temporal") + f" — {label_var(var)} | {concelho}", fontsize=11)
    ax.set_xlabel("Mês" if saz else "Data")
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))
    if saz:
        ax.set_xticks(range(1, 13)); ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])
    ax.grid(True, linestyle="--", alpha=.3)
    showfig(fig)


def line_counties_multi(df, var, saz=False):
    key = "Mês" if saz else "Data"
    t = agg(df, [key, "Concelho"], var)
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

    ax.set_title(("Sazonalidade média" if saz else "Evolução temporal") + f" por concelho — {label_var(var)}", fontsize=11)
    ax.set_xlabel("Mês" if saz else "Data")
    ax.set_ylabel(f"{label_var(var)} ({unit})" if unit else label_var(var))

    if saz:
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels([mes_labels()[m] for m in range(1, 13)])

    ax.grid(True, linestyle="--", alpha=.3)
    ax.legend(title="Concelho", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7, borderaxespad=0)
    fig.subplots_adjust(right=0.76)
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
            legend_kwds={"label": f"{label_var(var)} ({unit})" if unit else label_var(var)},
            missing_kwds={"color": "lightgrey"}, ax=ax)
    add_labels(ax, mp, "distrito", fs=4.6)
    ax.set_title(title, fontsize=10.5); ax.axis("off")
    showfig(fig)


def map_counties(df, gdf, var, title, distrito=None, labels=False, scale_df=None, figsize=(5, 5.8)):
    mp, unit, vmin, vmax = prepare_map_counties(df, gdf, var, scale_df)
    if distrito and distrito != "Portugal Continental":
        mp = mp[mp["Distrito_norm"] == norm_name(distrito)].copy()
    fig, ax = plt.subplots(figsize=figsize)
    mp.plot(column="Valor", cmap=MAP_CM.get(var, "viridis"), vmin=vmin, vmax=vmax,
            linewidth=.25 if not distrito or distrito == "Portugal Continental" else .7,
            edgecolor="gray" if not distrito or distrito == "Portugal Continental" else "black",
            legend=True, legend_kwds={"label": f"{label_var(var)} ({unit})" if unit else label_var(var)},
            missing_kwds={"color": "lightgrey"}, ax=ax)
    if labels and distrito and distrito != "Portugal Continental":
        add_labels(ax, mp, "municipio", fs=5.6)
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
        add_labels(ax, mp, "municipio", fs=5.6)
    ax.set_title(title, fontsize=10.5); ax.axis("off")
    showfig(fig)

# ============================================================
# CLUSTER MAPS
# ============================================================

def cluster_interactive(gdf_wgs, cl):
    try:
        import folium
        from streamlit_folium import st_folium
    except Exception:
        st.warning("Para mapa interativo: python -m pip install folium streamlit-folium")
        return
    mp = gdf_wgs.merge(cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster", "Distrito", "Concelho"]], on=["Distrito_norm", "Concelho_norm"], how="inner")
    if mp.empty:
        st.info("Sem concelhos para os filtros selecionados."); return
    m = folium.Map(location=[39.6, -8.0], zoom_start=6.4, tiles="cartodbpositron")
    def style(f):
        c = f["properties"].get("Cluster")
        return {"fillColor": CLUSTER_CORES.get(int(c), "#eee") if pd.notna(c) else "#eee", "color": "white", "weight": .6, "fillOpacity": .82}
    folium.GeoJson(mp, style_function=style, tooltip=folium.GeoJsonTooltip(
        fields=["Concelho", "Distrito", "Cluster", "Nome_Cluster"],
        aliases=["Concelho:", "Distrito:", "Cluster:", "Tipo:"]
    )).add_to(m)
    st_folium(m, height=500, use_container_width=True)


def cluster_static(gdf, cl):
    mp = gdf.merge(cl[["Distrito_norm", "Concelho_norm", "Cluster"]], on=["Distrito_norm", "Concelho_norm"], how="inner")
    if mp.empty:
        st.info("Sem concelhos para os filtros selecionados."); return
    mp["cor"] = mp["Cluster"].map(CLUSTER_CORES).fillna("#eee")
    fig, ax = plt.subplots(figsize=(5.5, 6.5))
    mp.plot(color=mp["cor"], edgecolor="white", linewidth=.35, ax=ax)
    ax.set_title("Mapa de clusters energéticos", fontsize=10.5); ax.axis("off")
    showfig(fig)

# ============================================================
# LOAD
# ============================================================

df = load_df(DATASET)
clusters = load_clusters(CLUSTERS_CSV, CLUSTERS_XLSX)
gdf_distritos, gdf_concelhos, gdf_concelhos_wgs = load_geo(CAOP)
if df is None:
    st.error("Não encontrei data/dataset_final.csv. Coloca o ficheiro na pasta data/."); st.stop()

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
            - filtrar por distrito e concelho;
            - observar mapas de clusters;
            - consultar a tabela dos concelhos;
            - comparar perfis médios por cluster.

            Serve para transformar concelhos em perfis operacionais.
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

        Em todas as áreas, as variáveis estão organizadas por secções: absolutas, relativas, climáticas e qualidade de serviço.
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
        - segmentar estratégias por cluster energético.
        """
    )


elif sec == "1. Visualização Exploratória":
    st.header("1. Visualização Exploratória")
    st.markdown("Exploração dinâmica dos indicadores por distrito e por concelho.")

    c1, c2, c3 = st.columns([1.25, 1.05, 1.2])
    with c1:
        var = choose_var(df, "expl")
    with c2:
        anos = choose_years(df, "expl_anos")
    with c3:
        level = st.radio("Granularidade", ["Nível distrito", "Nível concelho"], horizontal=True)

    dbase = df[df["Ano"].isin(anos)].copy() if anos else df.copy()
    st.divider()

    if level == "Nível distrito":
        st.subheader("Análise ao nível do distrito")
        st.caption("Os concelhos escolhidos influenciam a média/soma distrital apresentada.")

        a, b, c = st.columns([1.05, 1.55, 1.2])
        with a:
            dists = st.multiselect(
                "Distritos",
                sorted(dbase["Distrito"].dropna().unique()),
                default=sorted(dbase["Distrito"].dropna().unique()),
                key="expl_dist_level_dists"
            )

        dtmp = dbase[dbase["Distrito"].isin(dists)].copy() if dists else dbase.copy()

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
            viz = st.selectbox(
                "Visualização",
                ["Evolução temporal", "Sazonalidade", "Ranking distrital", "Mapa por distrito", "Tabela agregada"],
                key="expl_dist_viz"
            )

        if viz == "Evolução temporal":
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
                    default=sorted(dbase["Distrito"].dropna().unique()),
                    key="expl_conc_comp_dists"
                )

            dd = dbase[dbase["Distrito"].isin(dists)].copy() if dists else dbase.copy()

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
                viz = st.selectbox(
                    "Visualização",
                    ["Mapa por concelho", "Barras por concelho", "Tabela"],
                    key="expl_conc_comp_viz"
                )

            if viz == "Mapa por concelho":
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
                        figsize=(5.2, 6.0)
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
                viz = st.selectbox(
                    "Visualização",
                    ["Mapa do distrito", "Barras por concelho", "Evolução temporal dos concelhos", "Sazonalidade dos concelhos", "Tabela"],
                    key="expl_conc_detail_viz"
                )

            if viz == "Mapa do distrito":
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

    de = df[df["Distrito"].isin(DISTRITOS_ESTUDADOS)].copy()


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
    a, b = st.columns(2)
    with a:
        dists = st.multiselect("Filtrar distrito", sorted(clusters["Distrito"].dropna().unique()), default=sorted(clusters["Distrito"].dropna().unique()))
    cl = clusters[clusters["Distrito"].isin(dists)].copy() if dists else clusters.copy()
    with b:
        concs = st.multiselect("Filtrar concelho", sorted(cl["Concelho"].dropna().unique()), default=[])
    if concs: cl = cl[cl["Concelho"].isin(concs)].copy()
    counts = cl.groupby("Cluster").size().to_dict()
    st.subheader("Legenda dos clusters")
    cols = st.columns(5)
    for i, k in enumerate(sorted(CLUSTER_LABELS)):
        with cols[i]:
            st.markdown(f"""
            <div style='border:1px solid #ddd; border-radius:8px; padding:9px; min-height:125px;'>
            <div style='background:{CLUSTER_CORES[k]}; color:white; width:34px; height:34px; display:flex; align-items:center; justify-content:center; border-radius:4px; font-weight:bold;'>{k}</div>
            <b>{CLUSTER_LABELS[k]}</b><br><small>{counts.get(k,0)} concelhos selecionados</small><br>
            <span style='font-size:12px; color:#555;'>{CLUSTER_DESCRICOES[k]}</span></div>
            """, unsafe_allow_html=True)
    st.divider()
    c1, c2 = st.columns([1.35, 1])
    with c1:
        st.subheader("Mapa de clusters")
        mt = st.radio("Tipo de mapa", ["Estático", "Interativo"], horizontal=True)
        if gdf_concelhos is None: st.warning("Falta o ficheiro CAOP GeoPackage.")
        elif mt == "Interativo" and gdf_concelhos_wgs is not None: cluster_interactive(gdf_concelhos_wgs, cl)
        else: cluster_static(gdf_concelhos, cl)
    with c2:
        st.subheader("Tabela")
        st.dataframe(cl[["Distrito", "Concelho", "Codigo_Concelho", "Cluster", "Nome_Cluster"]].sort_values(["Cluster", "Distrito", "Concelho"]), use_container_width=True, height=430)
    st.subheader("Perfil médio por cluster")
    dc = df.merge(cl[["Distrito_norm", "Concelho_norm", "Cluster", "Nome_Cluster"]], on=["Distrito_norm", "Concelho_norm"], how="inner")
    pv = [v for v in ["Consumo_per_capita", "Energia_BT_per_capita", "Energia_MAT_per_capita", "CPEs_por_1000_hab", "UPACs_por_1000_hab", "Densidade_Populacional"] if v in dc.columns]
    if pv:
        prof = dc.groupby(["Cluster", "Nome_Cluster"], as_index=False)[pv].mean().round(2)
        st.dataframe(prof, use_container_width=True)

st.divider()
st.caption("Protótipo académico — Deployment CRISP-DM | Caracterização energética municipal em Portugal")
