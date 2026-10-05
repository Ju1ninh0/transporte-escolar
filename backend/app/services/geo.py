from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_M = 6_371_000


def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros entre dois pontos (fórmula de haversine)."""
    p1, p2 = radians(lat1), radians(lat2)
    dp = p2 - p1
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_M * asin(sqrt(a))