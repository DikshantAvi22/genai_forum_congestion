Build instructions for the LaTeX report
======================================

Working directory:
  /home/dikshantg/genai_forum_congestion/paper

Recommended build:
  latexmk -pdf main.tex

Fallback build:
  pdflatex main.tex
  bibtex main
  pdflatex main.tex
  pdflatex main.tex

Notes:
  - Replace the placeholder email handles in paper/main.tex before final submission.
  - The file paper/neurips_2021.sty is a repo-local scaffold so the project compiles
    in this workspace. If you need the exact official NeurIPS 2021 style file, swap
    it in before the final PDF export.
  - Figures are referenced directly from ../sim/figs and ../sim/figs/extra.
  - After building, rename the final PDF using the course naming rule once the final
    email handles are known.
