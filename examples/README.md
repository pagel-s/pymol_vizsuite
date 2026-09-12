# Runnable examples

From the repository root, open either file directly in PyMOL:

```bash
pymol examples/paper_figure.pml
pymol examples/pitch_hero.pml
```

They fetch public structure 4HHB and write a finished PNG to the current
directory. For your own structure, replace the `fetch` line with `load
your_structure.pdb` and keep the `viz` and `viz_render` lines unchanged.
