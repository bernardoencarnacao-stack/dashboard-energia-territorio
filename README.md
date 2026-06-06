# Dashboard Energético Municipal — Streamlit V5

Versão refinada do protótipo de deployment CRISP-DM.

## Estrutura esperada

Coloca os ficheiros numa pasta `data/` ao lado de `app.py`:

```text
data/
├── dataset_final.csv
├── concelhos_clusters_portugal.csv
└── Continente_CSOP2025.gpkg
```

Também é aceite `concelhos_clusters_portugal.xlsx`.

## Instalação

```bash
python -m pip install -r requirements.txt
```

## Correr

```bash
python -m streamlit run app.py
```

## Alterações da V5

- Nova página inicial/introdutória com explicação de uso do dashboard.
- Métricas gerais movidas para a página inicial.
- Secção dos 4 distritos voltou a usar escala original para consumo per capita, sem isolar outliers.
- Mantém tema escuro roxo, variáveis organizadas e clustering com mapa estático/interativo.

- Secção dos 4 distritos enriquecida com narrativas e soluções operacionais por distrito e variável.
