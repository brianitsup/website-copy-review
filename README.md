# website-copy-review

An agent skill (Claude, Codex CLI, Gemini CLI, Cursor, opencode) that pulls every piece of visitor-facing copy out of a website codebase and turns it into a review document for clients:

- **Landscape A4 `.docx`**, one section per page, one row per string, each with a `PAGEKEY-NN` Ref code
- Blank **Suggested revision** and **Notes** columns for reviewers
- Character counts and length guidance on length-sensitive rows (headings, buttons, menu items)
- **`copy-review-manifest.csv`** so returned edits can be applied back to the source by Ref code
- Every extracted string is checked against its source file (raw, tag-stripped, whitespace-squashed)

## Layout

```
SKILL.md                         workflow the agent follows
scripts/merge_and_verify.py      merge sub-agent extractions, assign Refs, verify, write manifest
scripts/build_review_docx.py     build the review .docx (python-docx) and self-check it
references/extraction-brief.md   brief pasted verbatim into each extraction sub-agent
assets/pages.example.json        page metadata + cover-page template
```

## Requirements

Python 3 with `python-docx` (the skill installs it into a scratch virtualenv). LibreOffice (`soffice`) and `pdftoppm` for the visual check.

## Install

```bash
git clone https://github.com/brianitsup/website-copy-review ~/my-skills/website-copy-review
ln -s ../../my-skills/website-copy-review ~/.agents/skills/website-copy-review
```

## Licence

MIT
