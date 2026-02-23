---
name: markdown
description: >
  Markdown formatting and structure skill based on CommonMark, GFM, and markdownlint conventions.
  Covers: headings, lists, tables, code blocks, links, whitespace, and anti-patterns.
  Use when: writing or reviewing any `.md` file — docs, rules, skills, CLAUDE.md, memory, README.
version: "1.0"
date: 2026-02-23
user-invocable: true
argument-hint: ""
---

# Markdown

Formatting and structure conventions for Markdown files. Based on CommonMark spec, GitHub Flavored Markdown (GFM) extensions, Google Markdown style guide, and markdownlint defaults.

## 1. Consistency choices

These are arbitrary but must be consistent within a file and across a project:

| Element | Convention | Rationale |
|---|---|---|
| Headings | ATX (`#`) | Consistent, easy to grep |
| Unordered lists | Hyphens (`-`) | Avoids `*` ambiguity with emphasis |
| Ordered lists | Lazy numbering (`1.` for all) | Diffs stay clean on reorder |
| Emphasis | Asterisks (`*italic*`, `**bold**`) | More common than underscores |
| Code fences | Backticks (`` ``` ``) | Standard, not tildes |
| Horizontal rules | `---` | Three hyphens, nothing else |
| Link style | Inline for short/one-off, reference for long/repeated | Balance readability and maintainability |

## 2. Headings

### Structure

- One `#` (H1) per file — the document title
- Increment by exactly one level — never skip from `##` to `####`
- Blank line before and after every heading
- Do not end headings with punctuation (no trailing `.`, `:`, `?`)
- Do not use emphasis (`**`, `*`, `` ` ``) inside headings — the heading itself provides emphasis
- Heading text must be unique within the document — enables reliable fragment links

### Case

- Sentence case for headings: capitalize the first word and proper nouns only
- Exception: title case is acceptable for the H1 document title

### Examples

```markdown
# User Authentication

## Token lifecycle

### Refresh token rotation
```

### Anti-patterns

```markdown
# user authentication          <!-- lowercase H1 -->
## Token Lifecycle:             <!-- trailing punctuation -->
#### Deep heading               <!-- skipped H3 -->
## **Important** section        <!-- emphasis in heading -->
```

## 3. Lists

### Markers

- Unordered: `-` (hyphen), consistently throughout the file
- Ordered: `1.` for every item (lazy numbering) — renderers auto-number, diffs stay clean
- Blank line before the first item and after the last item of a list
- No blank lines between items in a tight list (same logical group)
- Blank line between items only when items contain multiple paragraphs or blocks

### Content

- Single-sentence items: no trailing period
- Multi-sentence items: use periods on all sentences
- Indent continuation lines to align with the first character of the item text (3 spaces for `-`, 3 spaces for `1.`)

### Nesting

- Indent nested lists to align with the parent item text
- Maximum 3 levels of nesting — deeper nesting signals the content should be restructured

### Examples

```markdown
- First item
- Second item with a longer description
  that wraps to the next line
- Third item

1. Step one
1. Step two
1. Step three
```

## 4. Tables

### Formatting

- Blank line before and after every table
- Use leading and trailing pipes: `| cell | cell |`
- Align pipes vertically for source readability (not required by spec, but helps review)
- Same number of columns in every row — no ragged tables
- Header separator uses `---` (minimum three hyphens per column)

### Content

- Keep cells concise — if a cell needs a paragraph, the data doesn't belong in a table
- Prefer lists when data isn't truly two-dimensional
- Use code formatting in cells when showing identifiers, commands, or paths
- No empty tables — if you have only one column, use a list instead

### Alignment

- Default: left-align (no colons needed in separator)
- Right-align numbers: `---:` in separator
- Use alignment sparingly — most content reads fine left-aligned

### Examples

```markdown
| Command | Description |
|---|---|
| `just check` | Run linter and typecheck |
| `just test` | Run all tests |
```

## 5. Code blocks

### Fencing

- Always use fenced code blocks (triple backticks) — never indented code blocks
- Always declare the language after opening backticks: `` ```rust ``, `` ```sql ``, `` ```markdown ``
- Use `text` or `console` for plain output with no syntax highlighting
- Blank line before and after every code block

### Shell examples

- Do not prefix commands with `$` unless showing interleaved commands and output
- When showing command + output, use `$` prefix for the command lines only
- Use `sh` or `bash` as the language identifier for shell commands

### Content

- Keep examples minimal — show the relevant pattern, not a full file
- Use comments sparingly — the surrounding prose should explain the example
- Mark incorrect patterns clearly: `// WRONG`, `// CORRECT`, `<!-- WRONG -->`, `<!-- CORRECT -->`

### Examples

````markdown
```rust
// CORRECT — filter before aggregating
let total: BigDecimal = items
    .iter()
    .filter(|i| i.currency == "USD")
    .sum();
```
````

## 6. Links

### Link text

- Descriptive text that makes sense out of context — never "click here", "here", "this", "link"
- Screen readers navigate by link text — generic labels are inaccessible
- Keep link text concise but meaningful: 2-6 words typical

### Inline vs reference

- Inline `[text](url)` for short URLs used once
- Reference-style `[text][ref]` with `[ref]: url` at the bottom for long or repeated URLs
- Group reference definitions at the end of the file or end of the section

### URL conventions

- Use HTTPS for all external links
- Fragment links (`#heading-text`) must reference a valid heading in the document
- Relative paths for links within the same repository
- Verify links still resolve after renaming or moving files

### Examples

```markdown
<!-- Inline — short, used once -->
See the [CommonMark spec](https://spec.commonmark.org/) for details.

<!-- Reference — long URL, used multiple times -->
The [API design guide][api-guide] covers pagination patterns.

[api-guide]: https://cloud.google.com/apis/design/design_patterns#list_pagination
```

## 7. Whitespace

### Line endings

- No trailing whitespace on any line
- No hard tabs — use spaces for indentation
- File ends with exactly one newline (no blank line at EOF, no missing newline)

### Blank lines

- One blank line between blocks of different types (heading, paragraph, list, code, table)
- No multiple consecutive blank lines — exactly one blank line as separator
- Blank line before and after: headings, code blocks, tables, horizontal rules, lists

### Line length

- No hard line-length limit for prose — let the editor wrap
- Exception: code blocks should stay under 100 characters for readability in terminals and diffs
- Tables: keep rows on a single line — horizontal scrolling is preferable to wrapped table rows

## 8. Anti-patterns

Quick-reference table of common mistakes:

| Anti-pattern | Problem | Fix |
|---|---|---|
| Mixed list markers (`-` and `*`) | Inconsistent, confusing diffs | Pick one, use throughout |
| Skipped heading levels | Broken outline hierarchy | Increment by one |
| Indented code blocks | Fragile, no language hint | Use fenced blocks |
| Bare URLs | Poor accessibility | Wrap in `[descriptive text](url)` |
| Emphasis with spaces (`* text *`) | Won't render as emphasis | Remove spaces: `*text*` |
| Generic link text ("click here") | Inaccessible, meaningless in link lists | Describe the destination |
| Inline HTML (`<br>`, `<b>`) | Breaks portability, harder to maintain | Use Markdown equivalents |
| Trailing punctuation in headings | Noisy, inconsistent | Remove `.`, `:`, `?` |
| Multiple H1s | Ambiguous document title | One H1 at the top |
| No language on code fences | No syntax highlighting | Always declare language |
| Multiple consecutive blank lines | Visual noise in source | Exactly one blank line |
| Hard tabs | Inconsistent rendering | Spaces only |
