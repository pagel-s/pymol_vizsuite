# PyMOL Viz Suite

Turn a structure into a figure worth publishing, in one command.

`pymol_vizsuite.py` is a single-file PyMOL plugin. It ships complete visual
styles — illustrative Goodsell-style renders, journal cartoons, cel-shaded
posters, dark presentation heroes, binding-site close-ups — together with a
render pipeline that keeps ink outlines the same weight in print as on screen,
and post-processing for gradient backgrounds, glow, scale bars and multi-panel
figures.

## Install

**Plugin Manager** → *Install New Plugin* → *Choose file…* → pick
`pymol_vizsuite.py`. A **Viz Suite** entry appears in the Plugin menu.

Or, without installing:

```
run ~/.pymol/scripts/pymol_vizsuite.py
```

Requires open-source PyMOL 2.x/3.x. Post-processing (outline compositing,
gradients, glow, text, figures) uses `numpy` and the Qt build's `PyQt`; both
ship with standard PyMOL. Without them the suite still renders, single-pass.

## Thirty seconds

```
fetch 1aon, async=0
viz                                  # inspects the structure, picks a style
viz_render ~/figure.png, slide
```

`viz_gallery` renders every applicable style as a labelled contact sheet, so
you can choose a look by eye instead of by name.

## Start with an intention

Use these five short names for the common jobs. They are aliases for the
underlying complete styles, so `viz_script` always exports a reproducible
result.

| Intent | Command | Underlying style |
|---|---|---|
| Journal figure | `viz paper` | `publication` |
| Talk or cover image | `viz story` | `cinematic` |
| Molecular illustration | `viz illustration` | `illustrative` |
| Binding-site detail | `viz site` | `pocket` |
| AlphaFold confidence | `viz confidence` | `plddt` |

`viz_auto` remains the zero-decision choice when the structure should choose
the appropriate look from its contents.

The cinematic `story` intent is annotation-free by default so the molecule can
own a talk or cover image. Its information layer is always available on demand:
`viz_render story.png, legend=1, scalebar=20, name=Complex`.

## Commands

| Command | Does |
|---|---|
| `viz` | apply a style |
| `viz_auto` | inspect the structure and pick a style |
| `viz_render` | ray-trace to a file, with outlines and post-processing |
| `viz_gallery` | contact sheet of every style |
| `viz_figure` | compose rendered panels into a labelled figure |
| `viz_color` | recolour without touching the style |
| `viz_view` | camera presets |
| `viz_frame` | aspect-ratio presets |
| `viz_bg` | background presets |
| `viz_scalebar` | report the scale of the current view |
| `viz_turntable` | render a rotation as a PNG sequence |
| `viz_script` | export the equivalent `.pml` |
| `viz_reset` | back to PyMOL defaults |
| `viz_list` | list everything available |

Every command has full PyMOL help: `help viz`, `help viz_render`, …

## Styles

Run `viz_list styles` for descriptions.

**Illustrative** `illustrative` `goodsell` `comic` `blueprint` `sketch`
**Publication** `publication` `flatcartoon` `topology` `tube` `putty` `ghost`
`pocket` `cryoem` `clay`
**Presentation** `hero` `cinematic` `neon` `noir` `spacefill` `qutemol`
`macro` `architect` `section`
**Molecules** `chem` `licorice` `dna` `nucleoprotein`
**Interactions** `interface` `epitope` `peptide` `contacts`
**Schematic** `diagram`
**Analysis** `plddt` `hydrophobic` `charge`

```
viz illustrative                     # space-filling, flat colour, ink outline
viz goodsell, palette=pastel, blob=3.5
viz publication, coloring=ss         # journal cartoon by secondary structure
viz hero, palette=neon, view=hero, frame=slide
viz chem, organic                    # just the ligand, chemistry-journal style
viz pocket                           # binding-site close-up, framed for you
```

Anything a style decides can be overridden: `coloring`, `palette`, `rep`,
`light`, `outline`, `outline_color`, `ao`, `blob`, `background`, `fog`,
`hydrogens`, `waters`, `quality`, and the post-processing — `glow`,
`vignette`, `contrast`, `saturation`, `grain`, `posterize`, `sharpen`.

```
viz hero, glow=1.5, saturation=1.3
viz publication, posterize=5, contrast=1.2
viz goodsell, outline=0.008          # ink weight as a fraction of image width
```

9 lighting rigs (`flat` `soft` `studio` `glossy` `qutemol` `hard` `cel` `rim`
`clay`) and 15 representations (`viz_list` for both).

## Colouring

`chain` `chain-carbon` `entity` `spectrum` `spectrum-chain` `ss` `element`
`element-chain` `mono` `bfactor` `plddt` `hydrophobicity` `charge` `polymer`
`nucleic`
`pocket` `keep`

`viz_gaps` marks chain breaks, `viz_highlight` paints one residue set onto a
neutral fold, and `viz_super` superposes two structures as spectrum-over-grey.

For a protein-nucleic complex, `viz nucleoprotein` draws the protein as a
solid surface and the DNA or RNA as a ribbon with its bases and sugars as
filled rings. The protein half is a free choice — `rep=nucleic+cartoon`,
`nucleic+ghost`, `nucleic+spheres`, `nucleic+tube`, and so on for any
representation:

```
viz nucleoprotein, rep=nucleic+cartoon
```

Bases are flat plates seen edge-on from the side of a duplex and
hexagons seen down its axis — that is the geometry, not a setting.

`polymer` is the one that works at assembly scale: RNA in one tone, protein in
another. Beyond about eight chains no palette can keep them apart, and per-chain
colour on a ribosome destroys the RNA mass that gives it its shape.

```
viz_color ss
viz_color plddt                      # official AlphaFold confidence palette
viz_color chain, palette=#1B4965/#5FA8D3/#CAE9FF
```

25 built-in palettes (`viz_list palettes`), or your own `#hex` colours
separated by `/` — PyMOL treats commas as argument separators.

## Rendering

```
viz_render ~/fig.png, column, scalebar=20
viz_render ~/slide.png, slide, caption=GroEL/GroES chaperonin, label=A
viz_render ~/logo.png, square, transparent=1
viz_render ~/big.png, 4000x2500, dpi=600
```

Size presets: `thumb` `preview` `hd` `2k` `4k` `slide` `square` `column`
`dcolumn` `cover` `poster` `story` `print600`, or `WxH`.

`column` is 88 mm at 300 dpi (single journal column); `dcolumn` is 180 mm.

```
viz_render ~/fig.png, fit, width=2400
```

`fit` takes the canvas shape from the subject, so a wide complex is not boxed
into a square with half the page empty. `width` sets the long edge.

## Figures

```
viz_render ~/a.png, column, label=A
viz_render ~/b.png, column, label=B
viz_figure ~/a.png:apo ~/b.png:holo, ~/figure1.png, cols=2, title=Figure 1
```

Panels are separated by spaces or `|`; captions follow a colon. PyMOL treats
commas as argument separators, so they cannot separate panels.

## Two things worth knowing about the illustrative styles

**`assembly` colouring groups chains that are the same molecule.** A 21-chain
structure is rarely 21 different things — GroEL/GroES is two proteins in 14 and
7 copies. Chains are compared residue-by-residue (not by sequence string, since
copies routinely have different disordered stretches missing), grouped, then
shaded within one hue per group. Copies that form separate spatial assemblies —
the two stacked rings of a chaperonin — are given their own hue, because that
is what makes the architecture readable rather than just the composition.

**`illustrative` outlines subunits, not atoms.** PyMOL's edge detector fires on
normal discontinuities as well as depth, so in a space-filling model every atom
gets its own ring — the single thing that most separates a PyMOL render from a
published illustration. This style instead renders a depth buffer and draws a
line only where depth jumps by more than `ink_threshold` Ångström (10 by
default), plus one flat pass to find exact chain boundaries. Atoms inside a
subunit stay smooth; the subunit is outlined. It costs two extra ray passes.

## Two things worth knowing

**Outlines and occlusion are baked at render time.** The viewport shows a
preview; `viz_render` (or `ray`) produces the real image.

**Outline weight is a fraction of image width, not a pixel count.** PyMOL's
edge detector always draws a line about three pixels wide, so a single-pass
render gives bold outlines at 800 px and nearly invisible ones at 4000 px.
`viz_render` instead renders the outline as a separate low-resolution pass and
composites it, which keeps the same visual weight at any output size. The
weight is also scaled down automatically for thin geometry (a line that
flatters a chunky surface would swallow a cartoon ribbon whole) and for very
large structures.

## Framing

Camera presets: `best` `front` `back` `top` `bottom` `side` `iso` `hero`
`tilt` `tall` `core`.

`core` frames the compact bulk of the structure and lets disordered tails run
out of frame — the usual fix for an AlphaFold model whose floppy terminus is
half the bounding box. `viz_auto` switches to it by itself when it detects one.

Framing fits the structure's *projected* outline rather than PyMOL's bounding
sphere, so a flat or elongated structure fills the frame instead of floating in
the middle of it.

Scale bars, colour keys, subject names and captions are placed against the
rendered image: each is scored over the space it would actually occupy —
including the space the other annotations have already claimed — and slides
along the frame edge to wherever it covers least. A key re-reads its swatches
off the finished scene, so a chain that is hidden or faded is described as it
appears rather than as it was assigned.

## Order of operations

Apply the style first, then frame it — `viz` rebuilds geometry, and a zoom
computed for the old representation leaves the new one cropped:

```
viz goodsell                         # refits automatically
viz_frame slide
viz_view hero
```

Or do it in one call: `viz goodsell, frame=slide, view=hero`.

`viz` refits the zoom when the representation changes and leaves your camera
alone otherwise. `fit=1` forces a refit, `fit=0` suppresses it.

## Reproducing a look without the plugin

```
viz goodsell, palette=pastel
viz_script ~/goodsell.pml
```

`viz_script` writes the plain PyMOL commands the style applied.

## License

MIT.
