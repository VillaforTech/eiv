# EIV project page draft

## Preview inside the existing personal website

Serve the draft over HTTP from the fresh public checkout:

```sh
python3 -m http.server 4173 --bind 127.0.0.1
```

Open **http://127.0.0.1:4173/portfolio/villafortech-preview.html#caso-eiv** for the proposed EIV
integration in the author's actual website design. This serves the public checkout as static files; it is separate from the Python workbench on port 8765. The “En tus proyectos” and “Caso de estudio EIV”
controls switch between a native-style project list and the Spanish case study.
The EIV row opens the case view. The case now includes version-pinned source links, release validation and runnable reproduction commands. The page is a local visual draft; neither view
has been published to the live website.

The HTML preview follows the actual live website read on 2026-11-15: Manrope
for body and display text, the green clover/wordmark, lighter paper and forest
tokens, restrained project rows, case metadata and article rail. The MDX preserves
the current website repository's compatible schema and content classes. It is separate from `index.html`, the earlier standalone EIV
microsite draft. Links to the author's existing navigation open the real site;
the evidence and technical-report links point to the public versioned repository, so they also work when serving only the preview folder.

**Integration file:** `villafortech-eiv.mdx` is the Spanish content draft. For
review in the website repository, place it at `drafts/eiv/eiv-es.mdx`, outside
the live content collection. The intended final content path is
`src/content/projects/es-eiv.mdx`, producing `/es/projects/eiv/` through
`translationKey: eiv`. The frontmatter matches the current project schema and
uses `evidence: hold`; project routes and lists exclude that state. The working
copy also lives outside the live content collection, so production builds ignore it.
The repository and v0.4.0 release links are public. Before activation, review the public source links,
add the paired English entry at `src/content/projects/eiv.mdx`, change the
evidence state appropriately, and run the site's full verification. The draft
does not replace the current homepage flagship.

### Website source and asset provenance

The website content schema, layout classes and earlier asset set were read from
[`villafortech-labs/villafortech-site`](https://github.com/villafortech-labs/villafortech-site)
at master commit `71294e3c15166bf270151100688a62f339a7a3a9`. Source files:

- [`src/styles/global.css`](https://github.com/villafortech-labs/villafortech-site/blob/71294e3c15166bf270151100688a62f339a7a3a9/src/styles/global.css): design tokens, typography, responsive layouts, cards and case styles.
- [`src/components/Navbar.astro`](https://github.com/villafortech-labs/villafortech-site/blob/71294e3c15166bf270151100688a62f339a7a3a9/src/components/Navbar.astro) and [`src/i18n.ts`](https://github.com/villafortech-labs/villafortech-site/blob/71294e3c15166bf270151100688a62f339a7a3a9/src/i18n.ts): actual signature, navigation labels and language routes.
- [`src/layouts/ContentLayout.astro`](https://github.com/villafortech-labs/villafortech-site/blob/71294e3c15166bf270151100688a62f339a7a3a9/src/layouts/ContentLayout.astro): case-study header, metadata, disclosure, article rail and ending.
- [`src/content.config.ts`](https://github.com/villafortech-labs/villafortech-site/blob/71294e3c15166bf270151100688a62f339a7a3a9/src/content.config.ts): MDX frontmatter schema.

The live page has a later CSS override and a clover wordmark which are absent
from that checkout. The HTML preview follows those live overrides rather than
assuming the checkout matches production. `website-design-reference.json` records
the live URL, observed tokens, HTML/CSS digests and the clover SVG digest.
The source checkout remains authoritative for a future native MDX integration;
its styling will need reconciliation with the deployed design before activation.

The clover was read from `https://www.villafortech.com/brand/clover.svg` without
modification. Other assets under `villafortech-assets/` were copied read-only
from the existing site checkout. Their Git blob hashes match the corresponding assets in the above
remote source tree. The integration draft is copied to `drafts/eiv/` in the website checkout; production source, routes and assets remain unchanged.

| Asset | Original path | Git blob SHA |
| --- | --- | --- |
| Live clover (SHA-256) | `https://www.villafortech.com/brand/clover.svg` | `bb9744ab1c62ac64678eaacc48809dcb0678da2b1eb07281412d6895c9ab0c03` |
| Desktop signature (earlier design, retained) | `public/brand/signature-horizontal.svg` | `c8cbc4d41dd24baf2fe4cb23266d2e28650ae568` |
| Compact signature (earlier design, retained) | `public/brand/signature.svg` | `90c3b6ca7ae0d483eece56f189015a0d78c79d39` |
| Manrope variable font | `public/fonts/manrope/Manrope[wght].ttf` | `23dcf5e05a97f19a3567d40ebb3765580a4325f7` |
| Instrument Serif regular | `public/fonts/instrumentserif/InstrumentSerif-Regular.ttf` | `36fac00ef9b7d523236df6536cb09c712bb2c7e4` |
| Instrument Serif italic | `public/fonts/instrumentserif/InstrumentSerif-Italic.ttf` | `192c3eda9864241ad280e9bcc84e258c80a4a588` |

**Third-party font licenses:** Manrope and Instrument Serif retain their SIL
Open Font License terms. The original `OFL.txt` is bundled in each font directory;
the repository's MIT license does not replace those terms. The signatures are
the author's existing brand assets, included only to preview his website
integration; no general trademark or branding rights are granted.

The preview's action record is explicitly illustrative, not a newly executed
Python result. The 194-test count refers specifically to the verified v0.4.0 CI matrix,
not a real-world safety rate. No analytics, forms, models, tools or remote font
requests run in the preview. The HTML contains local navigation controls only.

## Standalone EIV microsite draft

An editorial project page for Roberto Villafuerte's personal portfolio. Open
`index.html` directly in a browser; it needs no build, server, package install,
external font, analytics, model, or API key. Keep the five runtime files together:

- `index.html` — narrative, exact results, primary references, accessible structure.
- `style.css` — responsive layout, reduced-motion and print styles.
- `demo.js` — finite teaching model, isolated from the research code.
- `app.js` — interactive controls, trace download, command copy.
- `favicon.svg` — local vector icon.

`website-copy.md` contains reusable project-card and case-study copy.

## Status and integration

This is a **draft, not a deployed website**. The public source repository is
[VillaforTech/eiv](https://github.com/VillaforTech/eiv). Its visibility was confirmed
at publication; website deployment is a separate operation.
The current page links to the adjacent project documents using relative paths,
so keep `portfolio/` inside the source tree when previewing it.

The personal-site HTML preview already uses verified public versioned links.
For a standalone deployment of the separate `index.html` microsite, replace its
relative source links with public repository URLs, or publish those documents too. Confirm
the published repository owner/name and default branch first. The external
author link is `https://villafortech.com`; the three academic links point to
publisher pages. Add an absolute canonical URL and social preview image only
after the final page URL and asset are available. Remove the draft footer when
the page is actually published.

The intended Spanish placement is `/es/projects/eiv/` and the paired English
placement is `/projects/eiv/` on the portfolio. The English case remains a separate
future editorial step before site activation. The page can also
be hosted as static files on any ordinary static host. It contains no tracking,
cookies, remote fonts, form submissions, or dependencies.

## What the interactive illustration does

Eight explicit candidates span recipient, format, and send-time dimensions.
The requested action is sending a report to Alex; the declared simulated intent
is Bea, plain text, later. Only recipient changes the allow/deny decision.

- **Targeted:** maximize the number of unlike-decision pairs separated by a
  question, with stable order breaking ties. One question reaches denial.
- **First:** ask the first positive-score question in format/time/recipient
  order. One or two questions end with abstention; three reach denial.
- **Omission:** remove every Bea interpretation. All supplied candidates allow,
  so no question is asked. The result is wrong relative to declared intent.
- **Unsure:** explicitly abstain after a nonselecting answer.

Question selection never reads the declared intent. The truthful answer oracle
reads it only after the visitor clicks “Apply truthful answer”. The site labels
the simulation as separate from the Python verifier; it neither invokes the
verifier nor contributes observations to any benchmark. The exported JSON also
records that distinction. The new optimal Python strategy is intentionally not
implemented in this small illustration; consult the actual workbench for it.

## Verification

```sh
node --check portfolio/demo.js
node --check portfolio/app.js
node --test portfolio/test-demo.cjs
```

The test exhausts the two strategies, four budgets, and two coverage settings,
checks abstention for nonselecting answers, confirms the pair scores and stable
order, verifies state immutability, and rejects invalid configurations.

The page uses landmarks, a skip link, associated labels, native keyboard
controls, a live decision region, text labels in addition to color, reduced
motion support, and horizontally scrollable evidence tables. Those features
are implementation choices, not a claim of a completed accessibility audit.

## Evidence maintenance

The page preserves the frozen V2, model-pilot, V3 and selection-counterexample
results. Do not replace those numbers with test counts or results of the teaching
model. Any new prospective study needs its own explicit protocol, denominator,
source, and result label. Keep negative findings adjacent to favorable ones.

Primary references checked against publisher pages on 2026-11-14:

1. Yao, Su, Sun, Yih. 2019. [Model-based Interactive Semantic Parsing](https://aclanthology.org/D19-1547/).
2. Cosler, Hahn, Mendoza, Schmitt, Trippel. 2023. [nl2spec](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18).
3. Saparina and Lapata. 2025. [Disambiguate First, Parse Later](https://aclanthology.org/2025.findings-acl.863/).
