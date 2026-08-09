# PyMOL Viz Suite

Turn a structure into a publishable figure in one command.

<p align="center">
  <img src="gallery/04_haemoglobin.jpg" width="49%" alt="Haemoglobin, space-filling with three tiers of ink" />
  <img src="gallery/05_assembly.jpg" width="34%" alt="GroEL/GroES chaperonin stood on its sevenfold axis" />
</p>

A single-file PyMOL plugin: 30 complete visual styles, a render pipeline that
keeps ink outlines the same weight in print as on screen, and automatic
orientation, framing, colour grouping, scale bars and colour keys.

**[See the gallery →](gallery/README.md)** · **[Full reference →](docs/REFERENCE.md)**

---

## Install

One file, no dependencies beyond what PyMOL already ships.

```bash
git clone <this repo> ~/pymol-vizsuite
```

Then either drop it in permanently:

```bash
echo "run ~/pymol-vizsuite/pymol_vizsuite.py" >> ~/.pymolrc
```

or load it for one session:

```
run ~/pymol-vizsuite/pymol_vizsuite.py
```

Or use PyMOL's **Plugin Manager → Install New Plugin → Choose file…** and pick
`pymol_vizsuite.py`. A *Viz Suite* entry appears in the Plugin menu.

Needs open-source PyMOL 2.x or 3.x. Post-processing — outline compositing,
gradients, glow, text, colour keys — uses `numpy` and the Qt build's `PyQt`,
both of which ship with a standard PyMOL. Without them everything still
renders, single-pass.

## Two minutes

```
fetch 4hhb, async=0
viz illustrative
viz_render ~/figure.png, fit, width=2400
```

That is the whole loop. `viz` picks the geometry, lighting, colours and camera;
`viz_render` ray-traces it and composites the outlines, scale bar and key.

Not sure what you want? Two commands answer that:

```
viz_auto        # inspects the structure and picks a style for it
viz_gallery     # renders every applicable style as a labelled contact sheet
```

## What it does for you

Everything in this list is decided from the structure, not from a default:

- **Orientation** on first styling. A symmetric assembly is stood on its n-fold
  axis so rings stack and a cap caps; anything else takes its widest projection.
- **Framing** fitted against a measured probe render, then backed off until
  nothing comes within 4 % of a frame edge, and centred on the subject's own
  measured extent.
- **Canvas shape** from the subject, with `size=fit`, so a wide complex is not
  boxed into a square with half the page empty.
- **Chain grouping** by comparing residues position by position, then splitting
  again where copies form separate spatial assemblies. Copies within a group
  alternate in chroma at constant hue, so a ring can be counted.
- **Ink** in three tiers — silhouette, chain boundary, per-residue contour — at
  a weight held constant as a fraction of image width, tapering as the subject
  gets larger so a ribosome does not become lace.
- **Scale bars** at a round length near a fifth of the frame.
- **Colour keys** for pLDDT, B-factor, hydropathy, charge, secondary structure,
  chain groups and polymer type. Every swatch is re-read off the finished scene,
  so a chain that is hidden or faded is described as it appears.
- **Cofactors** take one reserved saturated accent, keyed by residue name.
- **Annotation placement** scored over the area each item would occupy,
  including the area the others have already claimed.

## Commands

| Command | Does |
|---|---|
| `viz` | apply a style |
| `viz_auto` | inspect the structure and pick a style |
| `viz_render` | ray-trace to a file, with outlines and post-processing |
| `viz_gallery` | contact sheet of every style |
| `viz_figure` | compose rendered panels into a labelled figure |
| `viz_inset` | overview plus magnified callout, joined by leaders |
| `viz_color` | recolour without touching the style |
| `viz_focus` | make one selection the subject, push the rest back |
| `viz_interface` | colour a protein-protein interface, measure the buried area |
| `viz_partners` | name the two partners when the split is ambiguous |
| `viz_openbook` | open a complex so both contact faces face the reader |
| `viz_contact_table` | residue pairs across an interface, with distances |
| `viz_mix` | different representations for different selections |
| `viz_paint` | colour named selections, everything else quiet |
| `viz_highlight` | one set of residues loud, the rest of the fold neutral |
| `viz_super` | superpose two structures, spectrum over a grey reference |
| `viz_gaps` | draw every chain break as a dotted arc |
| `viz_cutaway` | cut the front off to reveal an interior |
| `viz_label` | residue, chain, terminus or ligand labels |
| `viz_membrane` | lipid bilayer as two planes |
| `viz_pose` | score candidate viewpoints (opt-in) |
| `viz_view` · `viz_frame` · `viz_bg` | camera, aspect and background presets |
| `viz_scalebar` | report the scale of the current view |
| `viz_turntable` | render a rotation as a PNG sequence |
| `viz_script` | export the equivalent plain `.pml` |
| `viz_check_palettes` | measure palettes for greyscale and colour-blind separation |
| `viz_list` | list everything available |
| `viz_reset` | back to PyMOL defaults |
| `viz_gui` | a panel, if you would rather click |

Every command has full PyMOL help: `help viz`, `help viz_render`, …

## Styles

```
architect   blueprint   charge      chem        cinematic   clay
comic       contacts    cryoem      diagram     dna         epitope
flatcartoon
ghost       goodsell    hero        hydrophobic illustrative interface
licorice    macro       neon        noir        nucleoprotein peptide
plddt       pocket      publication putty       qutemol     section
sketch      spacefill   topology    tube
```

Plus 25 palettes, 18 colourings, 9 lighting rigs, 19 backgrounds, 14 camera
presets and 13 output sizes. `viz_list` prints them all with descriptions.

## A few recipes

```
# binding site, labelled, ready for a referee to check
viz pocket
viz_label residues, byres (polymer within 4.2 of organic)

# one loop as the subject, everything else pushed back
viz publication
viz_focus resi 140-170, 0.8

# a 21-chain assembly, stood on its axis with a countable ring
viz goodsell

# AlphaFold model with the official confidence bands and their key
viz plddt

# protein as a see-through body, DNA with its bases as filled rings
viz nucleoprotein, rep=nucleic+ghost

# a 250 A ribosome: RNA one tone, protein another
viz goodsell, coloring=polymer

# a protein-protein interaction, at three scales
viz interface          # which surfaces meet
viz epitope            # what one partner actually touches
viz peptide            # the peptide in its groove, side chains and contacts
viz contacts           # every contacting residue named, bonds dashed

# a review-figure schematic, with chain breaks dotted
viz diagram

# these positions changed, everything else quiet
viz diagram, coloring=mono, palette=#E4E1D9
viz_highlight resi 113+117+193+203, #D6446B

# a remote homolog over its reference, with a magnified callout
viz_super model, reference
viz_inset resi 40-50, out.png, zoom=4

# multi-panel figure
viz_figure a.png/b.png/c.png, fig1.png, cols=3
```

**Mixing.** `rep` and `viz_mix` take `selection=representation` rules separated
by `/`. Rules apply in order and each claims only what no earlier rule took, so
`rest` means what is left:

```
viz_mix protein=ghost / nucleic=nucleic / ligand=ballstick
viz comic, rep=chain A=surface / chain B=cartoon / rest=lines
```

Selections are ordinary PyMOL selections plus the words `protein`, `nucleic`,
`dna`, `rna`, `ligand`, `ions`, `solvent`, `polymer`, `het` and `rest`.
`viz_paint` uses the same grammar for colour, and the rules become the key.

## Things worth knowing

**Custom colours use `/`, not commas.** PyMOL's parser eats commas inside an
argument, so a hex list is separated by `/` or `|`:

```
viz publication, palette=#5777A8/#B98E5C/#E69CED
```

**Reloading the same file keeps the camera.** `viz` cannot tell a reload from a
restyle, so pass `orient=1` when you know the subject is new. Loading a
*different* structure re-orients by itself.

**Style first, then frame.** `viz` rebuilds geometry, and a zoom computed for
the old representation will be wrong for the new one.

**`viz_script` is the honest one.** It writes the plain PyMOL that reproduces
the current look. If the plugin is doing something you cannot reproduce without
it, that file will show you.

## Where this is not there yet

Stated plainly, because a reviewer will find these anyway:

- Ribbon shading is a two-tone flip, not a value graded across the ribbon's
  width the way Jane Richardson draws it, and nothing draws the white cut-line
  she puts where two ribbons cross.
- Viewpoint is *computed*, not *chosen*. The n-fold axis where an assembly has
  one, the widest projection otherwise. `viz_pose` can rank candidate views and
  is off by default; neither is a decision about what a figure means.
- The ink-first styles (`illustrative`, `goodsell`, `architect`) fight a
  translucent body — legible, but roughly half the frame becomes ink.

## Licence

MIT. See [LICENSE](LICENSE).
