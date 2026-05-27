# incoming-observatory

**How blind are we, really?** — an open ledger of how much warning humanity *actually* had
before near-Earth objects arrived, plus the **first open-source imminent-impactor alert layer**.

🌏 繁體中文版 → [`README.zh-Hant.md`](README.zh-Hant.md)

---

> Every asteroid we have **ever** detected *before* it hit Earth was found **hours** in advance,
> not days. The longest warning on record (2008 TC3) was about **20 hours**. Most were under 4.
> Chelyabinsk (2013, ~20 m, ~0.5 megatonnes, 1,500 injured) gave us **zero** warning — it came
> from the direction of the Sun, where ground telescopes are blind.
>
> The official agencies know all this. But the one number that matters most —
> **"how long did we see it coming?"** — is *not published in any official table.*
> This project computes it, in the open, and keeps it updated.

## What this is

Three things, all built on **public** data (NASA/JPL CNEOS, the Minor Planet Center, ESA NEOCC):

1. **The warning-time ledger** — for every recorded impactor and close approach, we join the
   *discovery* time (which the official impact tables omit) against the *arrival* time and publish
   the **warning time**. The headline chart: every near-miss, and how little lead we actually had.
   Crucially, we **independently recompute** that number from the *raw MPC discovery observations*
   (earliest observation epoch → impact) rather than trusting an agency press release — and we
   surface any disagreement. All 11 pre-impact asteroids reproduce within ~0.5 h median; the one
   object that doesn't (2024 RW1) is flagged, not hidden.

2. **The blind-spot audit** — we quantify and visualise *why* things slip through: the **sunward**
   blind spot (Chelyabinsk), **long-period comets** (months of warning, not decades), and
   **interstellar objects** (1I/'Oumuamua, 2I/Borisov, and 3I/ATLAS — found 2025-07).

3. **Open imminent-impactor alerts + interstellar triage** — NASA's Scout and ESA's Meerkat do
   real-time impact alerting, but both are **closed-source**. Their *inputs* (the CNEOS Sentry/Scout
   APIs) are public. `incoming alert` is the **first open-source, self-hostable alert layer** on top
   of those feeds — transparent severity logic (Palermo/Torino scales) you can read, run, and extend.
   `incoming triage` flags **hyperbolic / interstellar** objects by eccentricity (and computes v∞):
   it correctly classifies all three confirmed interstellar visitors — 1I/'Oumuamua, 2I/Borisov,
   3I/ATLAS — i.e. "something just arrived from outside the solar system."

## Why this should exist

This is not another orbit propagator or another model — those exist and are excellent
(REBOUND, OrbFit, find_orb, B612's THOR). The gap, confirmed by surveying the field, is the
**verification and transparency layer**: nobody has published an open, continuously-updated
record that answers *"did we actually see it coming, and how blind are the places we can't see?"*

The value here is **not the code** (the orbital math is commodity). It is the **assembled,
provenance-stamped public record** — a thing that has to be *operated and maintained against
live reality*, not generated once. That is deliberately the part an AI cannot fabricate.

## Honesty boundaries (we will not cross these)

This project's credibility *is* the product, so the limits are stated up front:

- We measure **how late we caught the things we did catch**, and we give context on known blind
  spots. We **do not claim to detect the invisible** — you cannot infer undetected objects from a
  catalogue of detected ones.
- We do **not** do end-to-end impact *prediction from scratch* (that needs survey telescopes we
  don't operate). We do warning-time statistics, risk context, and real-time triage on public feeds.
- We make **no** "UFO / alien" claims. Interstellar objects are treated strictly as natural-object
  science. (We may neutrally note that the artificial-origin hypothesis for 'Oumuamua exists and
  is scientifically contested — that is a citation, not an endorsement.)
- Upstream APIs change; ESA NEOCC's is explicitly *experimental*. We **cache and pin** every
  snapshot and record its hash in a provenance manifest, so any number we publish is reproducible.

## Quickstart

```bash
pip install -e .

# Build the warning-time ledger from the bundled, sourced seed dataset (no network needed):
incoming ledger

# Print the headline summary + write outputs/warning_times.parquet + a plot:
incoming ledger --plot

# Independently recompute warning time from RAW MPC observations (offline, uses snapshot):
incoming recompute

# Refresh the recompute live from the Minor Planet Center (updates data/mpc_first_obs.json):
incoming recompute --live

# Flag hyperbolic / interstellar objects (default: the 3 confirmed ones; offline via snapshot):
incoming triage
incoming triage --live "C/2025 N1"      # classify any object from JPL SBDB

# Open impact-risk alerts aggregated from NASA's public Sentry feed:
incoming alert --live
```

> **What "warning time" means here** — we define it as *first-ever observation → impact*, computed
> from the earliest MPC observation epoch. Agencies sometimes quote *alert-issued → impact* instead
> (the moment an object was recognised as an impactor, which can be later than first sighting). That
> definitional gap is exactly why a recompute can legitimately differ — e.g. 2024 RW1 shows ~10.9 h
> from first observation vs a reported ~8 h. We compute the cleanly-defined quantity and flag the gap.

Each run writes a `provenance.json` recording which data snapshot and code commit produced the
numbers — the same "result → source" contract idea this project is built to defend.

### Web preview (Earth · Solar System · Galaxy)

`incoming ledger` also publishes `web/data/ledger.json`, which drives a 3D viewer (Three.js):

```bash
cd web && python -m http.server 8000   # then open http://localhost:8000
```

Three toggleable views, all driven by the real ledger: the **Earth** globe with every pre-impact
detection drawn as an incoming streak coloured by warning time (and the sunward blind-spot cone);
the **Solar System** with a schematic interstellar/hyperbolic trajectory; and a zoomed-out
**Galaxy** view showing where interstellar visitors arrive from. It is a presentation layer over
real data — it does not render anything we haven't measured.

## Data sources & attribution

| Source | Used for | Access |
| --- | --- | --- |
| **NASA/JPL CNEOS** (CAD, Sentry, Scout, SBDB) | close approaches, impact risk, imminent objects | public JSON API, no key |
| **IAU Minor Planet Center** | discovery observations (→ warning time), NEOCP firehose | public bulk + API |
| **ESA NEOCC** | risk list, past impactors, cross-check | public (experimental) API |

Data belongs to those organisations under their own public-use/attribution terms. Code is Apache-2.0.

## Status

Early. Phase 0 (skeleton + this README) and the Phase 1 core (warning-time ledger over a sourced
seed set of every asteroid detected before impact) are in place. Live MPC discovery-time recompute,
the blind-spot dashboard, and the open alert layer are next — see [the plan](#roadmap).

## Roadmap

- [x] Recompute warning time independently from raw MPC discovery observations (verify the agencies)
- [x] **Open imminent-impactor alert** aggregated from CNEOS Sentry (`incoming alert`)
- [x] Hyperbolic / interstellar candidate triage with v∞ (`incoming triage`)
- [ ] Blind-spot dashboard (sunward / long-period comet / interstellar)
- [ ] Live NEOCP firehose screening (auto-run triage on unconfirmed objects)
- [ ] Signed, reproducible data releases
