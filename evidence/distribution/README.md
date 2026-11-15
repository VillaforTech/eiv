# Frozen evidence distribution

Three large historical JSONL files are stored in this repository as small,
deterministic gzip parts. Restore their exact original bytes locally before
running tests, experiments, replay, or a complete source export:

```sh
python3 scripts/restore_evidence.py
```

The helper uses only Python's standard library. It performs **no network access,
remote API calls, Git commands, credential operations, or external actions**.
It validates every compressed part, the concatenated gzip stream, the restored
size and SHA-256, and the original Git content identifier. Expected hashes must
also agree with `PUBLIC-MANIFEST.json`. All inputs and existing targets are
checked before any missing data file is written. An identical existing file is
preserved; a conflicting file causes failure rather than replacement.

| Materialized path | Bytes | SHA-256 |
| --- | ---: | --- |
| `results/dimensions-v3/raw.jsonl` | 23,221,296 | `31faad7e4086ba6c2c32d73f2bbb199877ba293c98ab2880cb79383feeb2be4b` |
| `benchmark/v3/cases.jsonl` | 6,395,904 | `129fce5ea45f7bea2525457efab18e38a88ab9fd84118bd1e551fc26cd2b2600` |
| `results/engineering-v2/raw.jsonl` | 1,089,023 | `adad3e8f2f40aeb90b1e8c84264ca974c0c6ab856fc8af8b626b0a8942194af2` |

The four compressed parts total 340,253 bytes. `manifest.json` records their
order, exact lengths, compressed checksums and original data checksums. The
restore script also contains fixed expected metadata, preventing an edited
manifest from silently substituting different results.

The original experiment manifests and raw content remain unchanged. Restored
paths are ignored by Git to keep the checkout clean. The public source manifest
describes the **materialized source bundle**, not the bare checkout before
restoration. A complete source ZIP includes both the restored evidence and these
compressed distribution files. Source export never restores files implicitly.

These are synthetic permission cases and recorded research outcomes, not
personal instructions or production activity. Compression does not establish
semantic validity, human review, or safety; it preserves reproducible bytes.
