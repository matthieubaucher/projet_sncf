"""Données de la carte de fiabilité, sans Streamlit."""

# Imports
import math
import pandas as pd

# Constants
COL_DEPARTURE = "Gare de départ"
COL_ARRIVAL = "Gare d'arrivée"
COL_SERVICE = "Service"

TIER_LESS = "moins fiable"
TIER_MIDDLE = "intermédiaire"
TIER_MORE = "plus fiable"
CONFIDENCE_LOW = "peu fiable"

TIER_COLORS = {
    TIER_LESS: (214, 48, 49),
    TIER_MIDDLE: (240, 150, 0),
    TIER_MORE: (20, 140, 40),
}
NO_TIER_COLOR = (150, 150, 150)
ALPHA = 230
WIDTH = 3

# Courbure des lignes tracées sur l'app
BEND = 0.08
CURVE_POINTS = 24
# Écart entre les deux sens d'une même voie
OFFSET_DEGREES = 0.05
# L'écart diminue près des gares
OFFSET_TAPER_KM = 15.0
KM_PER_DEGREE = 110.0

PARIS_GROUP = "PARIS (toutes les gares)"
CAUSE_NAMES = [
    "Externes",
    "Infrastructure",
    "Gestion du trafic",
    "Matériel roulant",
    "Gestion en gare",
    "Prise en compte des voyageurs",
]
LABEL_SUFFIXES = (
    "St Charles",
    "Part Dieu",
    "St Jean",
    "Challes Les Eaux",
    "Ville",
    "Loche",
    "(Ain)",
    "TGV",
)
# Largeur d'un caractère et hauteur d'une étiquette
LABEL_CHAR_WIDTH = 0.35
LABEL_HEIGHT = 0.5

INSURER_READINGS = {
    TIER_MORE: (
        "success",
        "Risque faible : liaison favorable à assurer, une prime attractive est possible.",
    ),
    TIER_MIDDLE: (
        "warning",
        "Risque modéré : assurable, avec une prime ajustée ou une franchise.",
    ),
    TIER_LESS: ("error", "Risque élevé : prime majorée, ou liaison à éviter."),
    None: ("info", "Niveau non classé : pas de recommandation."),
}

MODE_EACH_DIRECTION = "Chaque sens"
MODE_WORST_DIRECTION = "Le moins bon des deux sens"

LOWER_CASE_WORDS = {
    " En ": " en ",
    " De ": " de ",
    " La ": " la ",
    " Le ": " le ",
    " Des ": " des ",
}


# Functions
def display_name(station: str) -> str:
    """Rend lisible un nom de gare écrit en majuscules.

    Args:
        station (str): Nom de la gare, en majuscules.

    Returns:
        str: Le nom avec une majuscule à chaque mot, « TGV » gardé en majuscules et
        les petits mots (en, de, la, le, des) en minuscules.
    """
    name = station.title().replace(" Tgv", " TGV")
    for word, replacement in LOWER_CASE_WORDS.items():
        name = name.replace(word, replacement)
    return name


def build_curve(
    start: tuple[float, float],
    end: tuple[float, float],
    side: int = 1,
    bend: float = BEND,
    points: int = CURVE_POINTS,
) -> list[list[float]]:
    """Construit une ligne courbe entre deux points.

    Args:
        start (tuple[float, float]): Point de départ, en (longitude, latitude).
        end (tuple[float, float]): Point d'arrivée, en (longitude, latitude).
        side (int): 1 courbe vers la gauche, -1 vers la droite.
        bend (float): Décalage du milieu, en part de la distance entre les points.
        points (int): Nombre de points de la courbe.

    Returns:
        list[list[float]]: Les points de la courbe, chacun en [longitude, latitude].
        Si les deux points sont identiques, le point de départ est répété.
    """
    stretch = math.cos(math.radians((start[1] + end[1]) / 2))
    x0, y0 = start[0] * stretch, start[1]
    x1, y1 = end[0] * stretch, end[1]
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        return [list(start)] * points
    cx = (x0 + x1) / 2 - side * bend * dy
    cy = (y0 + y1) / 2 + side * bend * dx
    curve = []
    for i in range(points):
        t = i / (points - 1)
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t**2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t**2 * y1
        curve.append([round(x / stretch, 5), round(y, 5)])
    return curve


def route_key(station_a: str, station_b: str) -> str:
    """Donne la clé d'une paire de gares, la même dans les deux sens.

    Args:
        station_a (str): Première gare.
        station_b (str): Deuxième gare.

    Returns:
        str: Les deux noms triés par ordre alphabétique, séparés par `|`.
    """
    first, second = sorted([station_a, station_b])
    return f"{first}|{second}"


def offset_path(
    path: list[list[float]], distance: float = OFFSET_DEGREES
) -> list[list[float]]:
    """Décale un chemin vers la droite, pour que les deux sens d'une voie ne se chevauchent pas.

    Le décalage diminue près des gares, sur `OFFSET_TAPER_KM` kilomètres.

    Args:
        path (list[list[float]]): Points du chemin, chacun en [longitude, latitude].
        distance (float): Décalage maximal, en degrés.

    Returns:
        list[list[float]]: Le chemin décalé. Un chemin de moins de deux points est
        simplement copié.
    """
    count = len(path)
    if count < 2:
        return [list(point) for point in path]
    stretch = math.cos(math.radians(sum(point[1] for point in path) / count))
    xs = [point[0] * stretch for point in path]
    ys = [point[1] for point in path]

    along = [0.0]
    for i in range(1, count):
        along.append(
            along[-1] + math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]) * KM_PER_DEGREE
        )
    total = along[-1]

    shifted = []
    for i in range(count):
        before, after = max(i - 1, 0), min(i + 1, count - 1)
        dx, dy = xs[after] - xs[before], ys[after] - ys[before]
        length = math.hypot(dx, dy)
        weight = min(
            1.0, along[i] / OFFSET_TAPER_KM, (total - along[i]) / OFFSET_TAPER_KM
        )
        weight = max(weight, 0.0)
        if length == 0:
            shifted.append([path[i][0], path[i][1]])
            continue
        x = xs[i] + distance * weight * dy / length
        y = ys[i] - distance * weight * dx / length
        shifted.append([round(x / stretch, 5), round(y, 5)])
    return shifted


def prepare_links(
    scores: pd.DataFrame,
    stations: pd.DataFrame,
    mode: str = MODE_EACH_DIRECTION,
    routes: dict[str, list[list[float]]] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Construit les lignes à dessiner, une par liaison.

    Args:
        scores (pd.DataFrame): Tableau de fiabilité, une ligne par liaison.
        stations (pd.DataFrame): Coordonnées des gares, avec les colonnes `gare`,
            `latitude` et `longitude`.
        mode (str): `MODE_EACH_DIRECTION` garde toutes les liaisons,
            `MODE_WORST_DIRECTION` garde seulement le moins bon sens de chaque paire.
        routes (dict[str, list[list[float]]] | None): Chemins le long du réseau
            ferré, par clé de voie (voir `route_key`). Sans chemin, on trace une
            courbe.

    Returns:
        tuple[pd.DataFrame, int]: Les liaisons à tracer, les pires en dernier pour
        qu'elles soient dessinées au-dessus, et le nombre de liaisons écartées
        faute de coordonnées.
    """
    routes = routes or {}
    coordinates = stations.dropna(subset=["latitude", "longitude"]).set_index("gare")
    table = scores.copy()
    located = table[COL_DEPARTURE].isin(coordinates.index) & table[COL_ARRIVAL].isin(
        coordinates.index
    )
    unlocated = int((~located).sum())
    table = table[located].copy()

    if mode == MODE_WORST_DIRECTION and len(table):
        pair = table.apply(
            lambda r: tuple(sorted([r[COL_DEPARTURE], r[COL_ARRIVAL]]))
            + (r[COL_SERVICE],),
            axis=1,
        )
        table = table.loc[table.groupby(pair)["score"].idxmin()]
    table = table.sort_values("score", ascending=False)

    rows = []
    for _, row in table.iterrows():
        departure, arrival = row[COL_DEPARTURE], row[COL_ARRIVAL]
        key = route_key(departure, arrival)
        route = routes.get(key)
        if route:
            path = route if departure == key.split("|")[0] else route[::-1]
            if mode == MODE_EACH_DIRECTION:
                path = offset_path(path)
            trace = "voie"
        else:
            start = (
                coordinates.loc[departure, "longitude"],
                coordinates.loc[departure, "latitude"],
            )
            end = (
                coordinates.loc[arrival, "longitude"],
                coordinates.loc[arrival, "latitude"],
            )
            path = build_curve(start, end)
            trace = "courbe"
        red, green, blue = TIER_COLORS.get(row["tiers"], NO_TIER_COLOR)
        title = f"{display_name(departure)} → {display_name(arrival)}"
        if mode == MODE_WORST_DIRECTION:
            title = f"{display_name(departure)} ↔ {display_name(arrival)} (sens le moins bon)"
        cause = row.get("cause_dominante")
        rows.append(
            {
                "depart": departure,
                "arrivee": arrival,
                "service": row[COL_SERVICE],
                "titre": title,
                "path": path,
                "trace": trace,
                "color": [red, green, blue, ALPHA],
                "width": WIDTH,
                "score": row["score"],
                "tiers": (
                    row["tiers"] if isinstance(row["tiers"], str) else "non classé"
                ),
                "confiance": row["confiance"],
                "score_txt": f"{row['score']:.1f} / 100",
                "perturbation_txt": f"{100 * row['taux_perturbation']:.1f} %",
                "cause_txt": (
                    cause if isinstance(cause, str) else "aucune (pas de retard)"
                ),
                "mois_txt": f"{int(row['mois'])} mois",
            }
        )
    columns = [
        "depart",
        "arrivee",
        "service",
        "titre",
        "path",
        "trace",
        "color",
        "width",
        "score",
        "tiers",
        "confiance",
        "score_txt",
        "perturbation_txt",
        "cause_txt",
        "mois_txt",
    ]
    return pd.DataFrame(rows, columns=columns), unlocated


def station_options(links: pd.DataFrame) -> list[str]:
    """Donne les gares proposées dans le filtre, le groupe Paris en premier.

    Args:
        links (pd.DataFrame): Liaisons à tracer, avec les colonnes `depart` et
            `arrivee`.

    Returns:
        list[str]: `PARIS_GROUP`, puis les gares par ordre alphabétique.
    """
    names = sorted(set(links["depart"]) | set(links["arrivee"]))
    return [PARIS_GROUP] + names


def filter_links(
    links: pd.DataFrame,
    services: list[str],
    tiers: list[str],
    station: str | None = None,
    score_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Garde les liaisons qui respectent les filtres.

    Args:
        links (pd.DataFrame): Liaisons à tracer.
        services (list[str]): Services à garder.
        tiers (list[str]): Niveaux à garder.
        station (str | None): Une gare (de départ ou d'arrivée), ou `PARIS_GROUP`
            pour toutes les gares de Paris. Sans valeur, toutes les gares sont gardées.
        score_range (tuple[float, float] | None): Score minimal et maximal à garder.

    Returns:
        pd.DataFrame: Les liaisons qui passent tous les filtres.
    """
    keep = links["service"].isin(services) & links["tiers"].isin(tiers)
    if station == PARIS_GROUP:
        keep &= links["depart"].str.startswith("PARIS") | links[
            "arrivee"
        ].str.startswith("PARIS")
    elif station:
        keep &= (links["depart"] == station) | (links["arrivee"] == station)
    if score_range is not None:
        keep &= links["score"].between(score_range[0], score_range[1])
    return links[keep]


def label_name(station: str) -> str:
    """Donne le nom court d'une gare pour son étiquette sur la carte.

    Args:
        station (str): Nom de la gare, en majuscules.

    Returns:
        str: « Paris » pour toutes les gares de Paris. Sinon le nom lisible, sans
        le suffixe de `LABEL_SUFFIXES` s'il y en a un.
    """
    if station.upper().startswith("PARIS"):
        return "Paris"
    name = display_name(station)
    for suffix in LABEL_SUFFIXES:
        if name.endswith(" " + suffix):
            return name[: -len(suffix) - 1]
    return name


def station_points(
    links: pd.DataFrame, stations: pd.DataFrame, min_links_for_label: int = 4
) -> pd.DataFrame:
    """Prépare les gares à dessiner, avec des étiquettes qui ne se chevauchent pas.

    Les gares les plus desservies passent en premier et gardent leur étiquette.

    Args:
        links (pd.DataFrame): Liaisons à tracer.
        stations (pd.DataFrame): Coordonnées des gares.
        min_links_for_label (int): Nombre minimal de liaisons pour avoir une étiquette.

    Returns:
        pd.DataFrame: Une ligne par gare, avec les colonnes `gare`, `nom`, `label`,
        `lon`, `lat` et `liaisons`. Le `label` est vide si la gare n'a pas d'étiquette.
    """
    counts = pd.concat([links["depart"], links["arrivee"]]).value_counts()
    points = stations[stations["gare"].isin(counts.index)].copy()
    points["liaisons"] = points["gare"].map(counts)
    points["lon"], points["lat"] = points["longitude"], points["latitude"]
    points["nom"] = points["gare"].map(display_name)
    points = points.sort_values(["liaisons", "gare"], ascending=[False, True])

    kept: list[tuple[str, float, float]] = []
    labels = {}
    for _, row in points.iterrows():
        name = label_name(row["gare"])
        labels[row["gare"]] = ""
        if row["liaisons"] < min_links_for_label or any(
            name == other for other, _, _ in kept
        ):
            continue
        half_width = LABEL_CHAR_WIDTH * len(name) / 2
        overlaps = any(
            abs(row["lon"] - lon) < half_width + LABEL_CHAR_WIDTH * len(other) / 2
            and abs(row["lat"] - lat) < LABEL_HEIGHT
            for other, lon, lat in kept
        )
        if not overlaps:
            kept.append((name, row["lon"], row["lat"]))
            labels[row["gare"]] = name
    points["label"] = points["gare"].map(labels)
    return points[["gare", "nom", "label", "lon", "lat", "liaisons"]].reset_index(
        drop=True
    )


def summary_metrics(links: pd.DataFrame) -> dict:
    """Compte les liaisons, les plus fiables et les moins fiables.

    Args:
        links (pd.DataFrame): Liaisons à tracer, avec la colonne `tiers`.

    Returns:
        dict: Les clés `liaisons`, `plus_fiables` et `moins_fiables`.
    """
    return {
        "liaisons": len(links),
        "plus_fiables": int((links["tiers"] == TIER_MORE).sum()),
        "moins_fiables": int((links["tiers"] == TIER_LESS).sum()),
    }


def least_reliable(links: pd.DataFrame, count: int = 10) -> pd.DataFrame:
    """Donne les liaisons qui ont les scores les plus bas, sous forme de tableau.

    Args:
        links (pd.DataFrame): Liaisons à tracer.
        count (int): Nombre de liaisons à garder.

    Returns:
        pd.DataFrame: Les colonnes `Liaison`, `Service`, `Score`, `Niveau` et
        `Historique`, triées par score croissant.
    """
    table = links.sort_values("score").head(count)[
        ["titre", "service", "score", "tiers", "mois_txt"]
    ]
    table.columns = ["Liaison", "Service", "Score", "Niveau", "Historique"]
    return table.reset_index(drop=True)


def insurer_reading(tier: str | None) -> tuple[str, str]:
    """Donne le message pour l'assureur, selon le niveau de la liaison.

    Args:
        tier (str | None): Niveau de la liaison. Un niveau inconnu ou `None` donne
            le message « non classé ».

    Returns:
        tuple[str, str]: Le type de message (`success`, `warning`, `error` ou
        `info`) et le texte à afficher.
    """
    return INSURER_READINGS.get(tier, INSURER_READINGS[None])


def disruption_frequency(rate: float) -> str:
    """Dit à quelle fréquence un trajet est perturbé, par exemple « 1 trajet sur 8 ».

    Args:
        rate (float): Taux de perturbation, entre 0 et 1.

    Returns:
        str: Une phrase. Si le taux est nul, aucune perturbation. Si presque tous les
        trajets sont perturbés, une phrase pour ce cas.
    """
    if rate <= 0:
        return "Aucune perturbation observée."
    one_in = round(1 / rate)
    if one_in <= 1:
        return "Presque tous les trajets sont perturbés (annulés ou en retard à l'arrivée)."
    return (
        f"Environ 1 trajet sur {one_in} est perturbé (annulé ou en retard à l'arrivée)."
    )


def pure_premium(rate: float, indemnity: float) -> float:
    """Calcule le coût attendu par trajet : taux de perturbation fois indemnité.

    Args:
        rate (float): Taux de perturbation, entre 0 et 1.
        indemnity (float): Indemnité versée en cas de perturbation.

    Returns:
        float: La prime pure par trajet.
    """
    return rate * indemnity


def link_details(
    scores: pd.DataFrame, departure: str, arrival: str, service: str
) -> tuple[pd.Series | None, pd.Series]:
    """Trouve une liaison et ses causes de retard.

    Args:
        scores (pd.DataFrame): Tableau de fiabilité, une ligne par liaison.
        departure (str): Gare de départ.
        arrival (str): Gare d'arrivée.
        service (str): Service.

    Returns:
        tuple[pd.Series | None, pd.Series]: La ligne de la liaison, ou `None` si elle
        n'existe pas, et ses causes de retard (une série vide si elle est introuvable
        ou sans retard).
    """
    found = scores[
        (scores[COL_DEPARTURE] == departure)
        & (scores[COL_ARRIVAL] == arrival)
        & (scores[COL_SERVICE] == service)
    ]
    if found.empty:
        return None, pd.Series(dtype=float)
    row = found.iloc[0]
    causes = row.reindex(CAUSE_NAMES).dropna().astype(float)
    return row, causes
