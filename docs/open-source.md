# Open-source project setup

The public project is EIV: Interactive Verifiable Specification. Its focus is an
inspectable formal decision layer for proposed agent actions, with reproducible
experiments and explicit semantic assumptions.

## Verified publication status

The canonical repository is [VillaforTech/eiv](https://github.com/VillaforTech/eiv),
verified **public** on 2026-11-15. The initial default branch is `master`; the
workflow validates pushes and pull requests on any branch. Public source history
starts independently with the MIT license and the reviewed source export.

The [v0.4.0 release](https://github.com/VillaforTech/eiv/releases/tag/v0.4.0)
was published on 2026-11-15 from verified commit
`3b805d9caa157f11e668381c9cfaea2e595f88f5`. Its source ZIP and SHA-256 checksum
are attached. The [publication receipt](../evidence/publication.json) records
the tag, successful release workflow, asset digests and observed settings.
The release request file was removed after publication.

Repository files configure CI, contribution/security policies, Dependabot,
ownership, citation metadata and the issue/PR templates. Issues are enabled.
Administrative settings were applied with the maintainer's GitHub CLI login and
independently read back on 2026-11-15. The [configuration receipt](../evidence/github-configuration-20261115.json)
records the observed controls and limitations. The personal website integration
remains a draft; no production page at `/es/projects/eiv/` has been published.

## Distribution contract

Publish a fresh source history from the allowlisted export. The public artifact
contains the runtime, tests, frozen research evidence, documentation, website
draft and community files. A previous working repository's history is not part
of that export. Creating a ZIP or adding an MIT license does not by itself make
a repository publicly accessible.

## Repository configuration

| Setting | Intended configuration | Implementation/status |
|---|---|---|
| Name | `eiv` under the maintainer's account | Verified: `https://github.com/VillaforTech/eiv` |
| Visibility | Public | Verified public on 2026-11-15 |
| Description | Formal models and traceable permission decisions for AI agents: bounded verification, clarification, and reproducible research. | Applied and independently verified |
| License | MIT | `LICENSE` |
| Citation | Software version and academic bibliography | `CITATION.cff`, `research/references.bib` |
| Documentation | README, architecture, action model, API, research and reproducibility | Included |
| Community | Contribution guide, conduct, governance, ownership, issue/PR templates | Included |
| CI | Python 3.10–3.14, full replay, package installation, portfolio checks | Versioned workflow; verify each release's run |
| Dependencies | Monthly review of GitHub Actions and build dependencies | Dependabot configuration included |
| Discussions and issues | Enabled | Both independently verified enabled |
| Wiki and project boards | Disabled | Wiki showed “Create the first page”; Projects showed zero open/closed projects before disabling. Readback confirms both disabled |
| Merging | Squash available, delete merged topic branches | Both independently verified enabled; existing merge/rebase methods preserved |
| Default branch | `master`: no force pushes or deletion; resolved conversations; strict required CI; administrators included | Seven existing checks required; PR required with **zero** approving reviews and no code-owner/last-push approval |
| Security reports | Private reporting, dependency alerts and automated security fixes | Independently verified enabled; use [private reporting](https://github.com/VillaforTech/eiv/security/advisories/new) |
| Secret protection | Secret scanning and push protection | Both independently verified enabled; optional non-provider patterns remained disabled after request |
| Code scanning | CodeQL default setup, free for the public repository | See the receipt for the setup run and final observed analysis state |
| Website / About URL | `https://www.villafortech.com/` | Verified HTTP 200 after canonical redirect. The EIV case study remains a draft, outside the production content collection |

Suggested topics: `ai-agents`, `formal-methods`, `ai-safety`, `authorization`,
`explainability`, `python`, `reproducible-research`, `human-in-the-loop`.

The required contexts are `test (3.10)`, `test (3.11)`, `test (3.12)`,
`test (3.13)`, `test (3.14)`, `replay` and `portfolio`, bound to the observed
GitHub Actions app. `release` publishes only on default-branch pushes and is not
a required PR validation check. This policy permits one maintainer to submit and
merge a passing PR without another reviewer. It does not bypass checks for admins.

The existing Dependabot PRs are preserved. The source publication helper now
preserves Wiki, Projects and other merge methods when retrying configuration;
disabling an unused feature requires a separate occupancy check. It also reads
settings back separately after writes. These administrative changes do not alter
the v0.4.0 tag, release or source asset.

## Publishing

After a Git clone, first run `python3 scripts/restore_evidence.py` before tests,
scientific replay or source packaging. The public export manifest describes the
materialized source tree; compressed delivery does not change historical hashes.

The included publication helper defaults to a read-only plan. Initial-publication
apply mode uses an authenticated GitHub CLI, a fresh source export and a new Git history.
**EIV is already published: use only `--configure-only` for configuration retries.**
It must refuse an existing private repository or a populated destination for
initial publication. Configuration retries are a separate operation from pushing
source. Read the helper's `--help` output before applying it.

```sh
python3 scripts/publish_github.py --help
python3 scripts/publish_github.py --repository VillaforTech/eiv --plan --configure-only

# After CI on the default branch succeeds, finish protection without pushing again.
python3 scripts/publish_github.py --repository VillaforTech/eiv --apply --configure-only
```

The helper does not expose tokens, force-push, publish the website or execute
simulated permissions. Its receipt must distinguish completed operations,
optional feature failures and branch protection deferred until CI exists.

## Versioned release automation

The workflow creates a release only after the Python matrix, replay and portfolio
checks succeed on a default-branch push with an explicit `.github/release-request.json`
file containing the version. The release job receives content-writing permission
only to create the tag/release and upload its ZIP and checksum; checkout credentials
are not persisted and no workflow pushes source changes to the default branch.
The script binds the release to the exact checked commit and never replaces an
existing tag or asset. Remove the request file after the release is confirmed.

## First contribution themes

The [formal action model](formal-action-model.md) specifies acceptance criteria
for four initial research/engineering issues:

1. Versioned operation and trace contracts.
2. A dry-run conversational adapter.
3. An execution gate tested against a fake tool.
4. Independent semantic review and prospective evaluation.

These are proposals, not implemented claims. Add `good first issue` only after
a task has a small scope, reproduction steps and maintainer support. Open-source
access invites independent inspection; it does not imply a peer-reviewed paper,
community adoption or outside endorsement.
