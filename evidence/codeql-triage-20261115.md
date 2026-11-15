# CodeQL contextual triage — EIV

Recorded 2026-11-15T19:18:47.203955+00:00. Read-only source review; no alerts dismissed and no repository source changed.

## Result

The [initial CodeQL setup run](https://github.com/VillaforTech/eiv/actions/runs/43751384263) succeeded for Python, JavaScript/TypeScript and Actions. Python produced **123 open `py/path-injection` alerts**, all with tool severity **high**. JavaScript/TypeScript and Actions analyses reported zero results. Enabling scanning is verified; this is not a clean-security-scan claim.

All 123 Python findings have reported dataflow roots in local command-line `argparse.parse_args()` calls. Every one of the 242 SARIF thread flows was checked programmatically against the corresponding source line; there are 17 unique CLI source locations. The paths are operator-selected input files, output locations, or packaging/release request files. **No remotely supplied HTTP path reaches these reported filesystem sinks in the inspected implementation.** This assessment concerns the recorded dataflows and their call sites, not a security guarantee for EIV.

The scan analyzes commit `7516fd5c6ba9f6b9c0e01cddd91ac35a4cf909dd`, Python analysis ID `2171973986`, with the `default` query suite and `remote_and_local` threat model. The local threat model intentionally treats CLI arguments as sources.

## Source groups

| Group | Open alerts | Boundary |
|---|---:|---|
| Current tooling | 84 | Local operator chooses experiment/data/export/package/release paths |
| Archived historical sources and saved source snapshots | 39 | Frozen replay evidence; preserve source bytes and hashes |

### Current tooling

- `eiv_experiment/dimensions.py` (14), `selection_audit.py` (9), `planner.py` (6): caller selects local data/output paths; generated artifact names are constants. The current planner and audit refuse an existing output directory. They are CLI research tools, not HTTP request handlers.
- `eiv_experiment/replay.py` (2): `export_requests` writes the local CLI `--export-model-requests` destination passed by `eiv_experiment/run.py`. A caller should use a fresh intended destination; the export function can overwrite a caller-selected existing file. No remote consumer calls it.
- `eiv_llm/analyze.py` (3), `eiv_llm/__main__.py` (1): saved raw/case/manifest files are read from operator-selected CLI paths for local analysis or optional local-model pilot generation. Paths are not taken from model output. The maintained simulator/workbench does not call this pilot.
- `scripts/export_public.py` (18), `package_release.py` (19): local `--output`/`--zip` selections lead to filesystem operations by design. Export enumerates fixed allowlists, rejects symlinked selected files, checks selected content, and stages a complete tree before rename. Package creation uses an atomic temporary archive and preserves an older archive by digest. These utilities are not sandboxes for untrusted users.
- `scripts/release_github.py` (5): the CLI selects the request JSON path. Its content is small/regular/non-symlink JSON containing only a numeric version; constructed release-note paths cannot contain traversal from the version. Publication additionally requires the intended repository, a default-branch push workflow, exact commit and release/tag checks. No HTTP payload chooses this local request path.
- `scripts/replay_frozen.py` (7): CLI selects output. Archived manifest paths pass `safe_relative` (absolute paths, `..`, backslashes rejected), payload hashes are verified, and replay executes in a temporary source stage. The manifest is tracked checkout evidence, not an untrusted remote upload.

### Historical sources

Frozen/source-snapshot findings total 39: `evidence/frozen-v0.3/eiv_experiment/dimensions.py` 14; `selection_audit.py` 9; `replay.py` 2; `evidence/frozen-v0.3/eiv_llm/analyze.py` 3; `__main__.py` 1; `results/selection-audit-final-20261023/audit-source.py` 9; `results/llm-pilot-v2-source/driver.py` 1. Their reported sources are CLI arguments. Changing these files to satisfy scanner patterns would alter preserved experimental evidence. No historical source was edited.

## HTTP boundary inspected

`eiv/web.py` binds to `127.0.0.1`, validates Host/Origin, and dispatches exact GET paths. Its three package-file reads use literal paths: `assets/workbench.html`, `assets/dimension-example.json`, `assets/selection-example.json`. Request paths are compared to constants and are never joined to filesystem paths. Unknown routes return 404.

POST routes `/api/analyze`, `/api/structured` and `/api/step` validate bounded JSON then invoke permission/session functions. `eiv/permissions.py`, `eiv/logic.py` and `eiv/planning.py` do not import filesystem APIs or perform file I/O. Resource identifiers in simulated requests remain data. No route invokes `eiv_experiment`, `eiv_llm`, export, package, or release tooling.

## Disposition and limits

The 123 alerts remain open with contextual review recorded here. Their scanner severity is preserved. No immediate remotely exploitable traversal was identified among them, and no source change is justified solely to reject deliberate local CLI path selection. This is a maintainer-side triage assessment, not independent security certification or proof that every local race/symlink misuse is impossible.

Do not expose these CLI utilities as a network service or privileged multi-user worker without a separate root-containment and authorization design. Local output paths can modify files selected by the same operator and may have ordinary shared-directory race considerations. This report does not dismiss alerts, change the threat model, suppress queries, edit archives, or establish production authorization security.

## Optional security-setting limitation

The repository API reports owner type `User`, public visibility, secret scanning and push protection enabled; generic/non-provider patterns remain disabled after the attempted setting change. Current [GitHub eligibility documentation](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enabling-secret-scanning-for-generic-patterns) limits that feature to organization-owned repositories on GitHub Team with GitHub Secret Protection enabled. EIV does not meet that documented repository type. Activation must therefore not be claimed from HTTP 200 alone. No paid service or additional authentication scope was requested.

## Evidence

- [Sanitized counts and source grouping](codeql-triage-summary-20261115.json).
- [GitHub CodeQL alerts](https://github.com/VillaforTech/eiv/security/code-scanning).
- [Initial successful setup run](https://github.com/VillaforTech/eiv/actions/runs/43751384263).

The inspection used the Python SARIF analysis and a paginated alert snapshot.
Raw local review exports are not required to run EIV and are not release assets.
