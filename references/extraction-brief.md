# Copy extraction brief (paste verbatim into every extraction agent's prompt)

You are extracting visitor-facing copy from website source files for a client wording review.
Your output is merged with other agents' output by a script, so follow the contract exactly.

## Output

Write a single JSON array to the output path you were given. One object per string, in the order
the strings appear on the rendered page (document order within each file):

```json
{
  "file": "custom-about.hbs",
  "line": 12,
  "page_key": "ABOUT",
  "section": "Chairperson's message",
  "element": "Section heading (h2)",
  "text": "Scaling a vision rooted in place",
  "chars": 32,
  "has_dynamic": false,
  "constrained": true
}
```

## Field rules

- `file` — path relative to the repo root (or to the snapshot directory for exported CMS/settings
  data), exactly as it exists on disk.
- `line` — 1-based line where the string starts.
- `page_key` — the short uppercase key you were assigned for this file. Do not invent new keys.
- `section` — short human label for the page section, inferred from the enclosing section element
  and its heading ("Hero", "Vision & mission", "Newsletter signup"). Reuse the *identical* label
  for every string in that section so the document groups cleanly.
- `element` — described **for a non-technical reviewer**, from this vocabulary where it fits:
  "Page title (h1)", "Section heading (h2)", "Sub-heading (h3)", "Kicker", "Body paragraph",
  "List item", "Card title", "Card body", "Button label", "Link text", "Navigation item",
  "Stat number", "Stat label", "Quote", "Quote attribution", "Alt text", "ARIA label",
  "Form label", "Form placeholder", "Form message", "Meta description", "Site title",
  "Copyright line", "Legal clause".
- `text` — exact wording with markup stripped, whitespace collapsed to single spaces, trimmed.
  Render an inline `<br>` as `" / "`. Decode HTML entities (`&amp;` → `&`). Preserve punctuation,
  capitalisation and spelling exactly — including mistakes. Do not correct anything.
- `chars` — length of `text` (the merge script recomputes this; give your best value).
- `has_dynamic` — true if the string contains a template expression (`{{...}}`, `${...}`,
  `{t('...')}`, `<?php ... ?>`). Keep the expression verbatim inside `text`.
- `constrained` — true where length matters: hero titles, card/feature titles, button labels,
  kickers, navigation items, stat numbers/labels, footer link labels, form placeholders. False for
  body prose and legal clauses.

## What to extract

All visible text, plus these easily missed kinds: `alt` text, `aria-label`, `title` attributes
that show as tooltips, form labels/placeholders/submit labels, success/error/validation messages,
empty states, 404/error page text, copyright and legal footers, and strings inside locale/i18n
files used by your assigned templates.

## Failure modes — read carefully

- Read every assigned file **in full**. Do not sample, summarise, paraphrase or skip repetitive
  blocks. Eleven team cards means eleven sets of entries. Forty legal clauses means forty entries.
- Do not invent entries. Every `text` must be traceable to the file.
- Do not extract class names, URLs, image paths, inline styles, code comments, or strings that are
  purely dynamic with no hardcoded wording (e.g. `{{title}}` alone).
- Do not edit any repository file.
- If a string spans inline tags (`<strong>`, `<a>`, `<em>`), extract it as one string with the tags
  stripped.
- For conditional or looped blocks, record the hardcoded text as written; if you had to record
  rendered text that is not a literal substring of the source, say so in your report.

## Report back

After writing the JSON, reply with: the number of entries per file; any file that contained no
copy; judgement calls (ambiguous elements, conditional text, strings you weren't sure were
visitor-facing); and anything that looks like a source defect (literal Markdown in HTML, anchors
to missing IDs, hardcoded placeholder values, templates that look unused) — with file and line,
described as what you saw, not a conclusion.
