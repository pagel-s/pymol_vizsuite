# Run from the repository root:
#   pymol examples/paper_figure.pml
#
# A complete, publication-ready starting point. Replace `fetch 4hhb` with
# `load your_structure.pdb` when working with a local structure.

run pymol_vizsuite.py
fetch 4hhb, async=0
viz paper
viz_render haemoglobin-paper.png, fit, width=2400
