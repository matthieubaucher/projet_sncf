import streamlit as st

st.title("Assurance SNCF")

st.write("""
Démonstrateur d'analyse des retards, annulations et coûts des liaisons SNCF pour l'assurance.
""")

st.page_link("pages/prediction_retard.py", label="Prévision des retards")