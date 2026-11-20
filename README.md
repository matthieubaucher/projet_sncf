# Projet SNCF

[![Python](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/)
[![GitHub](https://img.shields.io/badge/GitHub-projet__sncf-181717?logo=github)](https://github.com/projectSNCF-2026/projet_sncf)
[![Tests](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/tests.yml/badge.svg)](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/tests.yml)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://projetsncf-e6kkjdxhkpfr4wctupym6q.streamlit.app/)

RailInsight : application Streamlit qui note la fiabilité des liaisons TGV, pour aider un assureur à évaluer le risque.

## Application en ligne

https://projetsncf-e6kkjdxhkpfr4wctupym6q.streamlit.app/

L'application se met à jour automatiquement à chaque modification de la branche `develop`.

## Lancer en local

```
uv run streamlit run src/projet_sncf/app.py
```

## Tests

```
uv run pytest
```

## Déployer sur Streamlit Cloud

Sur [share.streamlit.io](https://share.streamlit.io/) : Create app, puis Deploy a public app from GitHub.

- Repository : `projectSNCF-2026/projet_sncf`
- Branch : `develop`
- Main file path : `src/projet_sncf/app.py`