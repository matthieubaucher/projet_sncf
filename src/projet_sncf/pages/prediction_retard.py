import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from projet_sncf.database import dataloader as dl
from projet_sncf.api import Retard_prevision_API as retard_api

st.markdown("""
<style>
.stApp {
    background:
        linear-gradient(135deg,
            #f5f7fa 0%,
            #e4ecf7 50%,
            #dce8ff 100%);
}

.stNumberInput input {
    background-color: #f8f0da;
}

.stSelectbox div[data-baseweb="select"] {
    background-color: #f8f0da;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Simulation de retard",
    layout="wide"
)

@st.cache_data
def get_axes():
    return dl.get_axes()

def normalise_prct():
    if "parameters" not in st.session_state:
        return 
    total = 0
    for parameter in retard_api.get_parameters(): 
        if parameter.startswith("Prct"):
            total += st.session_state[parameter]
    total /= 100.0
    for parameter in retard_api.get_parameters(): 
        if parameter.startswith("Prct"):
            st.session_state[parameter] /= total


st.title("Simulation sur les retards et les annulations")

st.write("""
Choisissez les variables en entrées et la cible à prévoir et nous simulons ce qui pourrait se passer !
""")


left, center, right = st.columns([1, 2, 1])

with center:

    if "axe" not in st.session_state:
        st.session_state.axe = None
    st.session_state.axe = st.selectbox(
        "Axe",
        get_axes()
    )

    if "cible" not in st.session_state:
        st.session_state.cible = None
    st.session_state.cible = st.selectbox(
        "Cible",
        retard_api.get_cibles()
    )

    if "parameters" not in st.session_state:
        st.session_state.parameters = {}
    for parameter in retard_api.get_parameters():
        if parameter.startswith("Prct"):
            value = st.number_input(
                parameter,
                min_value=0.0,
                max_value=100.0,
                value=16.65,
                step=2.35,
                key=parameter,
                on_change=normalise_prct
            )
        elif parameter=="Temps":
            col1, col2 = st.columns(2)
            with col1:
                annee = st.selectbox(
                    "Année",
                    range(2018, 2026),
                    index=7,
                    key="temps_annee",
                )
            with col2:
                mois = st.selectbox(
                    "Mois",
                    range(1, 13),
                    index=1,
                    key="temps_mois",
                    format_func=lambda m: [
                        "Janvier", "Février", "Mars", "Avril","Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
                    ][m - 1]
                )
            st.session_state["Temps"] = dl.get_temps(annee, mois)
        else:
            st.number_input(
                parameter,
                min_value=0,
                max_value=15000,
                value=0,
                key=parameter
            )
    
    st.session_state.parameters = {
        p: st.session_state[p]
        for p in retard_api.get_parameters()
    }

if st.button("Evaluate"):
    points = retard_api.simulation_scenario_utilisateur(st.session_state.parameters, st.session_state.axe, st.session_state.cible)
    fig, ax = plt.subplots(figsize=(8, 2))
    sns.boxplot(
        x=points,
        ax=ax
    )
    st.pyplot(fig)
