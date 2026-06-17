# Dashboard de Caracterização Energética Municipal

Aplicação desenvolvida em **Streamlit** no âmbito do projeto **“Mapeamento espaço-temporal do consumo elétrico e análise dos seus determinantes territoriais: estudo aplicado a concelhos de Portugal (2021–2024)”**.

A plataforma permite explorar dados de consumo elétrico, indicadores territoriais e resultados de clustering energético ao nível municipal.

## Funcionalidades

* Análise exploratória por distrito e concelho;
* Visualização de consumo elétrico, CPEs e UPACs;
* Mapas interativos;
* Comparação com variáveis climáticas;
* Clustering energético dos concelhos;
* Rankings e análises territoriais.

## Estrutura do repositório

```text
.
├── .streamlit/
│   └── config.toml
├── data/
│   ├── Continente_CAOP2025.gpkg
│   ├── concelhos_clusters_portugal.csv
│   ├── dataset_final_unificado.xlsx
│   └── upacs_tratado.xlsx
├── .gitattributes
├── README.md
├── app.py
└── requirements.txt
```

## Principais ficheiros

* **app.py** – aplicação principal.
* **requirements.txt** – dependências do projeto.
* **config.toml** – configurações do Streamlit.
* **dataset_final_unificado.xlsx** – dataset principal.
* **upacs_tratado.xlsx** – dados de UPACs.
* **concelhos_clusters_portugal.csv** – classificação dos clusters.
* **Continente_CAOP2025.gpkg** – informação geográfica para os mapas.

## Executar localmente

Instalar dependências:

```bash
python -m pip install -r requirements.txt
```

Executar a aplicação:

```bash
python -m streamlit run app.py
```

A aplicação ficará disponível em:

```text
http://localhost:8501
```

## Deployment
A aplicação pode ser, e neste momento está, publicada através do **Streamlit Community Cloud**.

## Nota

O repositório utiliza **Git LFS** para gerir ficheiros de dados e ficheiros geográficos de maior dimensão.

