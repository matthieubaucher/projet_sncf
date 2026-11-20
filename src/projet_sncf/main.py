from pathlib import Path

import streamlit as st


def run_app() -> None:
	"""Lance l'application avec une liste explicite de pages."""
	pages_dir = Path(__file__).resolve().parent / "pages"
	pages = {
		"RailInsight": [
			st.Page(pages_dir / "home.py", title="Accueil", default=True),
		],
		"Analyses": [
			st.Page(pages_dir / "analyses_trajets.py", title="Analyse des perturbations"),
			st.Page(pages_dir / "clustering_lignes.py", title="Clustering des modèles"),
		],
		"Prévisions": [
			st.Page(pages_dir / "prediction_retard.py", title="Simulation de retard"),
			st.Page(
				pages_dir / "prevision_perturbations.py",
				title="Prévision des perturbations",
			),
		],
		"Réseau": [
			st.Page(pages_dir / "reliability_map.py", title="Carte de fiabilité"),
		],
	}
	st.navigation(pages, position="sidebar").run()

if __name__ == "__main__":
	run_app()
