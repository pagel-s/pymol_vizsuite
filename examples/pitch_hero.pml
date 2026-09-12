# Run from the repository root:
#   pymol examples/pitch_hero.pml
#
# A clean cover or pitch image. `viz story` deliberately omits labels, keys,
# and scale bars so the molecule owns the frame.

run pymol_vizsuite.py
fetch 4hhb, async=0
viz story, frame=slide, view=hero
viz_render haemoglobin-hero.png, slide
