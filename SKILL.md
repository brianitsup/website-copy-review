---
name: website-copy-review
description: Extract every piece of visitor-facing copy from a website codebase (templates, components, locale files, plus CMS/site settings like nav labels and meta description) into a client-ready landscape .docx review document with addressable Ref codes, a blank "Suggested revision" column, and a CSV manifest so approved edits can be applied back to source. Use whenever the user wants the words on a site reviewed, proofread, audited, extracted, exported or signed off — "extract the website copy for review", "get the client to review our copy", "all the text on the site in a Word doc", "copy review", "proofing document", "send the wording to the comms team", or a wording-focused content inventory. Not for structural, SEO or performance site audits.
---

# Website copy review

Turn a website codebase into a document a non-technical reviewer can read page by page and mark up,
where every string keeps an address (a Ref code) so their edits can be applied back to the source
mechanically.

## Why it is built this way

Website copy is not prose. It is hundreds of short strings in fixed layout slots inside markup.
So:

- A prose dump with tracked changes comes back as a blur of insertions that can't be placed back
  into markup without guesswork. Hence one row per string, with a Ref code.
- A reviewer who turns a 4-word card heading into 12 words breaks the layout and can't see that
  from Word. Hence character counts and plain-language length guidance on constrained rows.
- Reviewers never see the code. Hence every row says what it is ("Button label", "Alt text") in
  plain words, and every page section says where it lives on the live site.

The document must read top-to-bottom per page (so tone and narrative can be judged) while keeping
every string individually addressable.

## Bundled files

`scripts/merge_and_verify.py`, `scripts/build_review_docx.py`, `references/extraction-brief.md`
and `assets/pages.example.json` live beside this file. If they are missing (the skill was
installed as SKILL.md only), look for them in `~/my-skills/website-copy-review/` or the
`brianitsup/website-copy-review` repo; if neither is reachable, tell the user rather than
improvising the document layout, because it must not vary between runs.

## Ground rules

- **Read-only.** Never edit the repository. All output goes to the scratchpad unless the user asks
  for it in the repo.
- Install `python-docx` in a virtualenv in the scratchpad, not globally:
  `python3 -m venv <scratch>/venv && <scratch>/venv/bin/pip install python-docx`
- Report honestly. If a file couldn't be parsed or a check couldn't run, say so; never quietly
  narrow the scope.
- If the repo has an issue-first (or similar) workflow convention in `AGENTS.md`, `CLAUDE.md`,
  `PROJECT_WORKFLOW.md` or `CONTRIBUTING.md`, tell the user the returned edits and any defects
  will need an issue before implementation. Don't open one unasked.

Expect scale: a medium brochure site is ~400–600 items across 15–20 pages, a 50–60 page document.
That is normal; per-page tables keep it navigable.

## Step 1 — Settle scope (ask once, with defaults)

Ask these together (AskUserQuestion if available), recommending the defaults:

1. **Which copy?** Hardcoded copy in templates/components only *(default — editor content can be
   fixed in the CMS without a code change)*, or also CMS-authored posts/pages?
2. **How will reviewers mark changes?** Blank "Suggested revision" column *(default — unambiguous
   and mechanically applicable)*, or Word comments/track changes (natural, but hard to apply back).
3. **Which content state?** Working tree, or live/production? Flag that a local database or content
   snapshot may lag what is actually published.

If the user is away, take the defaults and say so at the top of the report. The answers go on the
cover page (`meta.scope` in `pages.json`).

## Step 2 — Discover where copy lives

Don't assume a stack. Inspect the repo (package.json, theme manifests, framework config, directory
layout) and list copy sources:

- **In code:** `.hbs`, JSX/TSX, Vue, Svelte, Astro, Blade, ERB, Twig, PHP themes, HTML,
  Markdown/MDX content files, i18n/locale JSON or YAML.
- **Outside code:** CMS database/API (Ghost, WordPress, Sanity, Contentful, Strapi) and
  visitor-facing site settings that aren't in the repo — **site title, meta description,
  navigation labels, CTA/button labels set in admin**. When you pull these, save the raw export
  into `<scratch>/snapshots/` so they can be verified like any other source (see Step 4).

Always cover these easily missed categories, each labelled so reviewers know what they're seeing:
`alt` text (screen readers and search engines read it — partner/product names must be right),
`aria-label`, form placeholders, submit labels, success/error/validation messages, empty states,
404/error pages, copyright lines and legal footers.

Map each page template to its **live URL path** (routes.yaml, file-based routing, router config,
CMS page→template assignments). If a template has no page or route, say so explicitly in that
page's note — its copy is unreachable, and reviewers should know before spending time on it.

Then write `<scratch>/pages.json` from `assets/pages.example.json`: one entry per page in the order
the document should present them, with `key`, `title`, `url`, `source`, optional `note`, plus the
`meta` block (project, scope answers, exclusions, templates with no hardcoded copy). The build
script reads this — page metadata never gets hardcoded.

## Step 3 — Extract in parallel with a fixed contract

1. **Enumerate the whole surface first**: every page template *and* every partial/shared component
   those pages include (headers, footers, cards, newsletter forms, CTAs). Partials are what get
   lost when files are split between agents.
2. Split into non-overlapping groups (roughly 3–6 files or ~1,500 lines each) and assign every file
   explicitly. Shared partials get their own page entry (e.g. `FOOTER`, `NAV`) with a note that
   they appear site-wide, rather than being repeated under every page.
3. Spawn one sub-agent per group, in a single turn, on a mid-tier model (e.g. Sonnet): the work is
   mechanical, but omissions are invisible and fatal. Paste `references/extraction-brief.md`
   **verbatim** into every prompt, followed by that agent's file list, the `page_key` to use for
   each file, the repo root, and the output path `<scratch>/extract/<group>.json`.
4. When they return, confirm every enumerated file appears in some output (or was reported as
   containing no copy). Re-assign anything missing.

Collect each agent's reported judgement calls; you will need them in Step 4 and the final report.

## Step 4 — Merge and verify independently (don't skip)

Agent self-checks are not verification. Run:

```bash
<venv>/bin/python scripts/merge_and_verify.py \
  --extract-dir <scratch>/extract --pages <scratch>/pages.json \
  --repo <repo-root> [--snapshot-dir <scratch>/snapshots] --out <scratch>/out
```

It merges all extractions in `pages.json` order, assigns `PAGEKEY-NN` Refs, recomputes `chars`,
and re-checks **every** string against its source file with three progressively looser
normalisations — raw (whitespace collapsed), tag-stripped, whitespace-squashed — because each
catches a different thing (attribute text passes raw and *fails* tag-stripped by construction;
that's expected). It also asserts no duplicate Refs, no empty text, and that every item's
`page_key` exists in `pages.json`. Outputs: `items.json`, `copy-review-manifest.csv`,
`verification.md`.

Exit code is non-zero while anything is unresolved. For each `UNMATCHED` row, open the source and
look. Legitimate residue is usually conditional/looped blocks where the agent recorded the
*rendered* text rather than a literal substring — confirm it renders as recorded, then list it in
`<scratch>/accepted.json` as `{"REF": "reason"}` and rerun with `--accept <scratch>/accepted.json`.
Fix genuine errors in the extraction JSON (not the repo) and rerun. Refs are assigned at merge,
so fix data, then rerun, then build.

Also spot-check completeness: pick two or three of the densest files and compare the item count
against a quick read of the file. Missing strings don't show up in any automated check.

## Step 5 — Build the document

```bash
<venv>/bin/python scripts/build_review_docx.py \
  --pages <scratch>/pages.json --items <scratch>/out/items.json \
  --out <scratch>/out/<Project>-Website-Copy-Review.docx
```

The script owns the layout so it never varies between runs: landscape A4, 1.4 cm margins; cover
page (scope, what is/isn't included, how to review, keep length-sensitive rows near their length,
don't renumber or delete Refs, check *facts* — years, headcounts, figures, partner names, job
titles — as carefully as wording); contents table with totals and empty templates; one section per
page on a new page; columns Ref 2.2 / Element 4.3 / Current copy 8.4 / Suggested revision 8.4 /
Notes 3.6 cm; dark repeating header row; tinted uppercase section banner rows; zebra striping;
char-count guidance on constrained rows; tinted cells and a "keep the `{{…}}` part" warning on
dynamic rows; closing page with next steps and a sign-off table. It re-opens the file and asserts
the row count matches and the revision/notes columns are empty.

Never pre-fill "Suggested revision" or "Notes". The reviewer's judgement is the point.

If the user chose Word comments/track changes in Step 1, still build this document (the Ref codes
are what make tracked changes traceable) and tell them edits may need manual matching.

## Step 6 — Look at it before delivering

Structural checks prove the data is right, not that it reads well. Render and actually view: the
cover, a settings/navigation page, and the densest page of long paragraphs (where widths fail).

```bash
soffice --headless --convert-to pdf --outdir <dir> <file>.docx
pdftoppm -png -r 80 -f <n> -l <n> <file>.pdf <prefix>
```

Open the PNGs with Read. If these tools are missing, say plainly that no visual check happened.

## Step 7 — Report source defects separately

Reading every line of markup surfaces real bugs. Report them in a separate section (or a separate
`source-defects.md`) — they are code issues, not wording. Common ones:

- Literal Markdown in rendered HTML (`**bold**` showing on the page)
- Anchor links to IDs that exist nowhere
- Links to sections that exist but contain nothing actionable
- Templates with no page/route, so their copy is unreachable
- Orphaned CMS content behind a custom template that overrides it
- Placeholder values hardcoded in reusable templates

**Verify each yourself before reporting it** — grep for the target ID, open the template. Agents
overstate these: a "broken anchor" once turned out to have a valid target whose section simply had
nothing to act on. Describe what is actually there, with file and line.

## Step 8 — Deliver

Send the `.docx` to the user. Mention, briefly: total items and pages, the scope decisions taken,
the manifest CSV (for applying returned edits by Ref — keep it out of the reviewer's hands), any
verification residue you accepted and why, the defects list, and the issue-first note if the repo
has that convention.

## Applying returned revisions (when the user comes back)

Read the returned `.docx` table rows (Ref + Suggested revision + Notes), join to
`copy-review-manifest.csv` by Ref, and for each non-empty revision locate `text` in `file` near
`line` and replace it. Flag rather than silently trim any revision that is far over its `chars` on
a constrained row, and any that drops a `{{…}}` expression. Show the user the planned changes
before editing the repo.
