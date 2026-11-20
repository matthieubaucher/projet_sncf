from projet_sncf.business.service.Prevision_de_retard import clusterise

def test_clusterise_nominal():
    # Given
    axes = [["NICE VILLE", "PARIS LYON"], ["NANTES", "PARIS MONTPARNASSE"], ["LILLE", "LYON PART DIEU"], ["LAUSANE", "PARIS LYON"]]
    cible = "prct annulation"

    #When
    result = clusterise(axes, cible)

    #Then 
    assert result is not None
