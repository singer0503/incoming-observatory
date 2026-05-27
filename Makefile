.PHONY: install test lint ledger recompute triage alert screen blindspots refresh all web clean

install:          ## install package + dev/astro extras
	pip install -e ".[dev,astro]"

test:             ## run the offline test suite
	pytest -q

lint:
	ruff check src tests

ledger:           ## build the warning-time ledger (offline) + plot
	incoming ledger --plot

recompute:        ## independent recompute from the committed MPC snapshot (offline)
	incoming recompute

triage:           ## flag hyperbolic/interstellar objects from the snapshot (offline)
	incoming triage

alert:            ## open impact-risk alerts from cached Sentry feed
	incoming alert

screen:           ## screen the NEOCP firehose from the cached Scout feed
	incoming screen

blindspots:       ## assemble the blind-spot dashboard data (web/blindspots.html)
	incoming blindspots

refresh:          ## hit the live public APIs and refresh all snapshots
	incoming recompute --live
	incoming triage --live
	incoming alert --live
	incoming screen --live

all: ledger recompute triage alert screen blindspots  ## regenerate every output offline

web: all          ## regenerate data then serve the 3D preview
	cd web && python -m http.server 8000

clean:
	rm -rf outputs cache *.egg-info
