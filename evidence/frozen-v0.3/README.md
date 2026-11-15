# Frozen v0.3 research source

This directory preserves the pre-release source used by the historical engineering
studies. `manifest.json` binds 25 source files and 43 original evidence files by
SHA-256. The original v1, v2 and v3 experiment manifests remain unchanged.

The current implementation has received input validation and server hardening.
Its source hashes are intentionally different. Historical results are reproduced
in a temporary isolated workspace using these archived files, with the saved
benchmark and result files copied only after hash verification. This avoids
silently relabeling a changed implementation as the original frozen experiment.

```sh
python3 scripts/replay_frozen.py --output build/historical-replay
python3 scripts/reproduce.py --output build/full-verification
```

Both commands are offline and dependency-free. They never invoke model inference
or execute a simulated permission action. The first reproduces historical results;
the second also runs the current test suite. Use a fresh output path each time.
Original v2 timings are compared after excluding machine-dependent latency. V3
outcomes, summary and analysis, and the independent selection audit are compared
byte for byte. The saved model pilot is validated and reanalyzed without inference.

This is reproducibility evidence, not independent empirical validation. Hashes
establish internal consistency, not author authenticity or general safety. The
archived modules intentionally retain historical behavior and should not be used
as a network service. Human interpretation coverage remains unverified.
