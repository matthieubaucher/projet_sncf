
import streamlit as st

def fibo(n):
    if n<=1:
        return 1
    return fibo(n-1) + fibo(n-2)

# Initialisation
if "compteur" not in st.session_state:
    st.session_state.compteur = 0

# Incrémentation
if st.button("Incrémenter"):
    st.session_state.compteur += 1

st.write("Valeur actuelle :", fibo(st.session_state.compteur))

