# Open-source project setup

The public project is EIV: Interactive Verifiable Specification. Its focus is an
inspectable formal decision layer for proposed agent actions, with reproducible
experiments and explicit semantic assumptions.

## Verified publication status

The canonical repository is [VillaforTech/eiv](https://github.com/VillaforTech/eiv),
verified **public** on 2026-11-15. The initial default branch is `master`; the
workflow validates pushes and pull requests on any branch. Public source history
starts independently with the MIT license and the reviewed source export.

Repository files configure CI, contribution/security policies, Dependabot,
ownership, citation metadata and the issue/PR templates. Issues are enabled.
The About description/topics, branch protection and security settings still
require administrative configuration and readback; their desired values below
are not claims that those controls are already active. The website remains a draft.

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
| Description | Formal models and traceable permission decisions for AI agents: bounded verification, clarification, and reproducible research. | Publication configuration |
| License | MIT | `LICENSE` |
| Citation | Software version and academic bibliography | `CITATION.cff`, `research/references.bib` |
| Documentation | README, architecture, action model, API, research and reproducibility | Included |
| Community | Contribution guide, conduct, governance, ownership, issue/PR templates | Included |
| CI | Python 3.10–3.14, full replay, package installation, portfolio checks | Versioned workflow; verify each release's run |
| Dependencies | Monthly review of GitHub Actions and build dependencies | Dependabot configuration included |
| Discussions and issues | Enabled | Publication configuration; not assumed from source files |
| Wiki and project boards | Disabled initially | Keep documentation and a small issue roadmap in one place |
| Merging | Squash available, delete merged topic branches | Publication configuration |
| Default branch | No forced updates or deletion; resolved discussions; observed CI required | Apply after the initial CI has run |
| Security reports | Private reporting and dependency alerts when available | Verify API results; do not infer activation from `SECURITY.md` |
| Website | Draft under `/projects/eiv` | No production website deployment is implied |

Suggested topics: `ai-agents`, `formal-methods`, `ai-safety`, `authorization`,
`explainability`, `python`, `reproducible-research`, `human-in-the-loop`.

## Publishing

After a Git clone, first run `python3 scripts/restore_evidence.py` before tests,
scientific replay or source packaging. The public export manifest describes the
materialized source tree; compressed delivery does not change historical hashes.

The included publication helper defaults to a read-only plan. Its apply mode
uses an authenticated GitHub CLI, a fresh source export and a new Git history.
It must refuse an existing private repository or a populated destination for
initial publication. Configuration retries are a separate operation from pushing
source. Read the helper's `--help` output before applying it.

```sh
python3 scripts/publish_github.py --repository VillaforTech/eiv --plan

# Create a fresh source export, then publish it with your GitHub CLI login.
python3 scripts/restore_evidence.py
python3 scripts/export_public.py --output build/public-eiv-final
python3 scripts/publish_github.py --repository VillaforTech/eiv --apply --source build/public-eiv-final

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
