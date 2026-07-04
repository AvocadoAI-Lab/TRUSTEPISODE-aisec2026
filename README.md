# TrustEpisode AISec 2026 submission draft

This package contains an anonymous ACM two-column draft for:

**TrustEpisode: Calibrated Episode Risk Scoring with Evidence-Grounded Agentic RAG for Multi-Step Cyber Attacks**

## Contents

```
main.tex              # Preamble, title, abstract, bibliography
sections/
  intro.tex           # Section 1: Introduction
  related.tex         # Section 2: Related Work
  arch.tex            # Section 3: TrustEpisode Method
  exps.tex            # Section 4: Evaluation (+ Discussion)
  conc.tex            # Section 5: Conclusion
bib/
  references.bib      # BibTeX references
figs/
  fig1_workflow.png
  fig2_episode_scoring.png
  fig3_scoring_assurance.png
```

## Compile

```bash
latexmk -pdf -bibtex main.tex
```

The draft uses the ACM `sigconf` class in anonymous two-column mode.

## Collaboration notes

- Edit one section file at a time under `sections/` to reduce merge conflicts.
- Add new figures to `figs/`; paths are resolved via `\graphicspath{{figs/}}` in `main.tex`.
- Add new references to `bib/references.bib`.

## Important draft status

The main result table intentionally contains em dashes. Replace those cells only with measured results from the three-tier evaluation: DARPA Transparent Computing traces, controlled Caldera BAS scenarios, and anonymized enterprise validation. The draft does not fabricate experimental outcomes.
