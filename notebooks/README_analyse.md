# Analyse des retards et score de fiabilité

Auteur : Machoudi ADEGOUNTE

Mon objectif est d'expliquer les retards et annulations des liaisons TGV, de savoir si le risque d'une liaison est répétitif ou accidentel, et d'en déduire un score de fiabilité par liaison pour RailInsight. Tout le détail est dans `notebooks/01_analyse.ipynb`. Je vous invite à y jeter un œil, surtout les sections 4 à 6.

## Utilisation

Le notebook charge les données avec `get_dataframe()` (dossier `database`) et ne garde que la période de l'analyse, de janvier 2018 à juin 2026. Cette période est définie dans `src/projet_sncf/business/analysis/constants.py`. Le calcul du score est dans `src/projet_sncf/business/analysis/`, et l'application l'appelle avec `get_reliability_table()`.

## Démarche

Je suis parti de Paris Montparnasse - Nantes, puis j'ai généralisé aux 146 liaisons du dataset (triplet gare de départ, gare d'arrivée, service), dont 123 observées au moins 24 mois. Je n'applique qu'un filtre minimal (73 lignes écartées), le nettoyage de fond restant une tâche d'équipe.

## Score de fiabilité

Avec $A$ les trains annulés, $R$ les trains en retard à l'arrivée et $P$ les circulations prévues, additionnés sur tous les mois de la liaison :

$$\tau = \frac{A + R}{P}, \qquad \text{score} = 100 \times (1 - \tau)$$

J'y ajoute la régularité (part des perturbations dans les 10 % de mois les plus perturbés, hors mois de choc national), la confiance (« peu fiable » sous 24 mois) et un tiers (bornes à 81 et 85).

## Conclusions

- Huit mois sur 105 sont des chocs nationaux (grèves, confinements). Je les écarte de la saisonnalité et de la régularité, mais je les garde dans le score.
- Aucune cause ne domine sur le réseau : matériel roulant, causes externes, gestion du trafic et infrastructure arrivent en tête selon les liaisons.
- La saisonnalité est faible par liaison, avec des retards plus hauts en juin-juillet au niveau national.
- Le risque est plutôt répétitif pour la majorité des liaisons, avec quelques cas accidentels.
- Les scores vont de 44 à 91, surtout tirés par le taux de retard.

## Causes possibles (hypothèses)

Les liaisons les plus perturbées ont plus de gestion du trafic (24 % contre 17-18 %). Le dataset ne me permet pas de confirmer ces pistes.

## Limites

Le dataset ne contient pas de prix, le seuil de retard est à vérifier (5, 10 ou 15 minutes), 14 liaisons apparaissent à la fois en national et en international de juillet à septembre 2025, et le score décrit le passé sans le prévoir.

## Pistes pour la suite

1. Prévision (une personne) : par exemple en comparant aux mêmes mois des années précédentes.
2. Tests d'hypothèses : saisonnalité, cause selon le service, lien entre niveau de perturbation et régularité.
3. Alignement avec le nettoyage : définition d'une liaison, doublons de l'été 2025.
4. Prix : une hypothèse de coût par train annulé ou en retard permet de passer du score à un montant. L'application le fait avec une indemnité choisie par l'utilisateur.
5. Application : la page « Carte interactive » montre les liaisons colorées selon leur niveau de fiabilité, avec une estimation du coût attendu des perturbations (la prime pure). Elle utilise un jeu de données externe pour les coordonnées des gares, et le coût dépend de l'indemnité choisie.

Quelle que soit la forme retenue, je pense que l'interface doit rester simple pour un assureur : peu d'indicateurs, des mots plutôt que des mesures techniques, et un avertissement quand une liaison manque de recul.