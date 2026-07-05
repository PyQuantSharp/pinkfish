# Strategies

Private strategy notebooks and daily signal scripts live here. **Strategy
folders are not committed** — only this README is tracked.

Published examples live under [examples/](../examples/) — **basics**,
**tutorials**, **strategies**, **portfolios**, and **patterns**. See
[examples/README.md](../examples/README.md) for the full curriculum. Copy or
adapt those when starting a new strategy here.

Most strategy folders contain `strategy.ipynb` (backtest), `strategy.py`
(shared logic), and optionally `signals.py` + `run-signals.sh` for end-of-day
signals. See [examples/strategies/double-7s/](../examples/strategies/double-7s/)
for the full pattern.

## Daily signals on a VPS

`run-all-strategies.sh` runs every subfolder that has a `run-signals.sh`.
Use `sync-to-vps.sh` to rsync this directory to a remote machine:

```bash
./sync-to-vps.sh user@your-server
```

## Git

- Tracked: `strategies/README.md`
- Ignored: everything else under `strategies/` (notebooks, Python scripts,
  signal HTML, secrets, and logs)
