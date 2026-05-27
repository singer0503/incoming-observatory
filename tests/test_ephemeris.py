"""Validate Kepler propagation against known physics."""
import math

from incoming import ephemeris as eph


def _r(xyz):
    return math.sqrt(sum(c * c for c in xyz))


def test_elliptic_solver_satisfies_kepler():
    for M in (0.1, 1.0, 3.0, -2.0):
        for e in (0.0, 0.2, 0.7, 0.95):
            E = eph._solve_elliptic(M, e)
            resid = (E - e * math.sin(E)) - ((M + math.pi) % (2 * math.pi) - math.pi)
            assert abs(resid) < 1e-9


def test_hyperbolic_solver_satisfies_kepler():
    for M in (0.5, 5.0, 50.0):
        for e in (1.2, 3.4, 6.1):
            H = eph._solve_hyperbolic(M, e)
            assert abs((e * math.sinh(H) - H) - M) < 1e-7


def test_earth_is_about_one_au():
    r = _r(eph.planet_xyz("Earth", eph.J2000))
    assert 0.98 <= r <= 1.02


def test_mars_distance_in_range():
    r = _r(eph.planet_xyz("Mars", eph.J2000))
    assert 1.38 <= r <= 1.67  # Mars perihelion ~1.38, aphelion ~1.67 au


def test_all_eight_planets_within_expected_distance():
    expect = {"Mercury": (0.30, 0.47), "Venus": (0.71, 0.74), "Earth": (0.98, 1.02),
              "Mars": (1.38, 1.67), "Jupiter": (4.9, 5.5), "Saturn": (9.0, 10.1),
              "Uranus": (18.2, 20.1), "Neptune": (29.7, 30.4)}
    for name, (lo, hi) in expect.items():
        r = _r(eph.planet_xyz(name, eph.J2000))
        assert lo <= r <= hi, f"{name} at {r:.2f} au out of [{lo}, {hi}]"


def test_bennu_within_perihelion_aphelion():
    # SBDB elements for 101955 Bennu (a=1.13, e=0.204).
    b = {"a": 1.13, "e": 0.204, "i": 6.03, "om": 2.06, "w": 66.2, "ma": 102,
         "n": 0.824, "epoch": 2455562.5}
    q, Q = 1.13 * (1 - 0.204), 1.13 * (1 + 0.204)
    for jd in (2455562.5, 2455562.5 + 100, 2455562.5 + 300):
        r = _r(eph.state_xyz(jd=jd, **b))
        assert q - 0.02 <= r <= Q + 0.02


def test_interstellar_hyperbolic_position_is_finite_and_outbound():
    # 3I/ATLAS-like hyperbolic elements (a<0, e>1); near perihelion r ~ q.
    iso = {"a": -0.264, "e": 6.14, "i": 175, "om": 322, "w": 128, "ma": 818,
           "n": 7.27, "epoch": 2461090.5}
    r_peri = _r(eph.state_xyz(jd=2460977.995, **iso))  # at perihelion time tp
    assert 1.0 <= r_peri <= 1.8  # q ≈ 1.36 au
    r_later = _r(eph.state_xyz(jd=2460977.995 + 200, **iso))
    assert r_later > r_peri  # leaving the solar system
