# Dashboard de Caracterização Energética Municipal

Este repositório contém uma aplicação em Streamlit desenvolvida no âmbito de um projeto de análise de dados sobre o consumo elétrico em Portugal, à escala municipal, entre 2021 e 2024.

A plataforma funciona como proposta de deployment dos resultados obtidos nas fases de análise exploratória e clustering, permitindo explorar indicadores energéticos, demográficos, climáticos e territoriais de forma interativa.

## Funcionalidades principais

- Visualização exploratória por distrito e concelho
- Mapas territoriais de consumo, CPEs, UPACs, BT e MAT
- Análise dos quatro distritos estudados: Faro, Setúbal, Aveiro e Castelo Branco
- Narrativas territoriais e soluções operacionais para a E-Redes
- Clustering energético dos concelhos
- Mapa interativo de clusters
- Ranking interativo por cluster e variável

## Como correr localmente

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
