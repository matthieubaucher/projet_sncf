from projet_sncf.streamlit_app import fibo

def test_fibbo_base():
    assert fibo(1)==1, "erreur base on veut 1 pour 1"

def test_fibbo_base2():
    assert fibo(0)==1, "erreur base on veut 1 pour 0"

def test_fibbo_nombre_grand():
    result = fibo(5)
    assert result, f"erreur base on veut 13 pour 5 obtenu={result}"

def test_fibbo_cas_erreur():
    result = fibo(-1)
    assert result==1, f"erreur cas -1 obtenu={result}"  

