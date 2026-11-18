"""Data for the reliability map. No Streamlit in here."""

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

BEND = 0.08  # how much the curve bends
CURVE_POINTS = 24
# this variable help us to define gap between the two directions
OFFSET_DEGREES = 0.05
# the gap shrinks near the stations
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
LABEL_CHAR_WIDTH = 0.35  # width of a character
LABEL_HEIGHT = 0.5  # height of a label

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
    """Make an upper-case station name readable."""
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
    """Build a curved line between two points.

    Args:
        side: 1 bends to the left, -1 to the right.
        bend: how far the middle moves, as a share of the distance.
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
    """Key of a pair of stations, the same in both directions."""
    first, second = sorted([station_a, station_b])
    return f"{first}|{second}"


def offset_path(
    path: list[list[float]], distance: float = OFFSET_DEGREES
) -> list[list[float]]:
    """Shift a path to the right, so both directions of a track do not overlap."""
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
    """Build the lines to draw, one per liaison.

    Args:
        mode: keep every liaison, or only the worst direction of each pair.
        routes: paths along the rail network, by route key. Without one, a curve is drawn.

    Returns:
        The liaisons (worst last, so they are drawn on top) and how many had no coordinates.
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
    """Stations for the filter, the Paris group first."""
    names = sorted(set(links["depart"]) | set(links["arrivee"]))
    return [PARIS_GROUP] + names


def filter_links(
    links: pd.DataFrame,
    services: list[str],
    tiers: list[str],
    station: str | None = None,
    score_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Keep the liaisons that match the filters.

    Args:
        station: a station, or PARIS_GROUP for all Paris stations.
        score_range: lowest and highest score to keep.
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
    """Short name of a station for its map label."""
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
    """Stations to draw, with labels that do not overlap.

    The busiest stations get their label first.
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
    """Count the liaisons, and the best and worst ones."""
    return {
        "liaisons": len(links),
        "plus_fiables": int((links["tiers"] == TIER_MORE).sum()),
        "moins_fiables": int((links["tiers"] == TIER_LESS).sum()),
    }


def least_reliable(links: pd.DataFrame, count: int = 10) -> pd.DataFrame:
    """The liaisons with the lowest scores, as a table."""
    table = links.sort_values("score").head(count)[
        ["titre", "service", "score", "tiers", "mois_txt"]
    ]
    table.columns = ["Liaison", "Service", "Score", "Niveau", "Historique"]
    return table.reset_index(drop=True)


def insurer_reading(tier: str | None) -> tuple[str, str]:
    """Message for the insurer, depending on the tier."""
    return INSURER_READINGS.get(tier, INSURER_READINGS[None])


def disruption_frequency(rate: float) -> str:
    """Say how often a trip is disrupted, like "1 trip in 8"."""
    if rate <= 0:
        return "Aucune perturbation observée."
    one_in = round(1 / rate)
    if one_in <= 1:
        return "Presque tous les trajets sont perturbés (annulés ou en retard à l'arrivée)."
    return (
        f"Environ 1 trajet sur {one_in} est perturbé (annulé ou en retard à l'arrivée)."
    )


def pure_premium(rate: float, indemnity: float) -> float:
    """Expected cost per trip: disruption rate times indemnity."""
    return rate * indemnity


def link_details(
    scores: pd.DataFrame, departure: str, arrival: str, service: str
) -> tuple[pd.Series | None, pd.Series]:
    """Find a liaison and its causes of delay. The row is None if not found."""
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
