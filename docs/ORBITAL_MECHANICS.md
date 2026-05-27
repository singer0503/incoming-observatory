# Orbital mechanics, plainly — how we turn elements into 3D positions

This explains the math behind `src/incoming/ephemeris.py` (the tested reference) and its
mirror in `web/index.html` (so the map animates on real orbits). Goal: you should be able
to read the code and know *why* each line is there.

> **One-sentence version:** every orbit is described by 6 numbers ("orbital elements");
> to find where an object is at a given time, we advance one of those numbers, solve one
> equation (Kepler's), and rotate the result into 3D.

---

## 1. The six orbital elements

An orbit around the Sun is fully described by six numbers. JPL's SBDB gives us all of them.

| Symbol | Name | Plain meaning |
| --- | --- | --- |
| **a** | semi-major axis | the orbit's size (au). For a hyperbolic, unbound orbit, `a` is **negative**. |
| **e** | eccentricity | how stretched it is. `0` = circle, `<1` = ellipse (bound), `>1` = hyperbola (escapes — interstellar). |
| **i** | inclination | how tilted the orbit plane is vs. Earth's (degrees). |
| **Ω** (`om`) | longitude of ascending node | where the orbit crosses the reference plane going "up". |
| **ω** (`w`) | argument of perihelion | how the ellipse is rotated within its own plane. |
| **M** (`ma`) | mean anomaly | *where the object is along the orbit*, as an angle, at a reference time (`epoch`). |

Plus `epoch` (the reference time, a Julian Date) and `n` (mean motion, degrees/day — how
fast `M` grows). `i, Ω, ω` set the orbit's orientation in space; `a, e` set its shape;
`M` (with `epoch, n`) sets the timing.

---

## 2. Step 1 — advance the object in time

The mean anomaly grows linearly with time. To get `M` at any Julian Date `jd`:

```
M(jd) = M₀ + n · (jd − epoch)      # degrees, then convert to radians
```

`M` is a *fictitious* uniform angle — it is **not** the real angle to the object (orbits
speed up near the Sun). It's just a clean clock. The next step converts it to a real angle.

---

## 3. Step 2 — Kepler's equation (the one hard part)

To get the real position we need the **eccentric anomaly** `E` (for ellipses) from `M`.
They're related by **Kepler's equation**:

```
M = E − e · sin(E)            (elliptical, e < 1)
```

This can't be solved with algebra — you solve it numerically. We use **Newton's method**
(`_solve_elliptic`): guess `E`, repeatedly correct it until it stops moving:

```
E ← E − (E − e·sin E − M) / (1 − e·cos E)
```

A handful of iterations converges to machine precision.

For **hyperbolic** orbits (interstellar visitors, `e > 1`) the equivalent uses the
hyperbolic functions (`_solve_hyperbolic`):

```
M = e · sinh(H) − H           (hyperbolic, e > 1)
```

solved the same Newton way for the hyperbolic anomaly `H`.

---

## 4. Step 3 — position in the orbit's own plane (perifocal)

With `E` (or `H`) we can place the object in 2D, in the plane of its own orbit, with the
Sun at a focus and perihelion along the +x axis (`_perifocal`):

```
ellipse:    x' = a(cos E − e)            y' = a·√(1−e²)·sin E
hyperbola:  x' = a(cosh H − e)           y' = −a·√(e²−1)·sinh H
```

(The hyperbolic forms give a positive distance because `a` is negative — see the test
`test_interstellar_hyperbolic_position_is_finite_and_outbound`.)

---

## 5. Step 4 — rotate into 3D (ecliptic coordinates)

The 2D perifocal point is rotated into real 3D space by three angles — `ω` (within the
plane), `i` (tilt), `Ω` (swivel) — a standard 3-rotation (`state_xyz`):

```
x = x'(cosΩ cosω − sinΩ sinω cos i) − y'(cosΩ sinω + sinΩ cosω cos i)
y = x'(sinΩ cosω + cosΩ sinω cos i) − y'(sinΩ sinω − cosΩ cosω cos i)
z = x'(sinω sin i) + y'(cosω sin i)
```

The result `(x, y, z)` is **heliocentric J2000 ecliptic, in au** — exactly what the map
plots (with the ecliptic plane laid flat: scene-Y = ecliptic-Z).

---

## 6. Planets

Planets use the standard **Standish J2000 mean elements + per-century rates** (hard-coded
in `ephemeris._PLANETS`), valid ~1800–2050. We evaluate the elements at `jd`, derive `ω`
and `M`, and run the exact same Steps 3–5. So Earth lands at ~1.00 au (test
`test_earth_is_about_one_au`) and Mars stays between ~1.38 and ~1.67 au.

---

## 7. Honest limitations

- This is a **two-body** model (Sun + object). We ignore planetary perturbations,
  non-gravitational forces (comet outgassing), and relativity. That is **fine for a
  situational map** but is **not** a precision ephemeris — don't navigate a spacecraft
  with it. For sub-arcsecond accuracy you'd use JPL Horizons / SPICE.
- NEOCP objects have arcs of *hours*, so their elements are too uncertain to propagate
  honestly — the map deliberately shows them near Earth as "uncertain", not on a fake orbit.
- On-screen distances are scaled (`SCALE` units per au) for viewing; the *physics* is real.

---

## 8. Where it lives in the code

| Piece | File / function |
| --- | --- |
| Kepler solvers | `ephemeris._solve_elliptic`, `ephemeris._solve_hyperbolic` |
| Perifocal + rotation | `ephemeris._perifocal`, `ephemeris.state_xyz` |
| Planet elements | `ephemeris._PLANETS`, `ephemeris.planet_xyz` |
| Element fetch + export | `orbits.py` → `web/data/orbits.json` |
| Frontend mirror (animation) | `web/index.html` → `solveElliptic`, `solveHyper`, `posOf`, `pathPoints` |
| Tests | `tests/test_ephemeris.py`, `tests/test_orbits.py` |

Run the checks: `pytest tests/test_ephemeris.py tests/test_orbits.py -q`.
