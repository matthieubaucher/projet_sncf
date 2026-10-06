from projet_sncf.main import fibo

def test_fibbo_base():
    assert fibo(1)==1, "erreur base on veut 1 pour 1"

def test_fibbo_base2():
    assert fibo(0)==1, "erreur base on veut 1 pour 0"

def test_fibbo_nombre_grand():
    assert fibo(5)==100, "erreur base on veut 100 pour 5"

def test_fibbo_cas_erreur():
    assert fibo(-1)==0, "erreur cas -1"  

