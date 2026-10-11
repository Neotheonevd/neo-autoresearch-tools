---
name: neo-paper-figures
description: Create or refine compact, editable academic motivation and method figures using Neo's paper-figure style, reference images and iterative visual review. Use for research diagrams and PPT paper figures, especially parallel modules, evidence relations and candidate populations.
---

# Neo's paper figures

Use this skill for a scientific diagram, not an entire slide deck. Preserve the
method's actual semantics while improving visual communication. Do not infer
algorithmic effectiveness from an attractive diagram.

## Start with meaning

Write a short internal inventory: inputs, modules, outputs, serial/parallel
relations, feedback, and what the figure must demonstrate. Match the user's
sketch before decorating it. In the reference example, Reader and Relation
Analyst are **parallel**, both receive the map, and both inform Judger. Never
draw Reader → Relation Analyst merely to simplify layout.

Keep proposed architecture distinct from implemented or experimentally verified
mechanisms. A conceptual figure is not an implementation receipt.

## Visual language

- Use Comic Sans MS for English when following this style; confirm availability.
  Use one title size and one smaller label size. Italic headings are preferred.
- Start with white or very pale backgrounds, fine dark outlines, quiet pastel
  groups and short arrows. Round dashed or dash-dot panel borders fit the style.
- Default palette: ink `#202734`, navy `#172A4E`, blue `#9DBDDD`, green `#BDDBB2`,
  purple `#C6B4DF`, pink `#F6D7D8`, gold `#E8B950`, teal `#AED6C9`.
- Use an icon to communicate a role, a log/document to communicate input, nodes
  and edges for relations, and small explanation cards for candidate arguments.
  Icons support meaning; do not use them to fill arbitrary blank space.
- Keep labels short. Put mechanism details into visible structure, examples,
  contrasting paths and state transitions rather than paragraphs inside boxes.
- Keep panels compact and aligned. Reduce internal gaps before shrinking text.
  Do not stretch the artwork merely to fill a full slide.
- Prefer short straight or orthogonal arrows; separate forward flow from feedback.
  Route feedback around the panel perimeter and avoid crossings over labels.

## Depict mechanisms, not just module names

For a map, show actual branching, a highlighted decision and original references.
For an error relation, distinguish dependency, propagation, correction and
independence visually and add a tiny legend if needed.

For a candidate population, show multiple distinct error+argument cards, a
comparison of decisive premises, evidence feedback, and visible keep/revise/
reject outcomes. A row labelled "Judger" alone does not explain the mechanism.
These are example representations; do not impose this architecture on unrelated
papers.

## Deliver and verify

Use editable shapes and text for the diagram where possible. Role illustrations
may be raster assets. Never claim an all-vector or fully editable image when
some components are embedded bitmaps. Do not bundle proprietary font files.

Render the actual PPT/PDF, inspect it at its intended paper size, and correct
overlaps, tiny labels, line weights, arrow ambiguity and inconsistent spacing.
For an ACL single-column motivation figure, use a compact vertical composition
and test at the actual column width; the wide method figure can span two columns.

Provide a full-slide editable PPTX for easy copying, plus a tightly bounded paper
export when needed. Cropping the paper export must not silently change the PPT
slide dimensions. Retain the agreed final artifacts rather than cluttering the
delivery with every intermediate draft.

Read [the reusable prompts](references/prompts.md) when drafting or revising a
figure. Read [iteration lessons](references/iteration-lessons.md) when a rendered
figure looks sparse, generic or semantically wrong. Example outputs and their
limitations are in [the gallery](../../docs/gallery.md).
