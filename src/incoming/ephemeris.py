"""Real Kepler propagation — turn orbital elements into 3D positions.

Replaces the map's schematic placement with genuine heliocentric ecliptic positions
computed from orbital elements: planets from the standard J2000 mean elements (Standish),
small bodies and interstellar objects from JPL SBDB elements. Handles both elliptical
(e < 1) and hyperbolic (e > 1) orbits.

Coordinates are heliocentric, J2000 ecliptic, in astronomical units (au). The same math
is mirrored in the web frontend so the map animates on real orbits; this module is the
tested reference and the static exporter.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

J2000 = 2451545.0


def jd_now() -> float:
    return 2440587.5 + datetime.now(timezone.utc).timestamp() / 86400.0


def _solve_elliptic(M: float, e: float) -> float:
    """Eccentric anomaly E from mean anomaly M (rad), Newton iteration."""
    M = (M + math.pi) % (2 * math.pi) - math.pi
    E = M if e < 0.8 else math.pi
    for _ in range(60):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-12:
            break
    return E


def _solve_hyperbolic(M: float, e: float) -> float:
    """Hyperbolic anomaly H from mean anomaly M (rad): M = e*sinh(H) - H."""
    H = math.asinh(M / e) if M != 0 else 0.0
    for _ in range(100):
        f = e * math.sinh(H) - H - M
        H -= f / (e * math.cosh(H) - 1)
        if abs(f) < 1e-11:
            break
    return H


def _perifocal(a: float, e: float, M: float) -> tuple[float, float]:
    """Perifocal (x', y') in au, periapsis on +x'. a in au, M in radians."""
    if e < 1.0:
        E = _solve_elliptic(M, e)
        return a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    H = _solve_hyperbolic(M, e)
    return a * (math.cosh(H) - e), -a * math.sqrt(e * e - 1) * math.sinh(H)


def state_xyz(*, a: float, e: float, i: float, om: float, w: float,
              ma: float, n: float, epoch: float, jd: float) -> tuple[float, float, float]:
    """Heliocentric ecliptic (x, y, z) in au at time jd.

    Angles i, om(Ω), w(ω), ma(M) in degrees; n in deg/day; a in au; epoch, jd in JD.
    """
    M = math.radians(ma + n * (jd - epoch))
    xp, yp = _perifocal(a, e, M)
    i, om, w = math.radians(i), math.radians(om), math.radians(w)
    cw, sw = math.cos(w), math.sin(w)
    co, so = math.cos(om), math.sin(om)
    ci, si = math.cos(i), math.sin(i)
    x = xp * (co * cw - so * sw * ci) - yp * (co * sw + so * cw * ci)
    y = xp * (so * cw + co * sw * ci) - yp * (so * sw - co * cw * ci)
    z = xp * (sw * si) + yp * (cw * si)
    return x, y, z


# Standard J2000 mean orbital elements + per-century rates (Standish, valid ~1800-2050).
# columns: a(au), e, i(deg), L mean-longitude(deg), long.peri ϖ(deg), Ω(deg)  and their /century rates
_PLANETS = {
    "Mercury": ([0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593],
                [0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081]),
    "Venus":   ([0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255],
                [0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418]),
    "Earth":   ([1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0],
                [0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0]),
    "Mars":    ([1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891],
                [0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343]),
    "Jupiter": ([5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909],
                [-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106]),
    "Saturn":  ([9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448],
                [-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794]),
    "Uranus":  ([19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503],
                [-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589]),
    "Neptune": ([30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574],
                [0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664]),
}


def planet_xyz(name: str, jd: float) -> tuple[float, float, float]:
    base, rate = _PLANETS[name]
    T = (jd - J2000) / 36525.0
    a, e, i, L, peri, Om = (base[k] + rate[k] * T for k in range(6))
    w = peri - Om                      # argument of perihelion
    ma = (L - peri + 180) % 360 - 180  # mean anomaly, wrapped to [-180, 180]
    n = 0.0  # ma already at jd via L(T); propagate with n=0 from this epoch
    return state_xyz(a=a, e=e, i=i, om=Om, w=w, ma=ma, n=n, epoch=jd, jd=jd)


def elements_to_dict(els: dict, epoch: float) -> dict | None:
    """Coerce SBDB element strings to the float dict state_xyz expects."""
    try:
        return {
            "a": float(els["a"]), "e": float(els["e"]), "i": float(els["i"]),
            "om": float(els["om"]), "w": float(els["w"]), "ma": float(els["ma"]),
            "n": float(els["n"]), "epoch": float(epoch),
        }
    except (KeyError, TypeError, ValueError):
        return None
