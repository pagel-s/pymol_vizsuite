# PyMOL Viz Suite: agent quick guide

Use this guide when a user asks for a molecular image. The goal is a finished,
reproducible figure with the fewest meaningful choices.

## Fast path

1. Load `pymol_vizsuite.py` in PyMOL with `run /path/to/pymol_vizsuite.py`.
2. Load or fetch the structure.
3. Pick exactly one intent, apply it, then render.

```pml
viz paper
viz_render output.png, fit, width=2400
```

If no intent is stated, use `viz_auto`; it inspects the structure and selects a
sensible style.

## Intent map

| User wants | Use |
|---|---|
| A restrained publication figure | `viz paper` |
| A striking talk slide or cover | `viz story, frame=slide, view=hero` |
| An illustrated molecular body or assembly | `viz illustration` |
| A binding pocket or ligand close-up | `viz site` |
| An AlphaFold confidence view | `viz confidence` |
| A side-by-side style decision | `viz_gallery` |

`viz story` is deliberately annotation-free so it can work as a cover or pitch
image. If scientific context is needed, opt in at render time with
`legend=1`, `scalebar=20`, or `name=...`.

## Rendering contract

Always use `viz_render` for a deliverable. The viewport is only a preview;
outlines and post-processing are created at render time.

```pml
viz_render figure.png, column              # journal single column
viz_render figure.png, dcolumn             # journal double column
viz_render figure.png, fit, width=2400     # molecule-shaped canvas
viz_render slide.png, slide                # 16:9 slide
```

## One change at a time

Apply a style before changing the camera or framing. Then make the smallest
scientifically meaningful adjustment:

```pml
viz paper, coloring=ss                     # secondary structure
viz_focus resi 140-170, 0.8                # one region matters
viz_label residues, byres (polymer within 4.2 of organic)
```

Use `viz_color` to recolour without losing the selected representation and
lighting. Use `viz_script output.pml` if the user needs the plain PyMOL
commands that reproduce the current image.

## Avoid

- Do not use `viz story` for a quantitative result where lighting or depth fade
  could obscure a measurement; start with `viz paper` instead.
- Do not call `viz_render` before applying a style.
- Do not invent long custom command sequences when an intent preset already
  expresses the requested outcome.
