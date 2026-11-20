import matplotlib.pyplot as plt
import streamlit as st

from projet_sncf.api import Retard_prevision_API as retard_api
from projet_sncf.database import dataloader as dl

st.markdown(
    """
<style>
.stApp {
    background: #e4ecf7;
    color: black !important;
}

.stNumberInput input {
    background-color: #f8f0da;
    color: black !important;
}

.stNumberInput label,
.stNumberInput div {
    background: #e4ecf7 !important;
}
.stNumberInput p {
    background: #e4ecf7 !important;
    color: black !important;
}

.stButton * {
    background-color: #f8f0da;
    color: black !important;
}

h1, h2, h3 {
    color: black !important;
}
.stMarkdown p {
    color: black !important;
}
.stSelectbox * {
    background-color: #f8f0da;
    color: black !important;
}
.stMultiselect * {
    background-color: #f8f0da;
    color: black !important;
}
[data-testid="stMultiSelect"] * {
    color: black !important;
    background-color: #f8f0da !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.set_page_config(page_title="Simulation de retard", layout="wide")


@st.cache_data
def get_axes():
    return dl.get_axes()


st.header("Clustering des modèles prenant en paramètres les causes de retards")

st.write(
    "Choisissez les variables d'entrée et la cible pour explorer les "
    "groupes de modèles."
)

left, center, right = st.columns([1, 2, 1])

with center:
    if "cible" not in st.session_state:
        st.session_state.cible = None
    st.session_state.cible = st.selectbox("Cible", retard_api.get_cibles())

    if "axes" not in st.session_state:
        st.session_state.axes = []

    st.session_state.axes = st.multiselect(
        "Axes", options=get_axes(), default=st.session_state.axes
    )

if st.button("Clusteriser"):
    try:
        points = retard_api.clusterise_ligne_et_axe(
            st.session_state.axes, st.session_state.cible
        )
        fig, ax = plt.subplots(figsize=(8, 6))

        ax.scatter(points[:, 0], points[:, 1])

        ax.set_xlabel("Dimension 1")
        ax.set_ylabel("Dimension 2")
        ax.set_title("Clustering de modèle")

        st.pyplot(fig)

        st.write(
            "Vous pouvez voir si certains modèles ont tendance a être "
            "proches, voir à se regrouper"
        )
    except Exception as e:
        st.error(str(e))
