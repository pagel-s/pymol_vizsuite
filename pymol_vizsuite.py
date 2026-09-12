"""
PyMOL Viz Suite
===============

A visualization suite for PyMOL that turns structures into figures worth
publishing: illustrative Goodsell-style renders, journal cartoons, cel-shaded
posters, dark presentation heroes, multi-panel figures.

Install
-------
    Plugin > Plugin Manager > Install New Plugin > Choose file...

or, without installing:

    run /path/to/pymol_vizsuite.py

Quick start
-----------
    fetch 1aon, async=0
    viz                              # auto-detects a good look
    viz_render ~/fig.png, slide

    viz illustrative                 # Goodsell space-filling
    viz publication, coloring=ss     # journal cartoon
    viz hero, palette=neon           # dark presentation slide
    viz_gallery                      # contact sheet of every style

    viz_list                         # everything available

Commands
--------
    viz             apply a style
    viz_render      ray-trace to a file (bold outlines, post-processing)
    viz_auto        inspect the structure and pick a style
    viz_color       recolour without changing the style
    viz_view        camera presets
    viz_frame       aspect-ratio presets
    viz_bg          background presets
    viz_gallery     contact sheet of all styles
    viz_figure      compose rendered panels into a labelled figure
    viz_scalebar    add an Angstrom scale bar
    viz_script      export the equivalent .pml
    viz_reset       back to PyMOL defaults
    viz_list        list styles / palettes / colourings / presets

License: MIT
"""

from __future__ import annotations

import math
import os
import re

from pymol import cmd, util
from pymol import CmdException

__version__ = "2.20.0"

# ==========================================================================
# palettes
# ==========================================================================

PALETTES = {
    # pale enough that a thin dark contour is the dominant mark, which is what
    # makes a schematic read as a drawing rather than as a render
    "diagram": ["#B7D3C3", "#7E9CC2", "#E7E3DA", "#D8C6A4", "#C7B6CD",
                "#E6C9B4", "#A9C4D6", "#DFD2C2"],
    # --- distinct-hue sets, good for "colour by chain"
    "molstar": ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
                "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"],
    # Ordered on a lightness ladder: measured >=18/255 greyscale separation and
    # >=20 deuteranopia distance for the first six slots, which is the most any
    # categorical scheme can guarantee (see viz_check_palettes).
    "okabe": ["#053968", "#7C3F06", "#0C754F", "#C8548C", "#AB9315",
              "#64B7C9", "#DB8FFF", "#FFA194", "#B5F9B3", "#D6DFFF"],
    # validated as the strongest four-way categorical set measured
    "journal": ["#2666A6", "#E82828", "#1F9F9F", "#FF9900", "#6A4C93",
                "#118AB2", "#E07A5F", "#81B29A", "#3D405B", "#F2CC8F"],
    "nature": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
               "#8491B4", "#91D1C2", "#B24745", "#7E6148", "#B09C85"],
    "science": ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280",
                "#BB0021", "#5F559B", "#A20056", "#808180", "#1B1919"],
    "lancet": ["#00468B", "#ED0000", "#42B540", "#0099B4", "#925E9F",
               "#FDAF91", "#AD002A", "#ADB6B6", "#1B1919", "#7E6148"],
    "vivid": ["#12354B", "#8E3A31", "#1E6F72", "#6B4E8F", "#C0503F",
              "#2E86AB", "#4F8F3E", "#E09B3D", "#8FC6BC", "#B9BEC4"],

    # --- muted / illustrative
    # Measured with CIE76 dE after deuteranopia simulation: 18/255 greyscale
    # and dE 20 across the first four slots. The green that used to sit in slot
    # 3 collapsed onto the tan for deuteranopes (dE 9) however far apart their
    # lightness was, because red-green is exactly the axis they lose; a violet
    # of the same lightness separates instead. Holds to four groups, which is
    # what entity grouping actually produces.
    "goodsell": ["#5777A8", "#B98E5C", "#E69CED", "#FFB899", "#B2D1FF",
                 "#998268", "#B99CC7", "#E7BDAB", "#D1DEFF", "#FFF4CC"],
    "pastel": ["#A8C8E8", "#F5C6A5", "#F2A7A7", "#B7E1CD", "#D9C2E9",
               "#FDE79A", "#C9D6DF", "#E8C8D8", "#BFE3E0", "#E6D3A3"],
    "chalk": ["#8ECAE6", "#FFB703", "#90BE6D", "#F4978E", "#CDB4DB",
              "#83C5BE", "#FFD166", "#B8C0FF", "#F6BD60", "#A9DEF9"],
    "earth": ["#8C7A6B", "#A98467", "#6C584C", "#ADC178", "#DDE5B6",
              "#7F5539", "#B08968", "#9C6644", "#DDA15E", "#606C38"],

    "grey": ["#8A8A8A", "#A3A3A3", "#6E6E6E", "#B8B8B8", "#7C7C7C",
             "#9B9B9B", "#616161", "#C4C4C4", "#888888", "#A9A9A9"],
    "bone": ["#D5CCBE", "#BFB4A3", "#A69A87", "#8B8070", "#70665A",
             "#C8BEAF", "#B2A695", "#998D7B", "#7E7466", "#5C5349"],

    # --- moody / presentation
    "neon": ["#FF006E", "#3A86FF", "#FFBE0B", "#8338EC", "#06FFA5",
             "#FB5607", "#00F5D4", "#FF4D6D", "#4CC9F0", "#B5179E"],
    "cyber": ["#2E5FA3", "#D9743A", "#3FA796", "#C0506E", "#8A6BBF",
              "#D9B44A", "#5A7382", "#A8CBD9", "#7FA650", "#E3E7EA"],
    "ocean": ["#48CAE4", "#0077B6", "#90E0EF", "#023E8A", "#00B4D8",
              "#ADE8F4", "#0096C7", "#CAF0F8", "#03045E", "#5E60CE"],
    "sunset": ["#F94144", "#F8961E", "#F9C74F", "#90BE6D", "#577590",
               "#F3722C", "#43AA8B", "#4D908E", "#E76F51", "#6D597A"],
    "forest": ["#40916C", "#95D5B2", "#2D6A4F", "#74C69D", "#B7E4C7",
               "#1B4332", "#52B788", "#D8F3DC", "#3A5A40", "#588157"],
    "nord": ["#5E81AC", "#88C0D0", "#A3BE8C", "#EBCB8B", "#D08770",
             "#BF616A", "#B48EAD", "#8FBCBB", "#81A1C1", "#4C566A"],
    "jewel": ["#0B7A75", "#7B2D26", "#3D315B", "#D8B08C", "#708B75",
              "#444B6E", "#9AB87A", "#A44A3F", "#2E5266", "#6E8898"],


    # --- single-hue ramps, for "one protein, many domains"
    "mono-blue": ["#08306B", "#12508F", "#2171B5", "#4292C6", "#6BAED6",
                  "#9ECAE1", "#C6DBEF", "#DEEBF7", "#3A6EA5", "#5A8FC2"],
    "mono-teal": ["#003F3B", "#04635C", "#0A857B", "#17A398", "#3FC1B4",
                  "#79D6CC", "#A9E5DE", "#D2F2EE", "#0F6E66", "#2AB0A4"],
    "mono-red": ["#67000D", "#8B0A1A", "#B01B2E", "#CB3A45", "#E06B6B",
                 "#EE9A9A", "#F7C1C1", "#FDE3E3", "#A31621", "#D2544F"],
    "mono-violet": ["#3F007D", "#54278F", "#6A51A3", "#807DBA", "#9E9AC8",
                    "#BCBDDC", "#DADAEB", "#EFEDF5", "#5B2C8D", "#7A5BAF"],
}

# semantic colours reused by several colourings
SS_COLORS = {"H": "#C0453B", "S": "#EFC04A", "L": "#8E9499"}
PLDDT_COLORS = [(90.0, "#0053D6"), (70.0, "#65CBF3"),
                (50.0, "#FFDB13"), (-1e9, "#FF7D45")]

# Kyte & Doolittle hydropathy
KD_SCALE = {
    "ILE": 4.5, "VAL": 4.2, "LEU": 3.8, "PHE": 2.8, "CYS": 2.5, "MET": 1.9,
    "ALA": 1.8, "GLY": -0.4, "THR": -0.7, "SER": -0.8, "TRP": -0.9,
    "TYR": -1.3, "PRO": -1.6, "HIS": -3.2, "GLU": -3.5, "GLN": -3.5,
    "ASP": -3.5, "ASN": -3.5, "LYS": -3.9, "ARG": -4.5,
}
CHARGE_GROUPS = [
    ("acidic", "resn ASP+GLU", "#CE4B45"),
    ("basic", "resn LYS+ARG+HIS", "#3D6FA0"),
    ("polar", "resn SER+THR+ASN+GLN+CYS+TYR+TRP+GLY+PRO", "#C9C6BE"),
    ("apolar", "resn ALA+VAL+LEU+ILE+MET+PHE", "#D9A227"),
]

# Monotonic in lightness (98 -> 25) and colour-blind safe, unlike PyMOL's
# blue_red which passes through purple and is non-monotonic.
BFACTOR_RAMP = ["#FFF7EC", "#FDD49E", "#FC8D59", "#D7301F", "#7F0000"]

# Symmetric arms with the neutral midpoint lifted clear of the light background
HYDROPATHY_RAMP = ["#2C6E8F", "#8FBCCF", "#EDE7DA", "#DDA45A", "#9A5A1E"]

# ==========================================================================
# lighting rigs
# ==========================================================================

LIGHTING = {
    # form comes only from ambient occlusion: the illustrative look
    "flat": dict(ambient=1.0, direct=0.0, reflect=0.0, light_count=1,
                 specular=0.0, spec_reflect=0.0, shininess=10.0,
                 ray_shadows=0),
    # matte but three-dimensional; the workhorse for cartoons
    "soft": dict(ambient=0.42, direct=0.42, reflect=0.30, light_count=2,
                 specular=0.10, spec_reflect=0.06, shininess=30.0,
                 ray_shadows=0, light=[-0.35, -0.40, -1.0]),
    # multi-light studio setup, gentle sheen, no hard shadows
    "studio": dict(ambient=0.28, direct=0.35, reflect=0.55, light_count=4,
                   specular=0.22, spec_reflect=0.12, shininess=45.0,
                   ray_shadows=0, light=[-0.45, -0.35, -0.85],
                   light2=[0.60, -0.30, -0.35], light3=[0.10, 0.75, -0.45]),
    # glossy plastic / space-fill sheen
    "glossy": dict(ambient=0.20, direct=0.45, reflect=0.45, light_count=3,
                   specular=1.0, spec_reflect=0.35, shininess=55.0,
                   spec_power=200.0, ray_shadows=0),
    # QuteMol-like: many lights + decaying shadows fake global illumination
    "qutemol": dict(ambient=0.24, direct=0.10, reflect=1.30, light_count=8,
                    specular=0.22, spec_reflect=0.10, shininess=12.0,
                    ray_shadows=1, ray_shadow_decay_factor=0.14,
                    ray_shadow_decay_range=2.4),
    # single hard key light, deep shadows: noir
    "hard": dict(ambient=0.10, direct=0.80, reflect=0.12, light_count=2,
                 specular=0.30, spec_reflect=0.15, shininess=40.0,
                 ray_shadows=1, light=[-0.55, -0.45, -0.70]),
    # two-tone banding for cel shading
    "cel": dict(ambient=0.58, direct=0.42, reflect=0.0, light_count=1,
                specular=0.0, spec_reflect=0.0, shininess=10.0,
                ray_shadows=0),
    # dark scene, bright edge: presentation hero
    "rim": dict(ambient=0.18, direct=0.30, reflect=0.75, light_count=3,
                specular=0.55, spec_reflect=0.28, shininess=60.0,
                ray_shadows=0, light=[-0.70, -0.45, -0.45],
                light2=[0.85, 0.35, 0.55], light3=[0.10, -0.85, 0.30]),
    # unglazed clay / plaster
    "clay": dict(ambient=0.34, direct=0.40, reflect=0.34, light_count=3,
                 specular=0.02, spec_reflect=0.0, shininess=8.0,
                 ray_shadows=0, light=[-0.40, -0.50, -0.80],
                 light2=[0.55, 0.20, -0.30]),
}

# ==========================================================================
# render size / frame presets
# ==========================================================================

SIZES = {
    "thumb": (480, 480),
    "preview": (900, 900),
    "hd": (1920, 1080),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
    "slide": (3000, 1688),        # 16:9, 300 dpi at 10 in
    "square": (2400, 2400),
    "column": (1040, 1040),       # 88 mm at 300 dpi (single journal column)
    "dcolumn": (2126, 1400),      # 180 mm at 300 dpi (double column)
    "cover": (2480, 3300),        # A4 portrait at 300 dpi
    "poster": (4800, 3200),
    "story": (1080, 1920),        # 9:16 social / phone
    "print600": (2080, 2080),     # 88 mm at 600 dpi
}

FRAMES = {
    "square": 1.0,
    "slide": 16.0 / 9.0,
    "wide": 21.0 / 9.0,
    "photo": 3.0 / 2.0,
    "golden": 1.6180339887,
    "portrait": 4.0 / 5.0,
    "story": 9.0 / 16.0,
    "column": 1.0,
    "dcolumn": 2126.0 / 1400.0,
    "cover": 2480.0 / 3300.0,
}

# ==========================================================================
# background presets  (colour | ("linear", top, bottom) | ("radial", in, out))
# ==========================================================================

BACKGROUNDS = {
    "white": "#FFFFFF",
    "blush": "#FCF1EE",
    "cream": "#FBF7EF",
    "paper": "#F7F5F0",
    "ivory": "#FBF8F1",
    "light": "#EEF1F4",
    "black": "#000000",
    "ink": "#0B0E14",
    "slate": "#1B2027",
    "charcoal": "#16181D",
    "midnight": ("linear", "#101A33", "#03050C"),
    "deepspace": ("radial", "#1A2340", "#04060D"),
    "dusk": ("linear", "#2B2140", "#0C0A14"),
    "teal": ("linear", "#0D3B3E", "#041416"),
    "steel": ("linear", "#2C3440", "#12161C"),
    "cleanlight": ("linear", "#FFFFFF", "#E4E9EE"),
    "warmlight": ("radial", "#FFFDF8", "#E8DFD0"),
    "spotlight": ("radial", "#FFFFFF", "#C9D1D9"),
    "transparent": None,
}

# ==========================================================================
# style presets
# ==========================================================================
#   rep       : representation recipe
#   light     : lighting rig
#   ao        : (mode, scale, smooth) or None
#   outline   : line weight as a fraction of image width (0 = off)
#   ocolor    : outline colour
#   lineart   : draw contours only, no shaded fill
#   ink       : "edge"   PyMOL's own edge detector
#               "depth"  threshold the depth buffer in Angstrom
#               "tiered" silhouette, chain boundary and residue contour at
#                        three different line weights
#   ink_threshold : depth step in Angstrom that draws a line, for ink="depth"
#   edge      : (gain, depth, slope, disco) edge-detector character
#   focus     : "ligand" for a close-up on the bound ligand, "core" to frame
#               the compact bulk and let disordered tails leave the frame
#   ortho     : orthoscopic projection
#   blob      : solvent radius for surfaces
#   bg        : background preset name
#   palette   : default palette
#   coloring  : default colouring
#   fog       : 0..1 depth fade, 0 = off
#   set       : extra PyMOL settings
#   post      : post-processing chain

STYLES = {
    # ---------------------------------------------------------------- illustrative
    "illustrative": dict(
        desc="Space-filling atoms, flat colour, ambient occlusion and a "
             "depth-cued ink line that outlines subunits rather than every "
             "atom. The Goodsell illustration look.",
        rep="spheres", light="flat", ao=(1, 10.0, 10), outline=0.0030,
        ocolor="black", ortho=True, blob=1.4, bg="white",
        palette="goodsell", coloring="assembly", fog=0.0,
        ink="tiered", ink_threshold=10.0,
        set={}, post={"grade": {"contrast": 1.04}}),
    "goodsell": dict(
        desc="Blobby molecular surface per chain, pastel palette, soft occlusion, "
             "bold ink outline. Molecular-landscape illustration.",
        rep="surface", light="flat", ao=(1, 16.0, 18), outline=0.0045,
        ocolor="black", ortho=True, blob=3.0, bg="paper",
        palette="goodsell", coloring="assembly", fog=0.0,
        ink="tiered", ink_threshold=10.0,
        set={"surface_quality": 1}, post={"grade": {"contrast": 1.05}}),
    "comic": dict(
        desc="Cel-shaded poster art: banded colour, heavy ink line, flat "
             "background. Reads from across the room.",
        rep="cartoon", light="flat", ao=(1, 14.0, 25), outline=0.0060,
        ocolor="black", ortho=True, blob=1.4, bg="ivory",
        palette="journal", coloring="chain", fog=0.0,
        edge=(0.14, 1.6, 6.0, 1.4), flat_ribbon=True,
        set={"cartoon_discrete_colors": 1, "cartoon_fancy_helices": 1,
             # thin loops would be swallowed whole by a heavy ink line
             "cartoon_loop_radius": 0.35, "cartoon_tube_radius": 0.55,
             "cartoon_rect_width": 0.55, "cartoon_oval_width": 0.35},
        post={"posterize": 6, "grade": {"saturation": 1.18, "contrast": 1.06}}),
    "blueprint": dict(
        desc="Pure contour drawing, no fill. Line art for schematics and "
             "overlays.",
        rep="surface", light="flat", ao=None, outline=0.0050,
        ocolor="black", lineart=True, ortho=True, blob=2.2, bg="white",
        palette="grey", coloring="mono", fog=0.0,
        edge=(0.12, 0.45, 1.8, 1.0), set={}, post={}),
    "sketch": dict(
        desc="Fine pen-and-ink contours over a pale wash. Looks hand-drawn.",
        # no occlusion at all: shading would muddy the wash, and the contour
        # lines are what carry the form here
        rep="surface", light="flat", ao=None, outline=0.0060,
        ocolor="#141310", ink="tiered", ortho=True, blob=2.2, bg="ivory",
        palette="bone", coloring="mono", fog=0.0,
        edge=(0.10, 0.11, 0.7, 0.5),
        set={"surface_quality": 1},
        post={"grade": {"contrast": 1.02, "saturation": 0.45, "lift": 0.30},
              "grain": 0.012}),

    # ---------------------------------------------------------------- publication
    "publication": dict(
        desc="Clean journal cartoon: fancy helices, matte two-point light, "
             "white background, no outline. The safe choice for a paper.",
        rep="cartoon", light="soft", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="white",
        palette="journal", coloring="chain", fog=0.18,
        set={"cartoon_fancy_helices": 1, "cartoon_highlight_color": -1},
        post={"grade": {"contrast": 1.03}}),
    "flatcartoon": dict(
        desc="Flat vector-style cartoon with a thin ink line. Slide-friendly "
             "and prints perfectly.",
        rep="cartoon", light="flat", ao=(1, 18.0, 20), outline=0.0026,
        ocolor="grey15", ortho=True, blob=1.4, bg="paper",
        palette="molstar", coloring="chain", fog=0.0,
        set={"cartoon_fancy_helices": 1, "cartoon_discrete_colors": 1},
        post={}),
    "topology": dict(
        desc="Secondary-structure cartoon on white: helices, sheets and loops "
             "read instantly. For fold and topology figures.",
        rep="cartoon", light="soft", ao=None, outline=0.0022, ocolor="grey20",
        ortho=True, blob=1.4, bg="white",
        palette="molstar", coloring="ss", fog=0.0,
        set={"cartoon_fancy_helices": 1, "cartoon_flat_sheets": 1,
             "cartoon_discrete_colors": 1},
        post={}),
    "tube": dict(
        desc="Minimal smooth backbone tube. Elegant for large assemblies and "
             "rainbow chain traces.",
        rep="tube", light="studio", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="spectrum", fog=0.22,
        set={}, post={"grade": {"contrast": 1.04}}),
    "putty": dict(
        desc="B-factor sausage: thickness and colour follow flexibility. "
             "The standard way to show disorder.",
        rep="putty", light="soft", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="bfactor", fog=0.18, set={}, post={}),
    "ghost": dict(
        desc="Translucent neutral surface over a solid cartoon: shows shape "
             "and fold at the same time.",
        rep="cartoon+surface", light="soft", ao=None, outline=0.0,
        ocolor="black", ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="chain", fog=0.20,
        set={"transparency": 0.55, "two_sided_lighting": 1,
             "cartoon_fancy_helices": 1, "surface_quality": 1,
             "surface_color": "grey75"},
        post={}),
    "pocket": dict(
        desc="Binding-site close-up: ligand and contact side chains in sticks "
             "with polar contacts, framed looking into the pocket.",
        rep="pocket", light="studio", ao=(1, 12.0, 15), outline=0.0016,
        ocolor="grey25", ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="pocket", fog=0.10, focus="ligand",
        set={}, post={"grade": {"contrast": 1.04}}),
    "cryoem": dict(
        desc="Monochrome matte surface, soft occlusion. Looks like a density "
             "map or a grey EM reconstruction.",
        rep="surface", light="clay", ao=(1, 20.0, 18), outline=0.0,
        ocolor="black", ortho=True, blob=2.0, bg="light",
        palette="bone", coloring="mono", fog=0.10,
        set={"surface_quality": 1}, post={"grade": {"contrast": 1.06}}),
    "clay": dict(
        desc="Single-material clay render, soft shadowless light. Shape without "
             "colour distraction.",
        rep="surface", light="clay", ao=(1, 18.0, 20), outline=0.0,
        ocolor="black", ortho=False, blob=1.8, bg="cleanlight",
        palette="bone", coloring="mono", fog=0.12,
        set={"surface_quality": 1},
        post={"shadow": (0.0, 0.02, 0.03, 0.28), "grade": {"contrast": 1.05}}),

    # ---------------------------------------------------------------- hero / dark
    "hero": dict(
        desc="Dark gradient stage, saturated palette, rim light and bloom. "
             "Built for slides and pitch decks.",
        rep="auto", light="rim", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="midnight",
        palette="cyber", coloring="chain", fog=0.35, dof=0.25,
        set={"cartoon_fancy_helices": 1},
        post={"bloom": (0.62, 0.030, 0.50), "vignette": 0.28,
              "grade": {"contrast": 1.06, "saturation": 1.10}}),
    "neon": dict(
        desc="Black stage, electric palette, heavy glow. Maximum impact, "
             "minimum subtlety.",
        rep="auto", light="rim", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="ink",
        palette="neon", coloring="chain", fog=0.30,
        set={"cartoon_fancy_helices": 1},
        post={"bloom": (0.45, 0.045, 0.95), "vignette": 0.22,
              "grade": {"contrast": 1.05, "saturation": 1.25}}),
    "noir": dict(
        desc="One hard light, deep cast shadows, near-monochrome. Dramatic and "
             "sculptural.",
        rep="surface", light="hard", ao=(1, 16.0, 18), outline=0.0,
        ocolor="black", ortho=False, blob=1.8, bg="charcoal",
        palette="grey", coloring="mono", fog=0.32,
        set={"surface_quality": 1},
        post={"grade": {"contrast": 1.18, "saturation": 0.25},
              "vignette": 0.38}),
    "spacefill": dict(
        desc="Glossy CPK spheres with a studio sheen. The classic textbook "
             "space-filling model, upgraded.",
        rep="spheres", light="glossy", ao=(1, 20.0, 15), outline=0.0,
        ocolor="black", ortho=False, blob=1.4, bg="spotlight",
        palette="molstar", coloring="element", fog=0.18,
        set={}, post={"bloom": (0.85, 0.014, 0.28), "grade": {"contrast": 1.05}}),
    "qutemol": dict(
        desc="Soft global illumination on space-filling atoms, QuteMol style. "
             "Beautifully readable atomic detail.",
        rep="spheres", light="qutemol", ao=None, outline=0.0022,
        ocolor="grey10", ortho=True, blob=1.4, bg="white",
        palette="molstar", coloring="element", fog=0.0,
        set={}, post={"grade": {"contrast": 1.06}}),

    "macro": dict(
        desc="Extreme close-up with a shallow focal plane: atoms in focus at "
             "the centre, everything else falling away. For chemistry detail.",
        rep="detail", light="studio", ao=(1, 8.0, 12), outline=0.0026,
        ocolor="#1A1A1A", ortho=False, blob=1.4, bg="cleanlight",
        palette="grey", coloring="element", fog=0.0, focus="ligand",
        dof=0.75, set={"stick_radius": 0.16, "sphere_scale": 0.26,
                       "valence": 1},
        post={"grade": {"contrast": 1.06}}),
    "cinematic": dict(
        desc="Dark stage, shallow focus, rim light and bloom. A large assembly "
             "treated like a subject in a photograph rather than a specimen.",
        rep="auto", light="rim", ao=(1, 16.0, 15), outline=0.0,
        ocolor="black", ortho=False, blob=1.6, bg="deepspace",
        palette="cyber", coloring="assembly", fog=0.40, dof=0.42,
        # A cover or pitch image needs the molecule to own the whole frame.
        # `viz_render legend=1, scalebar=20, name=...` remains available when
        # the same look is used as a labelled figure.
        annotations={"legend": 0, "scalebar": 0, "name": 0},
        set={}, post={"bloom": (0.55, 0.032, 0.60), "vignette": 0.34,
                      "grade": {"contrast": 1.08, "saturation": 1.06}}),
    "interface": dict(
        desc="Two partners in two hues with the contact residues of both "
             "brought forward. The overview scale of a protein-protein "
             "interaction: which surfaces meet, and where.",
        rep="cartoon", light="soft", ao=(1, 12.0, 16), outline=0.0,
        ocolor="#2E2C28", ortho=True, blob=1.5, bg="paper",
        palette="molstar", coloring="chain", fog=0.10, interface=True,
        annotations={"legend": 0, "scalebar": 0, "name": 0},
        set={"surface_quality": 1, "two_sided_lighting": 1},
        post={"grade": {"contrast": 1.03}}),
    "epitope": dict(
        desc="One partner as a solid surface painted with the footprint of "
             "the other. The figure that "
             "answers 'what does it actually touch'.",
        rep="cartoon", light="soft", ao=(1, 14.0, 16), outline=0.0,
        ocolor="#2E2C28", ortho=True, blob=1.5, bg="paper",
        palette="molstar", coloring="chain", fog=0.10, interface="epitope",
        annotations={"legend": 0, "scalebar": 0, "name": 0},
        set={"surface_quality": 1}, post={"grade": {"contrast": 1.03}}),
    "peptide": dict(
        desc="A receptor as a quiet surface with a peptide lying in its "
             "groove, drawn thick with its side chains. The close scale of a "
             "binding event.",
        rep="cartoon", light="soft", ao=(1, 11.0, 14), outline=0.0,
        ocolor="#2E2C28", ortho=True, blob=1.4, bg="paper",
        palette="molstar", coloring="chain", fog=0.12, interface="peptide",
        annotations={"legend": 0, "scalebar": 0, "name": 0},
        set={"surface_quality": 1, "cartoon_side_chain_helper": 1,
             "stick_radius": 0.16},
        post={"grade": {"contrast": 1.03}}),
    "contacts": dict(
        desc="Residue-level close-up of an interface: the contacting side "
             "chains of both partners as sticks, named, with hydrogen bonds "
             "and salt bridges measured and dashed. The scale a referee asks "
             "for.",
        rep="cartoon", light="soft", ao=None, outline=0.0,
        ocolor="#3A3A38", ortho=True, blob=1.4, bg="paper",
        palette="molstar", coloring="chain", fog=0.06, interface="contacts",
        annotations={"legend": 0, "scalebar": 0, "name": 0},
        set={"cartoon_transparency": 0.55, "stick_radius": 0.14,
             "cartoon_side_chain_helper": 1, "dash_gap": 0.32,
             "dash_length": 0.30, "dash_radius": 0.035},
        post={}),
    "diagram": dict(
        desc="Schematic line drawing: helices as cylinders, thin loops, a "
             "translucent grey envelope behind and a chain break drawn as a "
             "dotted line. The idiom of a structural-biology review figure.",
        rep="cartoon+surface", light="flat", ao=None, outline=0.0016,
        ocolor="#4A4A46", ink="edge", ortho=True, blob=1.6, bg="paper",
        palette="diagram", coloring="chain", fog=0.0,
        edge=(0.16, 1.4, 5.0, 1.2), gaps=True,
        set={"cartoon_cylindrical_helices": 1, "cartoon_fancy_helices": 0,
             "cartoon_flat_sheets": 1, "cartoon_smooth_loops": 1,
             "cartoon_loop_radius": 0.16, "cartoon_transparency": 0.0,
             "transparency": 0.86, "surface_color": "grey80",
             "surface_quality": 1},
        post={"grade": {"contrast": 1.02}}),
    "architect": dict(
        desc="Helices as cylinders inside an inked contour, with a soft grey "
             "envelope behind. Reads like an architectural drawing of the fold.",
        rep="cartoon", light="flat", ao=(1, 13.0, 20), outline=0.0019,
        ocolor="#3A3A38", ink="tiered", ortho=True, blob=1.4, bg="paper",
        palette="goodsell", coloring="assembly", fog=0.0,
        set={"cartoon_cylindrical_helices": 1, "cartoon_fancy_helices": 0,
             "cartoon_flat_sheets": 1, "cartoon_smooth_loops": 1},
        post={"halo": (0.013, "#D5D0C6", 0.60),
              "grade": {"contrast": 1.03}}),
    "section": dict(
        desc="Sectioned solid: the front cut away to reveal an interior "
             "chamber or lumen, cut faces shaded as material.",
        rep="surface", light="soft", ao=(1, 15.0, 15), outline=0.0026,
        ocolor="#2A2A2A", ortho=True, blob=1.8, bg="paper",
        palette="goodsell", coloring="assembly", fog=0.0,
        set={"surface_quality": 1, "two_sided_lighting": 1,
             "ray_interior_color": "#C4A882"},
        post={"grade": {"contrast": 1.05}}),

    # ---------------------------------------------------------------- molecules
    "chem": dict(
        desc="Chemistry-journal ball-and-stick: element colours, thin ink line, "
             "white background. For ligands and small molecules.",
        rep="ballstick", light="soft", ao=None, outline=0.0022, ocolor="grey10",
        ortho=True, blob=1.4, bg="white",
        palette="grey", coloring="element", fog=0.0,
        set={"valence": 1, "stick_radius": 0.13, "sphere_scale": 0.22,
             "valence_mode": 1}, post={}),
    "licorice": dict(
        desc="Clean stick model, no spheres. Good for peptides, loops and "
             "chemical detail.",
        rep="sticks", light="studio", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="element", fog=0.15,
        set={"stick_radius": 0.16}, post={}),
    "nucleoprotein": dict(
        desc="Protein as a solid surface, DNA or RNA as a ribbon with its "
             "bases drawn as filled rings. For nucleosomes, polymerases, "
             "CRISPR complexes and ribosomes.",
        rep="nucleic+surface", light="soft", ao=(1, 12.0, 16), outline=0.0026,
        ocolor="#22201C", ortho=True, blob=1.5, bg="paper",
        palette="molstar", coloring="polymer", fog=0.10,
        set={"surface_quality": 1, "cartoon_ring_transparency": 0.0,
             "cartoon_nucleic_acid_color": "default"},
        post={"grade": {"contrast": 1.03}}),
    "dna": dict(
        desc="Nucleic-acid cartoon with base ladder and per-base colour. "
             "For DNA, RNA and protein-nucleic complexes.",
        rep="nucleic", light="soft", ao=None, outline=0.0020, ocolor="grey20",
        ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="nucleic", fog=0.18,
        set={"cartoon_ring_mode": 3, "cartoon_ring_finder": 1,
             "cartoon_nucleic_acid_mode": 4, "cartoon_ring_transparency": 0.0},
        post={}),

    # ---------------------------------------------------------------- analysis
    "plddt": dict(
        desc="AlphaFold confidence colouring on a smooth cartoon, official "
             "pLDDT palette.",
        rep="cartoon", light="soft", ao=None, outline=0.0, ocolor="black",
        ortho=False, blob=1.4, bg="white",
        palette="molstar", coloring="plddt", fog=0.18, focus="core",
        set={"cartoon_fancy_helices": 1, "cartoon_transparency": 0.0},
        post={}),
    "hydrophobic": dict(
        desc="Surface coloured by Kyte-Doolittle hydropathy: where the greasy "
             "patches are.",
        rep="surface", light="soft", ao=(1, 14.0, 18), outline=0.0,
        ocolor="black", ortho=False, blob=1.4, bg="light",
        palette="molstar", coloring="hydrophobicity", fog=0.12,
        set={"surface_quality": 1}, post={"grade": {"contrast": 1.05}}),
    "charge": dict(
        desc="Surface coloured by residue charge class: acidic, basic, polar, "
             "apolar.",
        rep="surface", light="soft", ao=(1, 14.0, 18), outline=0.0,
        ocolor="black", ortho=False, blob=1.4, bg="light",
        palette="molstar", coloring="charge", fog=0.12,
        set={"surface_quality": 1}, post={"grade": {"contrast": 1.05}}),
}

STYLE_GROUPS = [
    ("illustrative", ["illustrative", "goodsell", "comic", "blueprint", "sketch"]),
    ("publication", ["publication", "flatcartoon", "topology", "tube", "putty",
                     "ghost", "pocket", "cryoem", "clay"]),
    ("presentation", ["hero", "cinematic", "neon", "noir", "spacefill",
                      "qutemol", "macro", "architect", "section"]),
    ("molecules", ["chem", "licorice", "dna", "nucleoprotein"]),
    ("interactions", ["interface", "epitope", "peptide", "contacts"]),
    ("schematic", ["diagram"]),
    ("analysis", ["plddt", "hydrophobic", "charge"]),
]

# The complete catalogue is deliberately still available, but most figures start
# with one of these five intentions.  These are aliases rather than separate
# styles so a result is always reproducible with the underlying named style.
STYLE_ALIASES = {
    "paper": "publication",
    "story": "cinematic",
    "illustration": "illustrative",
    "site": "pocket",
    "confidence": "plddt",
}

COLORINGS = ("chain", "chain-carbon", "assembly", "entity", "polymer",
             "spectrum",
             "spectrum-chain",
             "ss", "element", "element-chain", "mono", "bfactor", "plddt",
             "hydrophobicity", "charge", "nucleic", "pocket", "keep")

REPS = ("auto", "cartoon", "surface", "ghost", "spheres", "sticks",
        "ballstick", "tube",
        "putty", "ribbon", "lines", "mesh", "dots", "cartoon+surface",
        "pocket", "detail", "nucleic")

# An ink line that flatters a chunky surface will swallow a thin ribbon whole,
# so the requested weight is scaled by how heavy the geometry is.
OUTLINE_REP_SCALE = {
    "surface": 1.0, "ghost": 0.5, "spheres": 1.0, "mesh": 0.6, "dots": 0.6,
    "cartoon+surface": 0.8, "cartoon": 0.42, "nucleic": 0.42, "putty": 0.45,
    "mix": 0.70,
    "tube": 0.40, "ribbon": 0.30, "pocket": 0.40, "sticks": 0.28,
    "ballstick": 0.32, "lines": 0.22,
}

# Space-filling models want pale carbons; stick models want dark ones.
CARBON_LIGHT = "#B9C0C9"
CARBON_DARK = "#4C525C"

# The single saturated accent reserved for ligands and cofactors, so the eye
# lands on the chemistry rather than hunting for it.
HET_ACCENT = "#A8321F"
HET_ACCENT_DARK = "#FF9E5C"

# selections used throughout
SEL_PROT = "polymer.protein"
SEL_NUC = "polymer.nucleic"
SEL_LIG = "(organic and not polymer)"
SEL_ION = "(inorganic and not solvent)"
SEL_WAT = "solvent"

# settings that change geometry and would otherwise leak from one style into
# the next (a carved surface staying carved, a putty staying fat, ...).
# Cleared at the start of every viz call so each style starts from the same
# place.
_STICKY = """
surface_carve_selection surface_carve_cutoff surface_carve_normal_cutoff
surface_cavity_mode surface_quality solvent_radius surface_smooth_edges
surface_mode
surface_color transparency transparency_mode cartoon_transparency
cartoon_ring_mode cartoon_ring_finder cartoon_ring_transparency
cartoon_nucleic_acid_mode cartoon_discrete_colors cartoon_highlight_color
cartoon_fancy_helices cartoon_flat_sheets cartoon_smooth_loops
cartoon_sampling cartoon_loop_quality cartoon_tube_quality
cartoon_loop_radius cartoon_tube_radius cartoon_dumbbell_radius
dash_radius dash_color dash_gap dash_length
cartoon_oval_quality cartoon_side_chain_helper cartoon_cylindrical_helices
sphere_scale stick_radius valence valence_mode two_sided_lighting
cartoon_loop_radius cartoon_tube_radius cartoon_rect_width cartoon_oval_width
""".split()

# every global setting the suite may touch, so that reset is exact
_TOUCHED = """
ray_trace_mode ray_trace_gain ray_trace_color ray_trace_disco_factor
ray_trace_depth_factor ray_trace_slope_factor ray_trace_fog ray_trace_fog_start
ray_interior_color ray_interior_mode ray_shadows ray_shadow_decay_factor
ray_shadow_decay_range ray_opaque_background ambient_occlusion_mode
ambient_occlusion_scale ambient_occlusion_smooth ambient direct reflect
light_count light light2 light3 light4 specular spec_reflect spec_power
shininess spec_count depth_cue fog fog_start antialias orthoscopic
field_of_view surface_quality solvent_radius surface_smooth_edges
surface_cavity_mode surface_carve_cutoff surface_carve_selection
surface_carve_normal_cutoff sphere_scale cartoon_discrete_colors
cartoon_highlight_color cartoon_sampling cartoon_fancy_helices
cartoon_fancy_sheets cartoon_flat_sheets cartoon_smooth_loops
cartoon_loop_quality cartoon_tube_quality cartoon_oval_quality
cartoon_side_chain_helper cartoon_transparency cartoon_ring_mode
cartoon_ring_finder cartoon_ring_transparency cartoon_nucleic_acid_mode
cartoon_putty_radius cartoon_putty_scale_min cartoon_putty_scale_max
cartoon_putty_transform transparency transparency_mode two_sided_lighting
hash_max stick_radius valence valence_mode label_size label_font_id
label_color label_outline_color label_position label_bg_color
label_bg_transparency label_bg_outline label_connector label_connector_mode
label_connector_color label_connector_width bg_gradient bg_rgb_top
bg_rgb_bottom mesh_width dot_density dot_radius nonbonded_size
dash_color dash_width dash_gap dash_length dash_round_ends
cartoon_dumbbell_length cartoon_dumbbell_radius cartoon_dumbbell_width
cartoon_loop_radius cartoon_tube_radius cartoon_rect_width cartoon_oval_width
surface_color
""".split()

# ==========================================================================
# small helpers
# ==========================================================================


def _hex2rgb(h):
    if isinstance(h, (list, tuple)):
        return tuple(float(x) for x in h[:3])
    h = str(h).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb2hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c * 255))))
                                   for c in rgb[:3])


def _mix(a, b, t):
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


def _lighter(rgb, t=0.30):
    return _mix(rgb, (1.0, 1.0, 1.0), t)


def _lum(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _b(v, default=False):
    """Coerce a PyMOL command-line argument to bool."""
    if v is None or v == "":
        return default
    if isinstance(v, str):
        return v.strip().lower() in ("1", "on", "yes", "true", "y", "t")
    return bool(v)


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default=0):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return default


def _s(v, default=""):
    if v is None:
        return default
    v = str(v).strip()
    return v or default


def _resolve(name, table, label, default=None):
    """Case-insensitive lookup with a helpful error."""
    key = _s(name).lower().replace("_", "-")
    if not key and default is not None:
        return default
    if key in table:
        return key
    alt = key.replace("-", "_")
    if alt in table:
        return alt
    close = [k for k in table if k.startswith(key[:3])] or list(table)
    # truncating at twelve alphabetically dropped surface, spheres and tube
    # from the representation list, which is most of what anyone wants
    names = sorted(close)
    shown = ", ".join(names) if len(names) <= 30 else \
        ", ".join(names[:30]) + ", ... (%d more)" % (len(names) - 30)
    raise CmdException("unknown %s '%s'. try: %s" % (label, name, shown))


def _palette(name):
    """A palette name, or a custom list of #hex colours.

    PyMOL's parser eats commas, so a custom list is separated by / or | or
    spaces: palette=#1B4965/#5FA8D3/#CAE9FF"""
    if isinstance(name, (list, tuple)):
        return [_hex2rgb(c) for c in name]
    txt = _s(name)
    if txt.startswith("#") or any(c in txt for c in "/|,"):
        parts = [p for p in re.split(r"[/|,\s]+", txt) if p]
        if parts and (len(parts) > 1 or parts[0].startswith("#")):
            return [_hex2rgb(p) for p in parts]
    return [_hex2rgb(h) for h in PALETTES[_resolve(txt, PALETTES, "palette",
                                                   "molstar")]]


def _color_name(spec):
    """Return a PyMOL colour name for a hex string, name, or rgb triple."""
    if isinstance(spec, (list, tuple)):
        rgb = tuple(float(x) for x in spec[:3])
    else:
        txt = _s(spec, "white")
        if not txt.startswith("#"):
            return txt
        rgb = _hex2rgb(txt)
    name = "viz_x%02x%02x%02x" % tuple(int(round(c * 255)) for c in rgb)
    cmd.set_color(name, list(rgb))
    return name


class _Rec:
    """Applies commands and records the equivalent .pml lines."""

    def __init__(self):
        self.lines = []
        self.enabled = True

    def note(self, text=""):
        self.lines.append(("# " + text) if text else "")

    def set(self, name, value, sel=""):
        if isinstance(value, (list, tuple)):
            value = "[%s]" % ", ".join("%.4f" % v for v in value)
            try:
                cmd.set(name, value, sel)
            except Exception:
                return
        else:
            try:
                cmd.set(name, value, sel)
            except Exception:
                return          # unknown setting on this PyMOL build
        self.lines.append("set %s, %s%s"
                          % (name, value, (", " + sel) if sel else ""))

    def unset(self, name, sel=""):
        try:
            cmd.unset(name, sel)
        except Exception:
            return
        self.lines.append("unset %s%s" % (name, (", " + sel) if sel else ""))

    def do(self, line, fn):
        fn()
        self.lines.append(line)

    def bg(self, color):
        name = _color_name(color)
        cmd.bg_color(name)
        self.lines.append("bg_color %s" % name)

    def hide(self, rep="everything", sel="all"):
        cmd.hide(rep, sel)
        self.lines.append("hide %s, %s" % (rep, sel))

    def show(self, rep, sel="all"):
        if not cmd.count_atoms(sel):
            return
        cmd.show(rep, sel)
        self.lines.append("show %s, %s" % (rep, sel))

    def set_color(self, name, rgb):
        cmd.set_color(name, list(rgb))
        self.lines.append("set_color %s, [%.4f, %.4f, %.4f]"
                          % (name, rgb[0], rgb[1], rgb[2]))

    def color(self, color, sel):
        if not cmd.count_atoms(sel):
            return
        cmd.color(color, sel)
        self.lines.append("color %s, %s" % (color, sel))

    def cartoon(self, kind, sel):
        if not cmd.count_atoms(sel):
            return
        cmd.cartoon(kind, sel)
        self.lines.append("cartoon %s, %s" % (kind, sel))

    def spectrum(self, expr, palette, sel, byres=1, minimum=None, maximum=None):
        if not cmd.count_atoms(sel):
            return
        kw = {"byres": byres}
        if minimum is not None:
            kw["minimum"] = minimum
        if maximum is not None:
            kw["maximum"] = maximum
        cmd.spectrum(expr, palette, sel, **kw)
        extra = "".join(", %s=%s" % (k, v) for k, v in kw.items())
        self.lines.append("spectrum %s, %s, %s%s" % (expr, palette, sel, extra))

    def rebuild(self):
        cmd.rebuild()
        self.lines.append("rebuild")


def _chain_keys(selection):
    """Ordered unique (object, chain) pairs inside *selection*."""
    keys, seen = [], set()

    def add(model, chain):
        k = (model, chain)
        if k not in seen:
            seen.add(k)
            keys.append(k)

    cmd.iterate(selection, "add(model, chain)", space={"add": add})
    return keys


def _sel_chain(selection, model, chain):
    return '(%s) and model %s and chain "%s"' % (selection, model, chain)


def _extent_span(selection):
    ext = cmd.get_extent(selection)
    return [ext[1][i] - ext[0][i] for i in range(3)]


def _visible(selection):
    """Restrict to atoms that are actually drawn.

    Framing must ignore hidden atoms: a handful of crystallographic waters
    scattered around a protein are invisible but still inside the bounding box,
    and fitting to them leaves the structure at half the size it should be."""
    sub = "(%s) and visible" % selection
    try:
        if cmd.count_atoms(sub):
            return sub
    except Exception:
        pass
    return selection


def _has(selection, sub):
    try:
        return cmd.count_atoms("(%s) and (%s)" % (selection, sub)) > 0
    except Exception:
        return False


def _count(selection, sub):
    try:
        return cmd.count_atoms("(%s) and (%s)" % (selection, sub))
    except Exception:
        return 0


def _survey(selection="all"):
    """Describe what is in *selection* so styles can adapt to it."""
    n = cmd.count_atoms(selection)
    if not n:
        raise CmdException("selection '%s' is empty" % selection)
    chains = _chain_keys("(%s) and polymer" % selection) or _chain_keys(selection)
    nres = cmd.count_atoms("(%s) and polymer and name CA+P" % selection)
    ext = cmd.get_extent(selection)
    span = max(ext[1][i] - ext[0][i] for i in range(3))
    bvals = []
    cmd.iterate("(%s) and name CA" % selection, "bvals.append(b)",
                space={"bvals": bvals})
    bmax = max(bvals) if bvals else 0.0
    bmin = min(bvals) if bvals else 0.0
    return {
        "atoms": n,
        "chains": len(chains),
        "residues": nres,
        "span": span,
        "protein": _count(selection, SEL_PROT),
        "nucleic": _count(selection, SEL_NUC),
        "ligand": _count(selection, SEL_LIG),
        "ion": _count(selection, SEL_ION),
        "water": _count(selection, SEL_WAT),
        "objects": len(cmd.get_object_list(selection) or []),
        "bmax": bmax,
        "bmin": bmin,
        # a pLDDT-looking model: b factors all inside 0..100 and no crystal water
        "plddt_like": bool(bvals) and 0.0 <= bmin and bmax <= 100.0
                      and _count(selection, SEL_WAT) == 0,
    }


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------

_LAST_SCRIPT = []
_LAST = {}          # last applied style options, used by viz_render / GUI
_LAST_GROUPS = []   # (hex, label, selection) per colour group, for the legend
_PINNED = {}        # choices the user made that a restyle must not discard

# ==========================================================================
# colouring
# ==========================================================================


def _group_sel(sel, members):
    return "(%s) and (%s)" % (sel, " or ".join(
        _sel_chain(sel, m, c) for m, c in members))


def _resolve_groups(groups, rep=""):
    """Re-read each key entry off the scene, so a swatch cannot misstate it.

    A swatch is written when the colour is assigned, but the picture is made
    later: `viz_focus` fades the context, a representation change can hide a
    chain entirely, and a key that still shows the original colour is then
    describing something the reader cannot see. Each entry is re-sampled from
    the atoms actually visible, and entries with nothing left are dropped.
    """
    out = []
    for entry in groups:
        if len(entry) < 3:
            out.append(tuple(entry)[:2])
            continue
        hexcol, label, gsel = entry
        # A cofactor sealed inside a chamber is "visible" in PyMOL's sense and
        # invisible to the reader. Under a surface or space-filling rep, having
        # no solvent-accessible area means no pixels, so it must not be keyed.
        if rep in ("surface", "mesh", "dots", "spheres", "cartoon+surface"):
            try:
                if not cmd.count_atoms("(%s) and polymer" % gsel) and \
                        cmd.get_area(gsel) < 5.0:
                    continue
            except Exception:
                pass
        try:
            seen = {}
            cmd.iterate("(%s) and visible" % gsel,
                        "d[color] = d.get(color, 0) + 1", space={"d": seen})
            if not seen:
                continue
            top = max(seen, key=seen.get)
            rgb = cmd.get_color_tuple(top)
            if rgb:
                hexcol = _rgb2hex(rgb)
        except Exception:
            pass
        out.append((hexcol, label))
    return out


def _color_chain_like(rec, sel, cols, tint):
    """Flat per-chain colour; *tint* lightens hetero atoms so carbon reads."""
    keys = _chain_keys(sel)
    if not keys:
        return
    del _LAST_GROUPS[:]
    for i, (model, ch) in enumerate(keys):
        rgb = cols[i % len(cols)]
        _LAST_GROUPS.append((_rgb2hex(rgb), ch,
                             _group_sel(sel, [(model, ch)])))
        base = "viz_c%d" % i
        rec.set_color(base, rgb)
        s = _sel_chain(sel, model, ch)
        if tint:
            light = "viz_c%dl" % i
            rec.set_color(light, _lighter(rgb, 0.34))
            rec.color(light, s)
            rec.color(base, s + " and (elem C or not polymer)")
        else:
            rec.color(base, s)


# A cartoon draws every assigned element, so a two-residue helix becomes a
# visible barrel and a lone sheet residue becomes an arrowhead pointing at
# nothing. Hand-drawn ribbons never show these; the illustrator silently drops
# them. Anything shorter than this many residues is demoted to loop.
SS_MIN_RUN = {"H": 4, "S": 3}


def _despeckle_ss(prot):
    """Demote secondary-structure elements too short to be real."""
    runs = []
    cmd.iterate("(%s) and name CA" % prot,
                "r.append((model, segi, chain, resv, ss))",
                space={"r": runs})
    drop = []
    i = 0
    while i < len(runs):
        ss = runs[i][4]
        j = i
        while (j + 1 < len(runs) and runs[j + 1][4] == ss
               and runs[j + 1][:3] == runs[i][:3]
               and runs[j + 1][3] == runs[j][3] + 1):
            j += 1
        if ss in SS_MIN_RUN and (j - i + 1) < SS_MIN_RUN[ss]:
            drop.extend(runs[i:j + 1])
        i = j + 1
    for model, segi, chain, resv, _ in drop:
        cmd.alter("%s and segi '%s' and chain '%s' and resi %d"
                  % (model, segi, chain, resv), "ss='L'")
    return len(drop)


def _refresh_ribbon_shade(sel="all"):
    """Re-decide the ribbon inner face after something recoloured the scene.

    The inner face is chosen from the colours on the ribbons, so any command
    that recolours after the style was applied leaves it describing colours
    that are gone - which is how a grey-and-rainbow superposition ended up
    with magenta undersides."""
    try:
        _ribbon_shade(_Rec(), sel, True)
    except Exception:
        try:
            cmd.set("cartoon_highlight_color", -1)
        except Exception:
            pass


def _ribbon_shade(rec, sel, shown):
    """Set the ribbon's inner face to a shadow of the ribbon's own colour.

    One fixed colour for every ribbon in the scene is what makes the inner
    face read as grey tape wrapped round a red helix, or as dirt inside a pale
    one. Taking the commonest ribbon colour and darkening it keeps the face
    reading as the shaded side of the same object."""
    if not shown:
        rec.set("cartoon_highlight_color", -1)
        return
    seen = {}
    try:
        cmd.iterate("(%s) and name CA and visible" % sel,
                    "d[color] = d.get(color, 0) + 1", space={"d": seen})
    except Exception:
        seen = {}
    rgb = None
    if seen:
        try:
            rgb = cmd.get_color_tuple(max(seen, key=seen.get))
        except Exception:
            rgb = None
    if not rgb:
        rgb = _hex2rgb(RIBBON_SHADE)
    # dark enough to read as the far side, light enough not to read as ink
    face = _mix(rgb, (0.0, 0.0, 0.0), 0.42)
    if _lum(face) < 0.16:
        face = _mix(rgb, (1.0, 1.0, 1.0), 0.30)
    rec.set_color("viz_ribbon_face", face)
    rec.set("cartoon_highlight_color", "viz_ribbon_face")


# Consecutive residues are ~3.8 A apart at the alpha carbon. Anything much
# beyond that between neighbours in sequence means residues are missing, not
# that the chain takes a long step.
CA_BREAK = 4.6


def _chain_breaks(sel):
    """CA pairs that flank a gap in the model.

    Both tests are needed: a numbering jump alone can be a renumbering with no
    gap in space, and a distance jump alone can be a genuine discontinuity the
    depositor numbered consecutively."""
    rows = []
    try:
        cmd.iterate_state(1, "(%s) and name CA and polymer" % sel,
                          "rows.append((model, segi, chain, resv, x, y, z))",
                          space={"rows": rows})
    except Exception:
        return []
    out = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if a[:3] != b[:3]:
            continue
        d = sum((p - q) ** 2 for p, q in zip(a[4:], b[4:])) ** 0.5
        if d <= CA_BREAK:
            continue
        if b[3] - a[3] <= 1 and d < CA_BREAK * 2:
            continue        # numbered consecutively and only slightly long
        out.append(('%s and segi "%s" and chain "%s" and resi %d and name CA'
                    % (a[0], a[1], a[2], a[3]),
                    '%s and segi "%s" and chain "%s" and resi %d and name CA'
                    % (b[0], b[1], b[2], b[3])))
    return out


def _ensure_ss(sel):
    """PyMOL leaves ss blank for many files; assign it if it is missing."""
    prot = "(%s) and %s" % (sel, SEL_PROT)
    if not cmd.count_atoms(prot):
        return
    if cmd.count_atoms("(%s) and ss H+S" % prot) == 0:
        cmd.dss(prot)
    try:
        if _despeckle_ss(prot):
            cmd.rebuild(prot)
    except Exception:
        pass


def _color_ss(rec, sel, cols):
    _ensure_ss(sel)
    order = [("H", _hex2rgb(SS_COLORS["H"])),
             ("S", _hex2rgb(SS_COLORS["S"])),
             ("L+''", _hex2rgb(SS_COLORS["L"]))]
    for i, (ss, rgb) in enumerate(order):
        name = "viz_ss%d" % i
        rec.set_color(name, rgb)
        rec.color(name, "(%s) and %s and ss %s" % (sel, SEL_PROT, ss))
    rec.set_color("viz_ss_other", _hex2rgb("#9FB3C8"))
    rec.color("viz_ss_other", "(%s) and not %s" % (sel, SEL_PROT))


def _color_plddt(rec, sel):
    """AlphaFold confidence bands. Uses the b-factor column."""
    for i, (cut, hexcol) in enumerate(PLDDT_COLORS):
        name = "viz_pl%d" % i
        rec.set_color(name, _hex2rgb(hexcol))
        if i == 0:
            expr = "b > %g" % cut
        else:
            expr = "b > %g and not b > %g" % (cut, PLDDT_COLORS[i - 1][0])
        rec.color(name, "(%s) and (%s)" % (sel, expr))


def _color_hydrophobicity(rec, sel):
    """Kyte-Doolittle, mapped onto a blue-to-orange ramp."""
    lo, hi = -4.5, 4.5
    stops = [_hex2rgb(c) for c in HYDROPATHY_RAMP]
    for resn, val in KD_SCALE.items():
        t = (val - lo) / (hi - lo) * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        rgb = _mix(stops[i], stops[i + 1], t - i)
        name = "viz_kd_%s" % resn.lower()
        rec.set_color(name, rgb)
        rec.color(name, "(%s) and resn %s" % (sel, resn))
    rec.set_color("viz_kd_other", _hex2rgb("#BFBBB2"))
    rec.color("viz_kd_other", "(%s) and not resn %s"
              % (sel, "+".join(sorted(KD_SCALE))))


def _color_charge(rec, sel):
    for i, (_, subsel, hexcol) in enumerate(CHARGE_GROUPS):
        name = "viz_q%d" % i
        rec.set_color(name, _hex2rgb(hexcol))
        rec.color(name, "(%s) and %s" % (sel, subsel))
    rec.set_color("viz_qother", _hex2rgb("#CFCFCF"))
    rec.color("viz_qother", "(%s) and not polymer.protein" % sel)


def _color_nucleic(rec, sel, cols):
    bases = [("DA+A", "#5A9BD4"), ("DT+T+U", "#E8944A"),
             ("DG+G", "#6BBF59"), ("DC+C", "#D66A6A")]
    for i, (resn, hexcol) in enumerate(bases):
        name = "viz_nt%d" % i
        rec.set_color(name, _hex2rgb(hexcol))
        rec.color(name, "(%s) and resn %s" % (sel, resn))
    if _has(sel, SEL_PROT):
        _color_chain_like(rec, "(%s) and %s" % (sel, SEL_PROT), cols, True)


# rRNA pale and coherent, proteins in one contrasting colour studded over it:
# the shape of a ribosome is the shape of its RNA, and per-chain colour across
# fifty chains destroys that mass into confetti.
POLYMER_COLORS = (("nucleic", "#C9B79A", "RNA"), ("protein", "#4E7CA1", "protein"))
# Where the protein is a surface and the nucleic is drawn as rings, the roles
# reverse: the body recedes and the chemistry carries the colour.
POLYMER_COLORS_RINGS = (("nucleic", "#3F72A8", "DNA/RNA"),
                        ("protein", "#CFC7B8", "protein"))


def _color_polymer(rec, sel, cols, rep=""):
    """Two tones: nucleic acid and protein.

    At assembly scale the useful question is not which chain but which kind of
    polymer, and a 50-chain complex has more chains than any palette can keep
    apart."""
    del _LAST_GROUPS[:]
    table = POLYMER_COLORS_RINGS if _s(rep).startswith("nucleic+") \
        else POLYMER_COLORS
    if _has(sel, SEL_NUC) and not _has(sel, "resn A+U+G+C+I"):
        table = tuple((k, c, "DNA" if k == "nucleic" else l)
                      for k, c, l in table)
    for i, (kind, hexcol, label) in enumerate(table):
        sub = "(%s) and polymer.%s" % (sel, kind)
        if not cmd.count_atoms(sub):
            continue
        name = "viz_pm%d" % i
        rec.set_color(name, _hex2rgb(hexcol))
        rec.color(name, sub)
        _LAST_GROUPS.append((hexcol, label, sub))
    other = "(%s) and not polymer" % sel
    if cmd.count_atoms(other):
        rec.set_color("viz_pm_het", _hex2rgb(HET_ACCENT))
        rec.color("viz_pm_het", other)
        _LAST_GROUPS.append((HET_ACCENT, _het_label(other), other))


def _color_pocket(rec, sel, cols, focus=""):
    """Grey protein, coloured ligand: the standard binding-site figure."""
    rec.set_color("viz_pk_prot", _hex2rgb("#A8B4C2"))
    rec.color("viz_pk_prot", "(%s) and polymer" % sel)
    lig = focus or "(%s) and %s" % (sel, SEL_LIG)
    if not cmd.count_atoms(lig):
        return
    near = "byres ((%s) and polymer within 4.5 of (%s))" % (sel, lig)
    if cmd.count_atoms(near):
        rec.set_color("viz_pk_near", _hex2rgb("#6E7C8C"))
        rec.color("viz_pk_near", "(%s) and elem C" % near)
    rec.set_color("viz_pk_lig", _hex2rgb("#F0A03C"))
    rec.color("viz_pk_lig", lig)
    rec.do("util.cnc('(%s) and not elem C')" % lig,
           lambda: util.cnc("(%s) and not elem C" % lig, _self=cmd))


def _entity_groups(sel):
    """Group polymer chains that are copies of the same molecule.

    A 21-chain assembly is not 21 different things: GroEL/GroES is two proteins
    in 14 and 7 copies. Giving every chain an unrelated colour hides that, so
    copies are grouped here and shaded within one hue instead.

    Chains are compared residue number by residue number rather than by
    sequence string, because copies of one protein routinely have different
    disordered stretches missing from the model - keying on the observed
    sequence splits them into spurious entities."""
    seqs = []
    for model, chain in _chain_keys("(%s) and polymer" % sel):
        res = {}
        cmd.iterate('(%s) and model %s and chain "%s" and guide'
                    % (sel, model, chain), "res[resv] = resn",
                    space={"res": res})
        if res:
            seqs.append(((model, chain), res))

    groups = []
    for key, res in seqs:
        for members, rep in groups:
            shared = set(rep) & set(res)
            if len(shared) >= 20 and \
                    sum(1 for r in shared if rep[r] == res[r]) >= 0.9 * len(shared):
                members.append(key)
                break
        else:
            groups.append(([key], res))
    return sorted((m for m, _ in groups), key=lambda v: (-len(v), v[0]))


# Offsets in CIELAB (dL, da, db), cycled within one entity so neighbouring
# copies stay countable. Goodsell's two greens measure dL -7, da -20, db +28:
# the separation is almost entirely chromatic, at near-constant lightness.
# That is not a stylistic choice — shading already swings lightness by 40-50
# L* across a curved subunit, so a lightness-only offset is buried inside it,
# while a chroma offset is orthogonal to shading and survives it.
# How consecutive copies within one entity differ, so a ring can be counted.
#
# Goodsell's two greens measure dL -7, da -20, db +28 in CIELAB. Applied as a
# vector in (a, b) that reads as a hue change and turns a tan into an olive:
# two entities rather than two copies, and the key stops matching the picture.
# In polar terms his pair is hue 140 and 133 degrees at chroma 39 and 73 - the
# same colour at two saturations. So the offset belongs on chroma at constant
# hue. Lightness alone will not serve either: shading already swings L* by
# 40-50 across a curved subunit and buries any identity offset inside its own
# modelling. Seven copies cannot be enumerated by two tones in any case; the
# black boundary between subunits does the counting, as it does in his rings.
_ALT_CHROMA = 26.0
_ALT_LIGHT = -6.0


def _shade(rgb, amount):
    if amount > 0:
        return _lighter(rgb, amount)
    if amount < 0:
        return _mix(rgb, (0.0, 0.0, 0.0), -amount)
    return rgb


def _alt(rgb, k):
    """Alternate a copy's colour so it can be told from the copy beside it.

    Chroma at constant hue: the copy stays recognisably the group's colour, so
    one swatch still describes the whole group honestly."""
    if not k:
        return rgb
    L, a, b = _lab(rgb)
    c = (a * a + b * b) ** 0.5
    if c < 6.0:
        # nothing to saturate; fall back to value
        return _lab2rgb((max(12.0, min(94.0, L + 16.0)), a, b))
    scale = (c + _ALT_CHROMA) / c
    return _lab2rgb((max(12.0, min(94.0, L + _ALT_LIGHT)), a * scale, b * scale))


def _spatial_split(members, sel):
    """Split copies of one molecule into spatial groups.

    Colouring purely by identity says "these 14 chains are the same protein"
    but hides that they form two stacked rings. Published illustrations give
    each ring its own hue, which is what makes the architecture readable, so
    look for a clean gap along the principal axis of the copies."""
    if len(members) < 4:
        return [members]
    try:
        import numpy
    except Exception:
        return [members]
    cents = []
    for model, chain in members:
        try:
            cents.append(cmd.centerofmass(
                _sel_chain("(%s) and polymer" % sel, model, chain)))
        except Exception:
            return [members]
    pts = numpy.array(cents, dtype=float)
    pts = pts - pts.mean(axis=0)
    try:
        _, vecs = numpy.linalg.eigh(numpy.cov(pts.T))
    except Exception:
        return [members]

    # Try every principal axis and keep the cleanest separation. Using only the
    # largest-variance axis is unreliable: for two stacked rings the in-plane
    # spread of the subunit centres rivals the ring spacing, so the split can
    # slice both rings in half instead of separating them.
    best = None
    for axis in range(3):
        proj = pts.dot(vecs[:, axis])
        order = numpy.argsort(proj)
        vals = proj[order]
        gaps = numpy.diff(vals)
        if len(gaps) < 3:
            continue
        cut = int(numpy.argmax(gaps))
        if min(cut + 1, len(vals) - cut - 1) < 2:
            continue
        gap = float(gaps[cut])
        left = float(vals[cut] - vals[0])
        right = float(vals[-1] - vals[cut + 1])
        # A real grouping means the gap dwarfs each group's own extent. The
        # bar has to be high: subunits evenly spaced around a single ring
        # project onto an in-plane axis with an uneven largest gap, which a
        # lenient test happily mistakes for two rings.
        quality = gap / max(left, right, 1e-6)
        if gap >= 4.0 and quality >= 2.5 and (best is None or quality > best[0]):
            best = (quality, order, cut)
    if best is None:
        return [members]
    _, order, cut = best
    return [[members[i] for i in order[:cut + 1]],
            [members[i] for i in order[cut + 1:]]]


def _chain_label(members):
    """Compact label for a colour group: 'A-N' for a run, 'A+C+E' otherwise."""
    # unsorted, this printed "E-A" and "K-H" for groups that are really A-G
    # and H-N: a range whose ends come from an arbitrary ordering is not a range
    ids = sorted(c for _, c in members)
    if len(ids) == 1:
        return ids[0]
    if len(ids) > 4:
        return "%s-%s (%d)" % (ids[0], ids[-1], len(ids))
    return "+".join(ids)


def _het_label(het):
    """Name the cofactor by its residue, so the accent means something.

    It is the most saturated colour in the picture and every reader's eye goes
    to it first; leaving it out of the key while listing the chains it sits in
    tells the reader the loudest thing on the page is not worth naming."""
    names = set()
    try:
        cmd.iterate(het, "n.add(resn)", space={"n": names})
    except Exception:
        pass
    names.discard("HOH")
    if not names:
        return "ligand"
    if len(names) == 1:
        return sorted(names)[0]
    if len(names) <= 3:
        return "+".join(sorted(names))
    return "ligands (%d)" % len(names)


def _distinct_accent(used):
    """The reserved accent, moved off any entity colour it collides with."""
    base = _hex2rgb(HET_ACCENT)
    if not used:
        return base
    for cand in (HET_ACCENT, "#1F6F8B", "#6A3D9A", "#0E7C5A", "#B8860B"):
        rgb = _hex2rgb(cand)
        if min(_delta_e(rgb, u) for u in used) >= 25.0:
            return rgb
    return base


def _color_assembly(rec, sel, cols, tint_het=True):
    groups = []
    for members in _entity_groups(sel):
        groups.extend(_spatial_split(members, sel))
    del _LAST_GROUPS[:]
    for gi, members in enumerate(groups):
        base = cols[gi % len(cols)]
        for ci, (model, chain) in enumerate(members):
            rgb = _alt(base, ci % 2) if len(members) > 1 else base
            if ci == 0:
                _LAST_GROUPS.append((_rgb2hex(base), _chain_label(members),
                                     _group_sel(sel, members)))
            name = "viz_a%d_%d" % (gi, ci)
            rec.set_color(name, rgb)
            s = _sel_chain("(%s) and polymer" % sel, model, chain)
            if tint_het:
                light = name + "l"
                rec.set_color(light, _lighter(rgb, 0.30))
                rec.color(light, s)
                rec.color(name, s + " and elem C")
            else:
                rec.color(name, s)
    het = "(%s) and not polymer" % sel
    if cmd.count_atoms(het):
        # the cofactor is the one saturated thing in the image, not palette
        # slot N+1 - but only if no entity already owns that hue
        accent = _distinct_accent([cols[i % len(cols)]
                                   for i in range(len(groups))])
        rec.set_color("viz_a_het", accent)
        rec.color("viz_a_het", het)
        _LAST_GROUPS.append((_rgb2hex(accent), _het_label(het), het))


def _bfactor_range(sel):
    """Clamp to the 5th-95th percentile so one hot loop cannot flatten the
    whole ramp."""
    vals = []
    cmd.iterate("(%s) and polymer and name CA+P+C1'" % sel,
                "vals.append(b)", space={"vals": vals})
    if len(vals) < 8:
        return None, None
    vals.sort()
    lo = vals[int(0.10 * (len(vals) - 1))]
    hi = vals[int(0.90 * (len(vals) - 1))]
    if hi - lo < 1e-6:
        return None, None
    return lo, hi


ELEMENT_COLORS = {"O": "#D94F3D", "N": "#3E6FB0", "S": "#D9A521",
                  "P": "#D9773A", "H": "#E8E8E8"}


def _color_element(rec, sel, cols, carbon=None):
    """CPK colours; carbons take the chain colour (or a fixed shade).

    Oxygen and nitrogen are toned down from PyMOL's saturated primaries, which
    vibrate against each other at space-filling density and moire in print."""
    if carbon is not None:
        rec.set_color("viz_carbon", carbon)
        rec.color("viz_carbon", "(%s) and elem C" % sel)
    else:
        keys = _chain_keys(sel)
        for i, (model, ch) in enumerate(keys):
            name = "viz_ec%d" % i
            rec.set_color(name, cols[i % len(cols)])
            rec.color(name, _sel_chain(sel, model, ch) + " and elem C")
    rec.do("util.cnc('(%s) and not elem C')" % sel,
           lambda: util.cnc("(%s) and not elem C" % sel, _self=cmd))
    for elem, hexcol in ELEMENT_COLORS.items():
        name = "viz_el_%s" % elem
        rec.set_color(name, _hex2rgb(hexcol))
        rec.color(name, "(%s) and elem %s" % (sel, elem))


HET_CPK_OK = ("chain", "chain-carbon", "entity", "spectrum", "spectrum-chain",
              "ss", "mono", "bfactor", "plddt")

# Colourings that encode a measured quantity. Their colours must survive the
# rendering pipeline unchanged or the reader cannot map colour back to value.
DATA_COLORINGS = ("plddt", "bfactor", "hydrophobicity", "charge")


def _color_het_cpk(rec, sel, dark=False):
    """Ligands and cofactors get the one saturated accent in the image.

    An element-grey haem in a coloured cartoon reads as dirt, not as the thing
    the whole figure is about. A warm accent puts the eye on it immediately,
    while the surrounding protein keeps the muted palette."""
    het = "(%s) and (%s or %s)" % (sel, SEL_LIG, SEL_ION)
    if not cmd.count_atoms(het):
        return
    accent = _hex2rgb(HET_ACCENT_DARK if dark else HET_ACCENT)
    rec.set_color("viz_het_c", accent)
    rec.color("viz_het_c", het + " and elem C")
    if _LAST_GROUPS:
        _LAST_GROUPS.append((_rgb2hex(accent), _het_label(het),
                             het + " and elem C"))
    rec.do("util.cnc('%s and not elem C')" % het,
           lambda: util.cnc("%s and not elem C" % het, _self=cmd))


def _apply_coloring(rec, sel, coloring, palette, het_cpk=False, dark=False,
                    pale_carbon=False, focus="", rep=""):
    coloring = _resolve(coloring, dict.fromkeys(COLORINGS), "coloring", "chain")
    if coloring == "keep":
        return coloring
    cols = _palette(palette)

    if coloring == "mono":
        rec.set_color("viz_mono", cols[0])
        rec.color("viz_mono", "(%s)" % sel)
    elif coloring == "chain":
        _color_chain_like(rec, sel, cols, False)
    elif coloring == "chain-carbon":
        _color_chain_like(rec, sel, cols, True)
    elif coloring == "assembly":
        _color_assembly(rec, sel, cols, tint_het=True)
    elif coloring == "entity":
        for i, obj in enumerate(cmd.get_object_list(sel) or []):
            rec.set_color("viz_e%d" % i, cols[i % len(cols)])
            rec.color("viz_e%d" % i, "(%s) and model %s" % (sel, obj))
    elif coloring == "spectrum":
        rec.spectrum("count", "rainbow", "(%s) and polymer" % sel)
        if _has(sel, "not polymer"):
            _color_element(rec, "(%s) and not polymer" % sel, cols,
                           _hex2rgb("#9AA0A6"))
    elif coloring == "spectrum-chain":
        for model, ch in _chain_keys("(%s) and polymer" % sel):
            rec.spectrum("count", "rainbow",
                         _sel_chain("(%s) and polymer" % sel, model, ch))
    elif coloring == "ss":
        _color_ss(rec, sel, cols)
    elif coloring == "element":
        _color_element(rec, sel, cols,
                       _hex2rgb(CARBON_LIGHT if pale_carbon else CARBON_DARK))
    elif coloring == "element-chain":
        _color_element(rec, sel, cols, None)
    elif coloring == "bfactor":
        # PyMOL's blue_red runs through purple and is not monotonic in
        # lightness, so it neither prints nor survives colour-blindness
        lo, hi = _bfactor_range(sel)
        names = []
        for i, hexcol in enumerate(BFACTOR_RAMP):
            name = "viz_bf%d" % i
            rec.set_color(name, _hex2rgb(hexcol))
            names.append(name)
        rec.spectrum("b", " ".join(names), "(%s) and polymer" % sel,
                     minimum=lo, maximum=hi)
    elif coloring == "plddt":
        _color_plddt(rec, sel)
    elif coloring == "hydrophobicity":
        _color_hydrophobicity(rec, sel)
    elif coloring == "charge":
        _color_charge(rec, sel)
    elif coloring == "polymer":
        _color_polymer(rec, sel, cols, rep=rep)
    elif coloring == "nucleic":
        _color_nucleic(rec, sel, cols)
    elif coloring == "pocket":
        _color_pocket(rec, sel, cols, focus=focus)
    if het_cpk and coloring in HET_CPK_OK:
        _color_het_cpk(rec, sel, dark=dark)
    return coloring


# ==========================================================================
# representations
# ==========================================================================


def _residue_count(selection):
    n = [0]

    def bump():
        n[0] += 1
    try:
        cmd.iterate("(%s) and guide" % selection, "bump()", space={"bump": bump})
    except Exception:
        return 0
    return n[0]


def _focus_selection(sel):
    """The most interesting bound thing in *sel*, for close-up styles.

    Real entries make this awkward: a ligand may be one hetero residue, or a
    cofactor plus its tail, or - as in many protease complexes - a peptide-like
    inhibitor that the PDB stores as its own polymer chain. So look for hetero
    groups first, grow them within their own chain, and fall back to a short
    polymer chain when there is no conventional ligand at all."""
    for sub in (SEL_LIG, SEL_ION):
        cand = "(%s) and %s" % (sel, sub)
        if not cmd.count_atoms(cand):
            continue
        groups = {}

        def add(chain, resi, resn, model):
            key = (model, chain, resi, resn)
            groups[key] = groups.get(key, 0) + 1

        cmd.iterate(cand, "add(chain, resi, resn, model)", space={"add": add})
        if not groups:
            continue
        model, chain, resi, resn = max(groups, key=lambda k: groups[k])
        seed = '(%s) and model %s and chain "%s" and resi %s and resn %s' \
            % (sel, model, chain, resi, resn)
        # a ligand and its covalently attached parts live in the same chain
        grown = ('byres ((%s) and model %s and chain "%s" and not %s '
                 'within 5.0 of (%s))' % (sel, model, chain, SEL_WAT, seed))
        if 0 < _residue_count(grown) <= 30:
            return grown
        return seed

    # no hetero group: a short polymer chain is probably the bound peptide
    chains = {}
    for model, chain in _chain_keys("(%s) and polymer" % sel):
        s = _sel_chain("(%s) and polymer" % sel, model, chain)
        chains[(model, chain)] = _residue_count(s)
    if len(chains) >= 2:
        (model, chain), n = min(chains.items(), key=lambda kv: kv[1])
        if n <= 30 and n < 0.5 * max(chains.values()):
            return _sel_chain("(%s) and polymer" % sel, model, chain)
    return ""


def _polar_contacts(rec, a, b, name="viz_contacts"):
    """Dashed hydrogen bonds between two selections, styled to read in print."""
    cmd.delete(name)
    try:
        n = cmd.distance(name, "(%s)" % a, "(%s)" % b, mode=2)
    except Exception:
        return 0
    if not n:
        cmd.delete(name)
        return 0
    for key, val in (("dash_color", "grey30"), ("dash_width", 2.4),
                     ("dash_gap", 0.35), ("dash_length", 0.32),
                     ("dash_round_ends", 0), ("label_size", 0)):
        rec.set(key, val, name)
    cmd.hide("labels", name)
    rec.lines.append("distance %s, (%s), (%s), mode=2" % (name, a, b))
    return n


# Richardson shades each ribbon across its width, dark at one edge and pale at
# the other, which is the whole reason her strands read as twisted surfaces
# crossing in depth. PyMOL's inner-face colour is the native way to get it.
RIBBON_SHADE = "#9A9488"


def _cartoon_quality(rec, fine=True):
    q = 16 if fine else 8
    rec.set("cartoon_sampling", q)
    rec.set("cartoon_loop_quality", 12 if fine else 6)
    rec.set("cartoon_tube_quality", 12 if fine else 6)
    rec.set("cartoon_oval_quality", 12 if fine else 6)
    rec.set("cartoon_smooth_loops", 1)


def _show_het(rec, sel, sticks=True, ion_scale=0.45):
    """Ligands as sticks, ions as small spheres: sensible for every style."""
    lig = "(%s) and %s" % (sel, SEL_LIG)
    ion = "(%s) and %s" % (sel, SEL_ION)
    if sticks:
        rec.show("sticks", lig)
    if cmd.count_atoms(ion):
        rec.show("spheres", ion)
        rec.set("sphere_scale", ion_scale, ion)


def _apply_rep(rec, sel, rep, blob=1.4, hydrogens=False, waters=False,
               fine=True, sphere_scale=1.0, focus="", shade_ribbon=True):
    # "nucleic+X" means: nucleic acid as a ring cartoon, protein as X. The
    # protein half is resolved and drawn by this same function, so every
    # representation is available on it without enumerating the pairs.
    # a full mix spec: "chain A=surface / rest=cartoon". Handled here so it
    # composes with every style rather than needing its own command.
    if "=" in _s(rep):
        rules = _spec_selections(_parse_spec(rep, "rep"), sel)
        if rules:
            rec.hide("everything", "(%s)" % sel)
            for sub, sub_rep, _ in rules:
                _apply_rep(rec, sub, sub_rep, blob=blob, hydrogens=hydrogens,
                           waters=waters, fine=fine, sphere_scale=sphere_scale,
                           shade_ribbon=shade_ribbon)
            return "mix"

    partner = ""
    if _s(rep).lower().startswith("nucleic+"):
        partner = _resolve(_s(rep).split("+", 1)[1], dict.fromkeys(REPS),
                           "representation", "surface")
        rep = "nucleic+" + partner
    else:
        rep = _resolve(rep, dict.fromkeys(REPS), "representation", "auto")
    poly = "(%s) and polymer" % sel
    if rep == "auto":
        if not cmd.count_atoms(poly):
            rep = "ballstick"
        elif cmd.count_atoms("(%s) and %s" % (sel, SEL_NUC)) > \
                cmd.count_atoms("(%s) and %s" % (sel, SEL_PROT)):
            rep = "nucleic"
        elif cmd.count_atoms(sel) > 35000:
            # a cartoon of a whole ribosome is spaghetti; shape reads better
            rep = "surface"
        else:
            rep = "cartoon"

    if rep in ("cartoon", "cartoon+surface", "tube", "putty", "ribbon",
               "nucleic", "mesh", "pocket"):
        _ensure_ss(sel)
        # The inner face is one global colour, so on a flat cel style it reads
        # as grey tape wrapped round every helix and wipes out chain identity.
        # Worth it where shading carries depth, not where flat fill does.
        if not shade_ribbon:
            rec.set("cartoon_highlight_color", -1)

    rec.hide("everything", "(%s)" % sel)

    if rep == "spheres":
        rec.set("sphere_scale", sphere_scale)
        rec.show("spheres", "(%s)" % sel)

    elif rep == "ghost":
        # a body you can see through: shape without hiding what is inside it,
        # which is the whole point of pairing it with a nucleic acid
        rec.set("solvent_radius", blob)
        rec.set("transparency", 0.55)
        rec.set("two_sided_lighting", 1)
        rec.show("surface", poly if cmd.count_atoms(poly) else "(%s)" % sel)
        _show_het(rec, sel)

    elif rep == "surface":
        rec.set("solvent_radius", blob)
        rec.set("surface_smooth_edges", 1)
        rec.show("surface", "(%s) and not %s" % (sel, SEL_WAT))

    elif rep == "mesh":
        rec.set("solvent_radius", blob)
        rec.show("mesh", "(%s) and not %s" % (sel, SEL_WAT))
        rec.show("cartoon", poly)
        _cartoon_quality(rec, fine)

    elif rep == "dots":
        rec.set("solvent_radius", blob)
        rec.show("dots", "(%s) and not %s" % (sel, SEL_WAT))

    elif rep == "cartoon":
        _cartoon_quality(rec, fine)
        if cmd.count_atoms("(%s) and %s" % (sel, SEL_NUC)):
            rec.set("cartoon_nucleic_acid_mode", 1)
            rec.set("cartoon_ladder_mode", 1)
            rec.set("cartoon_ladder_radius", 0.35)
            rec.set("cartoon_ring_mode", 3)
            rec.set("cartoon_ring_finder", 1)
        rec.cartoon("automatic", poly)
        rec.show("cartoon", poly)
        _show_het(rec, sel)

    elif rep == "cartoon+surface":
        _cartoon_quality(rec, fine)
        rec.set("solvent_radius", blob)
        rec.cartoon("automatic", poly)
        rec.show("cartoon", poly)
        rec.show("surface", "(%s) and polymer" % sel)
        _show_het(rec, sel)

    elif rep == "tube":
        _cartoon_quality(rec, fine)
        rec.cartoon("tube", poly)
        rec.show("cartoon", poly)
        _show_het(rec, sel)

    elif rep == "putty":
        _cartoon_quality(rec, fine)
        rec.cartoon("putty", poly)
        rec.show("cartoon", poly)
        _show_het(rec, sel)

    elif rep == "ribbon":
        rec.show("ribbon", poly)
        _show_het(rec, sel)

    elif rep == "lines":
        rec.show("lines", "(%s)" % sel)

    elif rep == "sticks":
        rec.show("sticks", "(%s) and not %s" % (sel, SEL_WAT))
        if cmd.count_atoms("(%s) and %s" % (sel, SEL_ION)):
            rec.show("spheres", "(%s) and %s" % (sel, SEL_ION))
            rec.set("sphere_scale", 0.45, "(%s) and %s" % (sel, SEL_ION))

    elif rep == "ballstick":
        rec.show("sticks", "(%s) and not %s" % (sel, SEL_WAT))
        rec.show("spheres", "(%s) and not %s" % (sel, SEL_WAT))
        rec.set("sphere_scale", 0.22)

    elif partner:
        # Two polymers, two idioms: the bases are chemistry and want their
        # rings drawn, the protein is a body and wants whatever suits it.
        # Drawing both as cartoon buries the nucleic in ribbon; drawing both
        # as surface loses the bases entirely.
        _cartoon_quality(rec, fine)
        nuc = "(%s) and %s" % (sel, SEL_NUC)
        prot = "(%s) and %s" % (sel, SEL_PROT)
        if cmd.count_atoms(prot):
            _apply_rep(rec, prot, partner, blob=blob, hydrogens=hydrogens,
                       waters=waters, fine=fine, sphere_scale=sphere_scale,
                       shade_ribbon=shade_ribbon)
        if cmd.count_atoms(nuc):
            rec.set("cartoon_ring_mode", 3)
            rec.set("cartoon_ring_finder", 1)
            rec.set("cartoon_nucleic_acid_mode", 1)
            rec.set("cartoon_ladder_mode", 1)
            rec.set("cartoon_ladder_radius", 0.35)
            rec.cartoon("automatic", nuc)
            rec.show("cartoon", nuc)
        _show_het(rec, sel)

    elif rep == "nucleic":
        _cartoon_quality(rec, fine)
        rec.cartoon("automatic", poly)
        rec.show("cartoon", poly)
        # mode 4 leaves the base stubs hanging in mid-air; mode 1 draws a
        # ladder whose rungs actually join the two strands
        rec.set("cartoon_ring_mode", 3)
        rec.set("cartoon_ring_finder", 1)
        rec.set("cartoon_nucleic_acid_mode", 1)
        rec.set("cartoon_ladder_mode", 1)
        rec.set("cartoon_ladder_radius", 0.35)
        _show_het(rec, sel)

    elif rep == "detail":
        lig = focus or _focus_selection(sel)
        if not lig:
            lig = "(%s) and %s" % (sel, SEL_LIG)
        if not cmd.count_atoms(lig):
            return _apply_rep(rec, sel, "ballstick", blob, hydrogens, waters,
                              fine, sphere_scale)
        near = "byres ((%s) and polymer within 6 of (%s))" % (sel, lig)
        rec.set("stick_radius", 0.10)
        if cmd.count_atoms(near):
            rec.show("sticks", "(%s) and not hydro" % near)
        rec.show("sticks", lig)
        rec.set("stick_radius", 0.17, lig)
        rec.show("spheres", "(%s) and not hydro" % lig)
        rec.set("sphere_scale", 0.24, lig)

    elif rep == "pocket":
        lig = focus or _focus_selection(sel)
        if not lig:
            return _apply_rep(rec, sel, "cartoon+surface", blob, hydrogens,
                              waters, fine, sphere_scale)
        # Contact residues are shown as whole residues, not side chains only:
        # a sidechain-only selection has no bond to the backbone, so it renders
        # as fragments floating in space. cartoon_side_chain_helper then hides
        # the cartoon exactly where sticks replace it, so nothing is drawn twice.
        shell = "byres ((%s) and polymer within 16 of (%s))" % (sel, lig)
        near = "byres ((%s) and polymer within 4.5 of (%s))" % (sel, lig)
        _cartoon_quality(rec, fine)
        rec.set("cartoon_side_chain_helper", 1)
        rec.set("cartoon_transparency", 0.0)
        rec.set("stick_radius", 0.13)
        rec.cartoon("automatic", shell)
        rec.show("cartoon", shell)
        if cmd.count_atoms(near):
            rec.show("sticks", "(%s) and not hydro" % near)
        # the ligand is the subject: heavier sticks, and spheres so single
        # atoms such as a bound metal do not vanish
        rec.show("sticks", lig)
        rec.set("stick_radius", 0.22, lig)
        rec.show("spheres", "(%s) and not hydro" % lig)
        rec.set("sphere_scale", 0.16, lig)
        if cmd.count_atoms(near):
            _polar_contacts(rec, lig, near)

    if not hydrogens:
        rec.hide("everything", "(%s) and hydro and not (neighbor (elem N+O+S))"
                 % sel)
    if not waters:
        rec.hide("everything", "(%s) and %s" % (sel, SEL_WAT))
    return rep


# ==========================================================================
# image backend: Qt for PNG i/o and text, numpy for pixel maths
# ==========================================================================

_IMG = {"checked": False, "ok": False, "why": ""}


def _img_backend():
    """Import Qt + numpy lazily; report why post-processing is unavailable."""
    if _IMG["checked"]:
        return _IMG["ok"]
    _IMG["checked"] = True
    try:
        import numpy                                    # noqa: F401
        from pymol.Qt import QtCore, QtGui              # noqa: F401
    except Exception as exc:
        _IMG["why"] = "needs numpy and PyMOL's Qt build (%s)" % exc
        return False
    try:
        if QtGui.QGuiApplication.instance() is None:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            _IMG["app"] = QtGui.QGuiApplication([])
    except Exception as exc:
        _IMG["why"] = "could not start a Qt application (%s)" % exc
        return False
    _IMG["np"] = numpy
    _IMG["QtGui"] = QtGui
    _IMG["QtCore"] = QtCore
    _IMG["fmt"] = getattr(QtGui.QImage, "Format_RGBA8888", None) or \
        QtGui.QImage.Format.Format_RGBA8888
    _IMG["ok"] = True
    return True


def _np():
    return _IMG["np"]


def _qimage_to_np(img):
    np = _np()
    img = img.convertToFormat(_IMG["fmt"])
    buf = img.constBits()
    try:
        buf.setsize(img.sizeInBytes())
    except Exception:
        pass
    a = _np().frombuffer(bytes(buf), np.uint8).reshape(
        img.height(), img.bytesPerLine() // 4, 4)[:, :img.width()]
    return a.astype(np.float32) / 255.0


def _np_to_qimage(arr):
    np = _np()
    a = np.ascontiguousarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8))
    if a.shape[2] == 3:
        a = np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])
        a = np.ascontiguousarray(a)
    img = _IMG["QtGui"].QImage(a.data, a.shape[1], a.shape[0],
                               a.shape[1] * 4, _IMG["fmt"])
    return img.copy()


def _img_load(path):
    img = _IMG["QtGui"].QImage(path)
    if img.isNull():
        raise CmdException("could not read image '%s'" % path)
    return _qimage_to_np(img)


def _img_save(arr, path, dpi=0):
    img = _np_to_qimage(arr)
    if dpi:
        per_m = int(round(dpi / 0.0254))
        img.setDotsPerMeterX(per_m)
        img.setDotsPerMeterY(per_m)
    if not img.save(path):
        raise CmdException("could not write image '%s'" % path)
    return path


def _img_resize(arr, w, h):
    QtCore = _IMG["QtCore"]
    img = _np_to_qimage(arr).scaled(
        int(w), int(h), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation)
    return _qimage_to_np(img)


def _box1d(a, r, axis):
    np = _np()
    if r < 1:
        return a
    a = np.moveaxis(a, axis, 0)
    pad = np.concatenate([np.repeat(a[:1], r + 1, 0), a,
                          np.repeat(a[-1:], r, 0)], 0)
    c = np.cumsum(pad.astype(np.float32), 0)
    out = (c[2 * r + 1:] - c[:-(2 * r + 1)]) / float(2 * r + 1)
    return np.moveaxis(out, 0, axis)


def _blur(a, radius):
    """Three box passes approximate a gaussian closely enough for glow."""
    r = int(round(max(0.0, radius) * 0.55))
    if r < 1:
        return a
    for _ in range(3):
        a = _box1d(_box1d(a, r, 0), r, 1)
    return a


def _srgb_to_lin(a):
    np = _np()
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(a):
    np = _np()
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055)


def _make_bg(spec, w, h):
    """Build an opaque RGB background from a background spec."""
    np = _np()
    if isinstance(spec, str):
        spec = BACKGROUNDS.get(spec.lower(), spec)
    if spec is None:
        return None
    if isinstance(spec, (list, tuple)) and len(spec) == 3 and \
            isinstance(spec[0], str) and spec[0] in ("linear", "radial"):
        kind, c1, c2 = spec
        a, bb = np.array(_hex2rgb(c1), np.float32), np.array(_hex2rgb(c2), np.float32)
        if kind == "linear":
            t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
        else:
            yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0) / max(h, 1)
            xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0) / max(w, 1)
            d = np.sqrt(yy[:, None] ** 2 + xx[None, :] ** 2)
            t = np.clip(d / (0.5 * math.sqrt(2.0)) * 1.25, 0.0, 1.0)[:, :, None]
        rgb = a * (1.0 - t) + bb * t
        return np.broadcast_to(rgb, (h, w, 3)).astype(np.float32).copy()
    rgb = np.array(_hex2rgb(spec), np.float32)
    return np.broadcast_to(rgb, (h, w, 3)).astype(np.float32).copy()


def _over(fg, bg_rgb):
    """Composite premultiply-free RGBA over an opaque RGB background."""
    np = _np()
    a = fg[:, :, 3:4]
    out = fg[:, :, :3] * a + bg_rgb * (1.0 - a)
    return np.clip(out, 0.0, 1.0)


def _apply_shadow(fg, bg_rgb, dx, dy, blur, opacity):
    """Soft drop shadow cast by the object silhouette onto the background."""
    np = _np()
    h, w = fg.shape[:2]
    alpha = fg[:, :, 3]
    sh = _blur(alpha, blur)
    sh = _shift(_shift(sh, int(round(dy)), 0), int(round(dx)), 1)
    sh = np.clip(sh * opacity, 0.0, 1.0)[:, :, None]
    return bg_rgb * (1.0 - sh)


def _apply_bloom(rgb, threshold, radius, strength, alpha=None):
    np = _np()
    lin = _srgb_to_lin(rgb)
    lum = lin[:, :, 0] * 0.2126 + lin[:, :, 1] * 0.7152 + lin[:, :, 2] * 0.0722
    mask = np.clip((lum - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0)
    if alpha is not None:
        mask = mask * alpha
    bright = lin * mask[:, :, None]
    glow = _blur(bright, radius) + 0.45 * _blur(bright, radius * 2.6)
    return _lin_to_srgb(lin + glow * strength)


def _apply_halo(bg_rgb, alpha, width_px, hexcol, opacity):
    """Lay a soft envelope field behind the subject.

    Architectural molecular illustration often draws a grey silhouette a little
    larger than the molecule, which separates it from the page and states its
    overall shape before the reader parses any detail."""
    np = _np()
    solid = alpha > 0.35
    grown = _dilate(solid, max(1, int(round(width_px))))
    band = grown.astype(np.float32)
    band = np.clip(_blur(band, max(1.0, width_px * 0.55)), 0.0, 1.0)
    band = band * (1.0 - np.clip(alpha, 0.0, 1.0)) * float(opacity)
    col = np.array(_hex2rgb(hexcol), np.float32)
    return np.clip(bg_rgb * (1 - band[:, :, None]) + col * band[:, :, None],
                   0.0, 1.0)


def _apply_vignette(rgb, amount):
    np = _np()
    h, w = rgb.shape[:2]
    yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0) / (h / 2.0)
    xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0) / (w / 2.0)
    d = np.sqrt(yy[:, None] ** 2 + xx[None, :] ** 2) / math.sqrt(2.0)
    v = 1.0 - amount * np.clip((d - 0.35) / 0.65, 0.0, 1.0) ** 1.6
    return np.clip(rgb * v[:, :, None], 0.0, 1.0)


def _apply_grade(rgb, contrast=1.0, saturation=1.0, gamma=1.0, lift=0.0,
                 tint=None, tint_amount=0.0):
    np = _np()
    out = np.clip(rgb, 0.0, 1.0)
    if gamma and abs(gamma - 1.0) > 1e-6:
        out = out ** (1.0 / gamma)
    if abs(contrast - 1.0) > 1e-6:
        out = np.clip((out - 0.5) * contrast + 0.5, 0.0, 1.0)
    if abs(saturation - 1.0) > 1e-6:
        lum = (out[:, :, 0] * 0.2126 + out[:, :, 1] * 0.7152 +
               out[:, :, 2] * 0.0722)[:, :, None]
        out = np.clip(lum + (out - lum) * saturation, 0.0, 1.0)
    if abs(lift) > 1e-6:
        out = np.clip(out * (1.0 - lift) + lift, 0.0, 1.0)
    if tint is not None and tint_amount > 0:
        t = np.array(_hex2rgb(tint), np.float32)
        out = np.clip(out * (1.0 - tint_amount) + t * tint_amount, 0.0, 1.0)
    return out


def _apply_posterize(rgb, levels):
    np = _np()
    n = max(2, int(levels)) - 1
    return np.clip(np.round(rgb * n) / float(n), 0.0, 1.0)


def _apply_grain(rgb, amount, seed=7):
    np = _np()
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, amount, rgb.shape[:2]).astype(np.float32)
    return np.clip(rgb + n[:, :, None], 0.0, 1.0)


def _apply_sharpen(rgb, amount):
    np = _np()
    blurred = _blur(rgb, 1.6)
    return np.clip(rgb + (rgb - blurred) * amount, 0.0, 1.0)


def _draw_text(arr, items):
    """items: list of dicts with text, x, y, size, color, align, weight, bg."""
    QtGui, QtCore = _IMG["QtGui"], _IMG["QtCore"]
    img = _np_to_qimage(arr)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
    for it in items:
        font = QtGui.QFont(it.get("family", "Helvetica Neue"))
        font.setPixelSize(max(6, int(it.get("size", 24))))
        font.setBold(bool(it.get("bold", False)))
        if it.get("letter_spacing"):
            font.setLetterSpacing(QtGui.QFont.SpacingType.PercentageSpacing,
                                  100.0 + it["letter_spacing"])
        p.setFont(font)
        fm = QtGui.QFontMetrics(font)
        text = it.get("text", "")
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        x, y = int(it.get("x", 0)), int(it.get("y", 0))
        align = it.get("align", "left")
        if align == "center":
            x -= tw // 2
        elif align == "right":
            x -= tw
        if it.get("bg"):
            pad = int(it.get("bg_pad", th * 0.28))
            r = QtCore.QRect(x - pad, y - pad, tw + 2 * pad, th + 2 * pad)
            col = QtGui.QColor(*[int(c * 255) for c in _hex2rgb(it["bg"])])
            col.setAlphaF(float(it.get("bg_alpha", 0.75)))
            p.setBrush(col)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, pad * 0.6, pad * 0.6)
        rgb = _hex2rgb(it.get("color", "#000000"))
        p.setPen(QtGui.QColor(*[int(c * 255) for c in rgb]))
        p.drawText(x, y + fm.ascent(), text)
    p.end()
    return _qimage_to_np(img)


def _draw_rects(arr, rects):
    """rects: list of (x, y, w, h, hexcolor, alpha)."""
    QtGui, QtCore = _IMG["QtGui"], _IMG["QtCore"]
    img = _np_to_qimage(arr)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    for (x, y, w, h, hexcol, alpha) in rects:
        col = QtGui.QColor(*[int(c * 255) for c in _hex2rgb(hexcol)])
        col.setAlphaF(float(alpha))
        p.setBrush(col)
        p.drawRect(int(x), int(y), int(w), int(h))
    p.end()
    return _qimage_to_np(img)


# ==========================================================================
# camera and framing
# ==========================================================================

VIEWS = {
    "best": [],
    "front": [],
    "back": [("y", 180)],
    "top": [("x", 90)],
    "bottom": [("x", -90)],
    "side": [("y", 90)],
    "iso": [("y", 30), ("x", -22)],
    "hero": [("y", 24), ("x", -13), ("z", 4)],
    "tilt": [("x", -18)],
    "tall": [("z", 90)],
    "core": [],
    "pose": [],
    "detail": [],
    "wide": [],
}


def _core_selection(sel, keep=0.92, name="viz_core"):
    """The compact bulk of *sel*, ignoring outlying tails.

    A disordered AlphaFold tail or a flexible arm can be half the bounding box
    while being a tenth of the structure, which leaves the interesting part
    tiny in the middle of the frame."""
    coords = []
    try:
        cmd.iterate_state(-1, sel, "coords.append((x, y, z))",
                          space={"coords": coords})
    except Exception:
        return ""
    if len(coords) < 20:
        return ""
    n = float(len(coords))
    cx = sum(c[0] for c in coords) / n
    cy = sum(c[1] for c in coords) / n
    cz = sum(c[2] for c in coords) / n
    d = sorted(math.sqrt((c[0] - cx) ** 2 + (c[1] - cy) ** 2 +
                         (c[2] - cz) ** 2) for c in coords)
    radius = d[min(len(d) - 1, int(keep * (len(d) - 1)))]
    if radius <= 0 or radius >= d[-1] * 0.98:
        return ""
    cmd.delete("viz_core_centre")
    cmd.pseudoatom("viz_core_centre", pos=[cx, cy, cz])
    cmd.select(name, "(%s) within %.3f of viz_core_centre" % (sel, radius))
    cmd.delete("viz_core_centre")
    if not cmd.count_atoms(name):
        cmd.delete(name)
        return ""
    return name


def _scale_field(factor):
    """Zoom out (>1) or in (<1) without changing what is centred."""
    v = list(cmd.get_view())
    dist = -v[11]
    new = dist * factor
    delta = new - dist
    v[11] = -new
    v[15] += delta
    v[16] += delta
    cmd.set_view(v)


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 1e-9 else None


# 2*dist*tan(fov/2) is the world height PyMOL shows, verified exactly against a
# rendered ruler under orthoscopic projection, where fitting reaches ~86% frame
# fill. Under perspective the relationship does not hold and the fit comes out
# looser (~66-75%). Scaling the distance down was measured across styles: 0.92
# already clips a translucent surface, so no single factor tightens perspective
# framing safely and this stays at 1. Orthoscopic styles frame tighter.
PERSPECTIVE_FIT = 1.0


def _fit_projected(sel, margin=0.05, pad=0.0, aspect=None):
    """Tighten the zoom to the structure's projected outline.

    cmd.zoom fits a bounding sphere, so that nothing clips whichever way you
    then rotate. That is the safe choice interactively and the wrong one for a
    figure: a flat or elongated structure ends up floating in the middle of a
    lot of empty frame. Fitting what the camera actually sees fills it."""
    try:
        import numpy
        coords = cmd.get_coords(sel)
    except Exception:
        return False
    if coords is None or len(coords) < 2:
        return False
    v = list(cmd.get_view())
    rot = numpy.array(v[0:9], dtype=float).reshape(3, 3)
    origin = numpy.array(v[12:15], dtype=float)
    # verified against rendered pixel positions; rot.T swaps the screen axes,
    # which mis-fits anything that is not roughly square
    seen = (coords - origin).dot(rot)
    half_w = float(numpy.abs(seen[:, 0]).max()) + pad
    half_h = float(numpy.abs(seen[:, 1]).max()) + pad
    if half_w <= 0.0 or half_h <= 0.0:
        return False
    if aspect is None:
        vp = cmd.get_viewport()
        aspect = (vp[0] / float(vp[1])) if vp and vp[1] else 1.0
    fov = cmd.get_setting_float("field_of_view")
    half_fov = math.tan(math.radians(fov) / 2.0)
    grow = 1.0 + 2.0 * margin

    need = max(2.0 * half_h, 2.0 * half_w / aspect) * grow
    dist = need / (2.0 * half_fov)
    if not cmd.get_setting_int("orthoscopic"):
        dist *= PERSPECTIVE_FIT
    delta = dist - (-v[11])
    v[11] = -dist
    v[15] += delta
    v[16] += delta
    cmd.set_view(v)
    return True


def _symmetry_axis(sel):
    """The n-fold axis of a ring of copies, if there is one.

    A group of identical chains arranged in a ring has its axis along the
    normal of the plane their centres lie in. `cmd.orient` cannot find this:
    it returns the axis of largest spread, which for a barrel is whatever the
    deposited coordinates happen to make widest, and lands the ring obliquely
    where neither the symmetry nor the stacking can be read."""
    try:
        import numpy
    except Exception:
        return None
    rings = []
    for members in _entity_groups(sel):
        for grp in _spatial_split(members, sel):
            if len(grp) < 3:
                continue
            pts = []
            for model, chain in grp:
                try:
                    c = cmd.get_coords(_sel_chain("(%s) and polymer" % sel,
                                                  model, chain))
                except Exception:
                    c = None
                if c is not None and len(c):
                    pts.append(c.mean(axis=0))
            if len(pts) >= 3:
                rings.append((len(pts), numpy.array(pts, dtype=float)))
    if not rings:
        return None
    axes = []
    for n, pts in rings:
        cen = pts - pts.mean(axis=0)
        try:
            _, sv, vt = numpy.linalg.svd(cen, full_matrices=False)
        except Exception:
            continue
        # a ring is flat: its third singular value is small beside the first
        if sv[0] <= 1e-6 or sv[2] / sv[0] > 0.30:
            continue
        axes.append((n, vt[2] / (numpy.linalg.norm(vt[2]) or 1.0)))
    if not axes:
        return None
    ref = max(axes, key=lambda t: t[0])[1]
    # rings sharing an axis (the two stacked halves of a chaperonin) agree
    agree = [a if float(a.dot(ref)) >= 0 else -a for _, a in axes
             if abs(float(a.dot(ref))) > 0.85]
    v = sum(agree[1:], agree[0]) if agree else ref
    n = float((v.dot(v)) ** 0.5)
    return v / n if n else None


def _orient_pocket(sel, lig):
    """Look into the pocket, not at the back of it.

    `cmd.orient` on the site returns the widest projection of those atoms,
    which is just as likely to put the protein between the reader and the
    ligand as behind it. A binding-site figure has one requirement - the
    ligand must be the nearest thing to the camera - so the view direction is
    taken from the protein's centre out through the ligand."""
    try:
        import numpy
        prot = cmd.get_coords("(%s) and polymer" % sel)
        lc = cmd.get_coords(lig)
    except Exception:
        return False
    if prot is None or lc is None or len(lc) < 1 or len(prot) < 3:
        return False
    cen, lcen = prot.mean(axis=0), lc.mean(axis=0)
    z = lcen - cen
    nz = float(numpy.linalg.norm(z))
    if nz < 1.0:
        return False                      # ligand sits on the centroid
    z = z / nz
    flat = lc - lcen
    perp = flat - numpy.outer(flat.dot(z), z)
    x = None
    if len(perp) > 2:
        try:
            _, _, vt = numpy.linalg.svd(perp, full_matrices=False)
            x = vt[0] - z * float(vt[0].dot(z))
        except Exception:
            x = None
    if x is None or float(numpy.linalg.norm(x)) < 1e-6:
        x = numpy.cross(z, [0.0, 0.0, 1.0])
        if float(numpy.linalg.norm(x)) < 1e-6:
            x = numpy.cross(z, [0.0, 1.0, 0.0])
    x = x / float(numpy.linalg.norm(x))
    y = numpy.cross(z, x)

    def _apply(xa, za):
        v = list(cmd.get_view())
        m = numpy.column_stack([xa, numpy.cross(za, xa), za])
        v[0:9] = [float(t) for t in m.flatten()]
        cmd.set_view(v)

    _apply(x, z)
    # which way is "toward the camera" is a convention, so measure it rather
    # than assume: the ligand must end up in front of the protein's bulk
    v = cmd.get_view()
    rot = numpy.array(v[0:9], dtype=float).reshape(3, 3)
    org = numpy.array(v[12:15], dtype=float)
    if float((lc - org).dot(rot)[:, 2].mean()) < \
            float((prot - org).dot(rot)[:, 2].mean()):
        _apply(-x, -z)
    cmd.zoom(_visible(sel), 0.0, complete=1)
    return True


def _orient_across(pair, core):
    """Put the line between two partners across the frame, not into it."""
    if not pair:
        return False
    try:
        import numpy
        ca = numpy.array(cmd.get_coords(pair[0])).mean(axis=0)
        cb = numpy.array(cmd.get_coords(pair[1])).mean(axis=0)
        pts = numpy.array(cmd.get_coords(core))
    except Exception:
        return False
    x = cb - ca
    n = float(numpy.linalg.norm(x))
    if n < 1.0:
        return False
    x = x / n
    flat = pts - pts.mean(axis=0)
    perp = flat - numpy.outer(flat.dot(x), x)
    try:
        _, _, vt = numpy.linalg.svd(perp, full_matrices=False)
        y = vt[0] - x * float(vt[0].dot(x))
    except Exception:
        y = numpy.cross(x, [0.0, 0.0, 1.0])
    ny = float(numpy.linalg.norm(y))
    if ny < 1e-6:
        return False
    y = y / ny
    v = list(cmd.get_view())
    m = numpy.column_stack([x, y, numpy.cross(x, y)])
    v[0:9] = [float(t) for t in m.flatten()]
    cmd.set_view(v)
    return True


def _orient_symmetry(sel):
    """Stand a symmetric assembly on its axis: rings stack, a cap caps.

    Oblique is the one orientation that shows neither the symmetry nor the
    stacking, and it is what an inertial orient gives for most assemblies."""
    axis = _symmetry_axis(sel)
    if axis is None:
        return False
    try:
        import numpy
        coords = cmd.get_coords(_visible(sel))
    except Exception:
        return False
    if coords is None or len(coords) < 3:
        return False
    up = numpy.array(axis, dtype=float)
    flat = coords - coords.mean(axis=0)
    # the widest direction perpendicular to the axis faces the reader
    perp = flat - numpy.outer(flat.dot(up), up)
    try:
        _, _, vt = numpy.linalg.svd(perp, full_matrices=False)
    except Exception:
        return False
    right = vt[0] - up * float(vt[0].dot(up))
    nr = float(numpy.linalg.norm(right))
    if nr < 1e-6:
        return False
    right /= nr
    fwd = numpy.cross(right, up)
    v = list(cmd.get_view())
    # columns are the camera axes in world coordinates, matching the
    # (coords - origin) . R convention the framing code is verified against
    m = numpy.column_stack([right, up, fwd])
    v[0:9] = [float(x) for x in m.flatten()]
    cmd.set_view(v)
    cmd.zoom(_visible(sel), 0.0, complete=1)
    return True


# Shorthands so a mix spec reads like the sentence you would say out loud.
# "rest" is what no earlier rule claimed, which is what makes a spec
# order-dependent in the way a person expects.
SPEC_WORDS = {
    "protein": SEL_PROT, "nucleic": SEL_NUC, "dna": "polymer.nucleic and "
    "resn DA+DT+DG+DC+DI", "rna": "polymer.nucleic and resn A+U+G+C+I",
    "ligand": SEL_LIG, "ligands": SEL_LIG, "solvent": SEL_WAT,
    "water": SEL_WAT, "ions": SEL_ION, "polymer": "polymer",
    "het": "not polymer", "all": "all", "everything": "all",
}


def _parse_spec(text, label):
    """Parse 'selection = value / selection = value' into ordered pairs.

    PyMOL's parser eats commas inside an argument, so pairs are separated by
    / or |. Selections are ordinary PyMOL selections, plus a few words for the
    things people ask for by name, plus `rest` for whatever is left over."""
    txt = _s(text)
    if not txt:
        raise CmdException("%s needs at least one 'selection=value' pair" % label)
    pairs = []
    for chunk in re.split(r"\s*[/|]\s*", txt):
        if not chunk.strip():
            continue
        if "=" not in chunk:
            raise CmdException(
                "%s: '%s' is not a 'selection=value' pair. Separate pairs with "
                "/ because PyMOL's parser eats commas: "
                "protein=ghost / nucleic=cartoon" % (label, chunk.strip()))
        sel, val = chunk.split("=", 1)
        sel, val = sel.strip(), val.strip()
        if not sel or not val:
            raise CmdException("%s: '%s' has an empty side" % (label, chunk))
        pairs.append((SPEC_WORDS.get(sel.lower(), sel), val))
    return pairs


def _spec_selections(pairs, scope="all"):
    """Resolve each rule to a concrete selection, giving `rest` the remainder.

    Earlier rules win, so overlapping selections do not double-draw and the
    reader of the spec gets the precedence they wrote."""
    out, claimed = [], []
    for sel, val in pairs:
        if sel.lower() == "rest":
            if claimed:
                s_ = "(%s) and not (%s)" % (scope, " or ".join(
                    "(%s)" % c for c in claimed))
            else:
                s_ = "(%s)" % scope
        else:
            s_ = "(%s) and (%s)" % (scope, sel)
            if claimed:
                s_ += " and not (%s)" % " or ".join("(%s)" % c for c in claimed)
        try:
            n = cmd.count_atoms(s_)
        except Exception as exc:
            raise CmdException("bad selection '%s': %s" % (sel, exc))
        if n:
            out.append((s_, val, n))
        if sel.lower() != "rest":
            claimed.append(sel)
    return out


def _rep_pad(rep, blob):
    """How far the drawn geometry reaches past the atom centres.

    A cartoon ribbon, a nucleic-acid ladder and a stick all extend beyond the
    coordinates they are built from, so fitting to atom positions alone clips
    the drawing at the frame edge."""
    if rep == "mix":
        return blob + 2.0
    if _s(rep).startswith("nucleic+"):
        return max(3.2, _rep_pad(rep.split("+", 1)[1], blob))
    if rep in ("surface", "ghost", "mesh", "dots", "cartoon+surface", "pocket"):
        return blob + 2.0
    if rep == "spheres":
        return 2.0
    if rep in ("nucleic", "putty"):
        return 3.2
    if rep in ("cartoon", "tube", "ribbon"):
        return 2.6
    if rep in ("sticks", "ballstick", "lines", "detail"):
        return 1.6
    return 1.2


def _angstrom_per_pixel(height_px):
    """Validated against a CGO ruler: exact for orthoscopic projection."""
    v = cmd.get_view()
    fov = cmd.get_setting_float("field_of_view")
    world_h = 2.0 * (-v[11]) * math.tan(math.radians(fov) / 2.0)
    return world_h / float(max(1, height_px))


def _viewport_aspect():
    vp = cmd.get_viewport()
    if not vp or not vp[1]:
        return 1.0
    return float(vp[0]) / float(vp[1])


def viz_pose(selection="", subject="", candidates=32, quiet=0):
    """
DESCRIPTION

    Search orientations and keep the one that shows the most.

    cmd.orient picks the view with the largest projected spread, which is an
    inertial property and says nothing about whether the result explains the
    structure. This scores candidate orientations on how much of the subject is
    unoccluded and how much of the whole is visible, and takes the best.

    It is off by default and always will be - a scored pose is a suggestion,
    not a fact, and the view you chose yourself is usually the right one.

USAGE

    viz_pose [selection [, subject [, candidates ]]]

ARGUMENTS

    selection  = what to orient {default: everything}
    subject    = what must remain visible; empty picks the bound ligand if
                 there is one, otherwise scores overall exposure only
    candidates = orientations to try {default: 32}

EXAMPLES

    viz_pose
    viz_pose all, organic
    viz pocket
    viz_pose all, resi 145
    """
    try:
        import numpy
    except Exception:
        raise CmdException("viz_pose needs numpy")
    sel = _s(selection) or "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    subj = _s(subject) or _focus_selection(sel)

    shown = _visible(sel)
    coords = cmd.get_coords(shown)
    if coords is None or len(coords) < 4:
        raise CmdException("nothing visible to orient")
    centre = coords.mean(axis=0)
    pts = coords - centre
    subj_mask = None
    if subj and cmd.count_atoms(subj):
        sc = cmd.get_coords(_visible(subj))
        if sc is not None and len(sc):
            keys = set(map(tuple, numpy.round(sc, 3)))
            subj_mask = numpy.array([tuple(r) in keys
                                     for r in numpy.round(coords, 3)])
            if not subj_mask.any():
                subj_mask = None

    n = max(8, _i(candidates, 32))
    # Fibonacci sphere: an even spread of viewing directions without clustering
    # at the poles, which a naive latitude/longitude grid gives you
    ga = math.pi * (3.0 - math.sqrt(5.0))
    best = None
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - z * z))
        th = ga * i
        view_dir = numpy.array([r * math.cos(th), r * math.sin(th), z])
        up = numpy.array([0.0, 0.0, 1.0])
        if abs(float(view_dir.dot(up))) > 0.9:
            up = numpy.array([0.0, 1.0, 0.0])
        xa = numpy.cross(up, view_dir)
        na = numpy.linalg.norm(xa)
        if na < 1e-6:
            continue
        xa = xa / na
        ya = numpy.cross(view_dir, xa)
        proj = numpy.stack([pts.dot(xa), pts.dot(ya), pts.dot(view_dir)], axis=1)

        spread = float(numpy.ptp(proj[:, 0]) * numpy.ptp(proj[:, 1]))
        score = spread
        if subj_mask is not None:
            # how much of the subject has nothing sitting in front of it
            sp = proj[subj_mask]
            other = proj[~subj_mask]
            if len(sp) and len(other):
                exposed = 0
                for q in sp[:: max(1, len(sp) // 40)]:
                    near = other[(numpy.abs(other[:, 0] - q[0]) < 2.2) &
                                 (numpy.abs(other[:, 1] - q[1]) < 2.2)]
                    if not len(near) or near[:, 2].max() <= q[2] + 1.0:
                        exposed += 1
                frac = exposed / float(max(1, len(sp[:: max(1, len(sp) // 40)])))
                score = spread * (0.25 + 1.75 * frac)
        if best is None or score > best[0]:
            best = (score, xa, ya, view_dir)

    if best is None:
        raise CmdException("no usable orientation found")
    _, xa, ya, za = best
    v = list(cmd.get_view())
    v[0:9] = [float(xa[0]), float(ya[0]), float(za[0]),
              float(xa[1]), float(ya[1]), float(za[1]),
              float(xa[2]), float(ya[2]), float(za[2])]
    cmd.set_view(v)
    cmd.zoom(shown, 0.0, complete=1)
    _fit_projected(shown, 0.05, _rep_pad(_LAST.get("rep", ""),
                                         _LAST.get("blob", 1.4)))
    if not _b(quiet):
        print(" viz_pose: best of %d orientations%s"
              % (n, " (keeping '%s' visible)" % subj if subj else ""))
    return True


def viz_view(preset="best", selection="", buffer=0.0, margin=0.04, quiet=0):
    """
DESCRIPTION

    Point the camera at the structure using a named viewpoint.

USAGE

    viz_view [preset [, selection [, buffer ]]]

ARGUMENTS

    preset    = best | front | back | top | bottom | side | iso | hero |
                tilt | tall | core
                'core' frames the compact bulk and lets disordered tails run
                out of frame, which is usually what you want for AlphaFold
                models.
    selection = what to frame {default: everything visible}
    buffer    = extra Angstrom of margin around the structure {default: 0}
    margin    = fraction of the frame left empty around the structure
                {default: 0.04}
    """
    preset = _resolve(preset, VIEWS, "view preset", "best")
    sel = _s(selection) or "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    frame_on = sel
    if preset == "pose":
        viz_pose(sel, quiet=1)
        if not _b(quiet):
            print(" viz_view: pose (scored orientation)")
        return
    if preset == "detail":
        target = _focus_selection(sel)
        if target:
            pocket = "(%s) or byres ((%s) and polymer within 6 of (%s))" \
                % (target, sel, target)
            if not _orient_pocket(sel, pocket):
                cmd.orient(pocket)
            cmd.zoom(pocket, 1.5)
            if not _b(quiet):
                print(" viz_view: detail (framed on the bound ligand)")
            return
        cmd.orient(sel)
    elif preset == "wide":
        cmd.orient(sel)
        cmd.zoom(_visible(sel), 0.0, complete=1)
        _scale_field(1.45)
        if not _b(quiet):
            print(" viz_view: wide")
        return
    elif preset == "core":
        core = _core_selection(sel)
        if core:
            frame_on = core
        cmd.orient(frame_on)
    elif preset in ("best", "iso", "hero", "tilt", "tall"):
        cmd.orient(sel)
    else:
        v = list(cmd.get_view())
        v[0:9] = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        cmd.set_view(v)
    for axis, deg in VIEWS[preset]:
        cmd.turn(axis, deg)
    shown = _visible(frame_on)
    cmd.zoom(shown, _f(buffer, 0.0), complete=1)
    m = _f(margin, 0.04)
    pad = _rep_pad(_LAST.get("rep", ""), _LAST.get("blob", 1.4)) + _f(buffer, 0.0)
    if not _fit_projected(shown, m, pad) and m:
        _scale_field(1.0 + 2.0 * m)
    if frame_on != sel:
        cmd.delete(frame_on)
    if not _b(quiet):
        print(" viz_view: %s" % preset)


def viz_frame(preset="slide", selection="", buffer=0.0, margin=0.04, quiet=0):
    """
DESCRIPTION

    Set the viewport to a figure aspect ratio and refit the structure, so the
    interactive view matches what viz_render will produce.

USAGE

    viz_frame [preset [, selection [, buffer ]]]

ARGUMENTS

    preset = square | slide | wide | photo | golden | portrait | story |
             column | dcolumn | cover   (or a number such as 1.5)
    """
    txt = _s(preset, "slide")
    try:
        aspect = float(txt)
    except ValueError:
        aspect = FRAMES[_resolve(txt, FRAMES, "frame preset", "slide")]
    area = 780.0 * 780.0
    h = int(round(math.sqrt(area / aspect)))
    w = int(round(h * aspect))
    cmd.viewport(w, h)
    sel = _s(selection) or "all"
    if cmd.count_atoms(sel):
        shown = _visible(sel)
        cmd.zoom(shown, _f(buffer, 0.0), complete=1)
        m = _f(margin, 0.04)
        pad = _rep_pad(_LAST.get("rep", ""), _LAST.get("blob", 1.4))
        if not _fit_projected(shown, m, pad + _f(buffer, 0.0)) and m:
            _scale_field(1.0 + 2.0 * m)
    if not _b(quiet):
        print(" viz_frame: %s (%dx%d, aspect %.3f)" % (txt, w, h, aspect))


# ==========================================================================
# render
# ==========================================================================

STYLE_DEFAULTS = dict(desc="", rep="auto", light="soft", ao=None, outline=0.0,
                      ocolor="black", lineart=False, ortho=False,
                      blob=1.4, bg="white", palette="molstar",
                      coloring="chain", fog=0.0, focus="", edge=None,
                      ink="edge", ink_threshold=12.0, dof=0.0,
                      flat_ribbon=False, gaps=False, interface=False,
                      annotations={}, set={}, post={})

# (gain, depth_factor, slope_factor, disco_factor).
# Lower depth/slope means the edge detector fires more often, so more interior
# contour lines survive: that is the difference between a clean silhouette and
# a hatched drawing.
EDGE_DEFAULT = (0.12, 1.0, 4.0, 1.0)


def _style(name):
    st = dict(STYLE_DEFAULTS)
    name = STYLE_ALIASES.get(_s(name).lower(), name)
    st.update(STYLES[_resolve(name, STYLES, "style", "publication")])
    return st


def _subject_aspect(sel, lo=0.62, hi=1.78):
    """Width:height of the subject as the camera sees it.

    A landscape complex on a square canvas leaves half the page empty, and the
    empty half is what makes a figure look like a screenshot. Clamped so an
    extreme axial ratio does not produce a letterbox nothing else can sit in."""
    try:
        import numpy
        coords = cmd.get_coords(_visible(sel))
        v = cmd.get_view()
        seen = (coords - numpy.array(v[12:15], dtype=float)).dot(
            numpy.array(v[0:9], dtype=float).reshape(3, 3))
        # the span of the subject, not its distance from the camera centre:
        # abs().max() is what the zoom fit needs and the wrong measure of shape
        ew = float(numpy.ptp(seen[:, 0]))
        eh = float(numpy.ptp(seen[:, 1]))
    except Exception:
        return None
    if eh <= 0.0:
        return None
    return max(lo, min(hi, ew / eh))


def _resolve_size(size, width, height):
    """Return (w, h) from a preset name and/or explicit dimensions."""
    w, h = _i(width), _i(height)
    txt = _s(size)
    if txt.lower() in ("fit", "auto"):
        # the canvas follows the subject rather than the subject rattling
        # around inside whatever canvas was asked for
        asp = _subject_aspect("all") or 1.0
        base = w or h or 2000
        if asp >= 1.0:
            return base, int(round(base / asp))
        return int(round(base * asp)), base
    if txt:
        if "x" in txt.lower() and txt.lower().replace("x", "").isdigit():
            a, b = txt.lower().split("x")
            return int(a), int(b)
        key = _resolve(txt, SIZES, "size preset", "preview")
        pw, ph = SIZES[key]
        if w and not h:
            return w, int(round(w * ph / float(pw)))
        return pw, ph
    if w and h:
        return w, h
    vp = cmd.get_viewport()
    base = w or 2000
    if vp and vp[0]:
        return base, int(round(base * vp[1] / float(vp[0])))
    return base, base


def _ink_mask(path, div, w, h):
    """Read a low-resolution outline pass and grow it to full size."""
    np = _np()
    lines = _img_load(path)
    m = 1.0 - lines[:, :, :3].min(axis=2)
    m = np.dstack([m, m, m, np.ones_like(m)])
    if div > 1.001:
        m = _img_resize(m, w, h)
    elif m.shape[0] != h or m.shape[1] != w:
        m = _img_resize(m, w, h)
    m = m[:, :, 0]
    return np.clip((m - 0.10) / 0.42, 0.0, 1.0)


def _shift(a, k, axis):
    """Shift by k, replicating the edge rather than wrapping.

    numpy.roll wraps, so a feature at the right border produces a phantom edge
    at the left one - which showed up as stray ink marks floating in empty space
    beside the molecule."""
    np = _np()
    out = np.roll(a, k, axis)
    dst = [slice(None)] * a.ndim
    src = [slice(None)] * a.ndim
    if k > 0:
        dst[axis] = slice(0, k)
        src[axis] = slice(0, 1)
    else:
        dst[axis] = slice(a.shape[axis] + k, None)
        src[axis] = slice(a.shape[axis] - 1, a.shape[axis])
    out[tuple(dst)] = a[tuple(src)]
    return out


def _dilate(mask, r):
    """Grow a boolean mask by r pixels (separable max filter)."""
    np = _np()
    if r < 1:
        return mask
    out = mask
    for axis in (0, 1):
        acc = out
        for k in range(1, r + 1):
            acc = np.maximum(acc, _shift(out, k, axis))
            acc = np.maximum(acc, _shift(out, -k, axis))
        out = acc
    return out


def _despeckle(mask, min_neighbours=2):
    """Drop isolated edge pixels: crevices between two atoms throw single-pixel
    depth spikes that read as dirt rather than as drawing."""
    np = _np()
    m = mask.astype(np.uint8)
    n = np.zeros(m.shape, np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                n = n + _shift(_shift(m, dy, 0), dx, 1)
    return mask & (n >= min_neighbours)


def _neighbour_jump(a):
    np = _np()
    j = np.zeros(a.shape, a.dtype)
    for axis in (0, 1):
        for k in (1, -1):
            j = np.maximum(j, np.abs(a - _shift(a, k, axis)))
    return j


def _capture_colors():
    saved = []
    cmd.iterate("all", "saved.append(color)", space={"saved": saved})
    return saved


def _restore_colors(saved):
    it = iter(saved)
    cmd.alter("all", "color = nxt(it)", space={"nxt": next, "it": it})
    cmd.recolor()


def _close(mask, r=1):
    """Heal one-pixel breaks so a contour reads as a drawn line, not a dotted
    trail of fragments."""
    if r < 1:
        return mask
    return ~_dilate(~_dilate(mask, r), r)


def _region_edges(w, h, expr, space, inside):
    """Render a flat one-colour-per-region pass and return its boundaries."""
    np = _np()
    tmp = os.path.join(_tmpdir(), "viz_id_%d.png" % os.getpid())
    cmd.alter("all", expr, space=space)
    cmd.recolor()
    cmd.rebuild()
    cmd.ray(w, h)
    cmd.png(tmp)
    if not os.path.exists(tmp):
        return None
    ids = _img_load(tmp)[:, :, :3]
    os.remove(tmp)
    edge = np.zeros(ids.shape[:2], bool)
    for axis in (0, 1):
        for k in (1, -1):
            edge |= np.abs(ids - _shift(ids, k, axis)).max(axis=2) > 0.05
    return edge & inside


def _border_free(mask):
    """Clear the outermost pixels.

    Where geometry runs off the frame, the object/background boundary follows
    the frame edge, and outlining it draws a black bar along the image border."""
    out = mask.copy()
    out[0, :] = False
    out[-1, :] = False
    out[:, 0] = False
    out[:, -1] = False
    return out


def _render_depth(w, h):
    """Render a normalised depth map: 0 at the near plane, 1 at the far plane.

    Fog over a white model gives a usable depth buffer, which is what makes
    depth of field, depth-scaled line weight and cutaway shading possible at
    all without a real G-buffer."""
    np = _np()
    saved = _capture_colors()
    keep = {}
    for key in ("ambient_occlusion_mode", "depth_cue", "ray_trace_fog", "fog",
                "fog_start", "antialias", "ray_opaque_background",
                "ray_trace_mode", "bg_rgb", "ambient", "direct", "reflect",
                "specular", "ray_shadows", "light_count",
                "transparency", "cartoon_transparency"):
        keep[key] = cmd.get(key)
    tmp = os.path.join(_tmpdir(), "viz_dpass_%d.png" % os.getpid())
    try:
        cmd.color("white", "all")
        for key, val in (("transparency", 0.0), ("cartoon_transparency", 0.0),
                         ("ambient_occlusion_mode", 0), ("ray_trace_mode", 0),
                         ("depth_cue", 1), ("ray_trace_fog", 1), ("fog", 1.0),
                         ("fog_start", 0.0), ("antialias", 0),
                         ("ray_opaque_background", 1), ("ambient", 1.0),
                         ("direct", 0.0), ("reflect", 0.0), ("specular", 0.0),
                         ("ray_shadows", 0), ("light_count", 1)):
            cmd.set(key, val)
        cmd.bg_color("black")
        cmd.rebuild()
        cmd.ray(w, h)
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return None
        depth = 1.0 - _img_load(tmp)[:, :, :3].max(axis=2)
        os.remove(tmp)
        return depth
    except Exception:
        return None
    finally:
        _restore_colors(saved)
        for key, val in keep.items():
            try:
                cmd.set(key, val)
            except Exception:
                pass
        cmd.rebuild()


def _apply_dof(rgb, depth, inside, focus, strength):
    """Depth of field by blending progressively blurred copies.

    A single blur cannot express focus falloff; three levels selected per pixel
    by distance from the focal plane reads as a lens without the cost of one
    blur per pixel radius."""
    np = _np()
    if depth is None or strength <= 0:
        return rgb
    valid = inside if inside.any() else np.ones_like(inside)
    coc = np.abs(depth - focus)
    span = float(coc[valid].max()) or 1.0
    coc = np.clip(coc / span, 0.0, 1.0) * float(strength)
    levels = [rgb]
    base = 0.004 * max(rgb.shape[0], rgb.shape[1])
    for mult in (1.0, 2.5, 5.0):
        levels.append(_blur(rgb, base * mult))
    out = rgb
    n = len(levels) - 1
    for i in range(n):
        lo, hi = i / float(n), (i + 1) / float(n)
        t = np.clip((coc - lo) / max(hi - lo, 1e-6), 0.0, 1.0)[:, :, None]
        out = np.where((coc[:, :, None] >= lo), levels[i] * (1 - t) +
                       levels[i + 1] * t, out)
    return np.clip(out, 0.0, 1.0)


def _ink_masks(w, h, inside, width_px, quiet=True):
    """Build a three-tier ink mask: silhouette, chain boundary, residue contour.

    Goodsell's illustrations outline every residue-scale lump at a lighter
    weight than the subunit boundary, and that interior ink is what makes a
    space-filling model read as a solid object built from parts rather than as
    a flat pastel field. A single-weight outline — however well placed — cannot
    express that, so three passes are rendered and dilated by different amounts.

    Residues are coloured by index modulo three rather than uniquely: any two
    sequence-adjacent residues then differ, which is all the boundary detector
    needs, and it costs three colours instead of thousands."""
    np = _np()
    saved = _capture_colors()
    keep = {}
    for key in ("ambient_occlusion_mode", "depth_cue", "ray_trace_fog",
                "antialias", "ray_opaque_background", "ray_trace_mode",
                "bg_rgb", "light_count", "ambient", "direct", "reflect",
                "specular", "ray_shadows",
                "transparency", "cartoon_transparency"):
        keep[key] = cmd.get(key)
    try:
        # flat, unshaded, no occlusion: only region identity may vary
        # A see-through body makes every region-identity pass read whatever
        # is behind it, so the edge detector fires on the whole subject and
        # the plate composites to solid black. The ink describes the geometry,
        # which is opaque whatever the colour pass does with it.
        cmd.set("transparency", 0.0)
        cmd.set("cartoon_transparency", 0.0)
        cmd.set("ambient_occlusion_mode", 0)
        cmd.set("ray_trace_mode", 0)
        cmd.set("depth_cue", 0)
        cmd.set("ray_trace_fog", 0)
        cmd.set("antialias", 0)
        cmd.set("ray_opaque_background", 1)
        cmd.set("ambient", 1.0)
        cmd.set("direct", 0.0)
        cmd.set("reflect", 0.0)
        cmd.set("specular", 0.0)
        cmd.set("ray_shadows", 0)
        cmd.set("light_count", 1)
        cmd.bg_color("black")

        trio = []
        for i, hexcol in enumerate(("#FF0000", "#00FF00", "#0000FF")):
            name = "viz_rid%d" % i
            cmd.set_color(name, list(_hex2rgb(hexcol)))
            trio.append(cmd.get_color_index(name))
        residue = None
        try:
            crowded = cmd.count_atoms("visible") > 100000
        except Exception:
            crowded = False
        if not crowded and not cmd.get_setting_int("cartoon_cylindrical_helices"):
            residue = _region_edges(w, h, "color = trio[int(resv) % 3]",
                                    {"trio": trio, "int": int}, inside)

        # a normal-delta pass: creases inside a subunit that neither the
        # residue nor the chain boundary finds. Rendered as a flat normal-shaded
        # pass whose colour varies only with orientation.
        normal_edge = None
        try:
            cmd.color("white", "all")
            cmd.set("ambient", 0.0)
            cmd.set("direct", 1.0)
            cmd.set("reflect", 0.0)
            cmd.set("light_count", 3)
            cmd.rebuild()
            cmd.ray(w, h)
            tmpn = os.path.join(_tmpdir(), "viz_nrm_%d.png" % os.getpid())
            cmd.png(tmpn)
            if os.path.exists(tmpn):
                shade = _img_load(tmpn)[:, :, :3].max(axis=2)
                os.remove(tmpn)
                normal_edge = (_neighbour_jump(shade) > 0.22) & inside
            cmd.set("ambient", 1.0)
            cmd.set("direct", 0.0)
            cmd.set("light_count", 1)
        except Exception:
            normal_edge = None

        chain_ids = {}
        for i, (model, chain) in enumerate(_chain_keys("all")):
            name = "viz_cid%d" % i
            n = i + 1
            cmd.set_color(name, [((n >> 0) & 7) / 7.0, ((n >> 3) & 7) / 7.0,
                                 ((n >> 6) & 7) / 7.0])
            chain_ids[(model, chain)] = cmd.get_color_index(name)
        default = cmd.get_color_index("white")
        chain = _region_edges(w, h, "color = cids.get((model, chain), dflt)",
                              {"cids": chain_ids, "dflt": default}, inside)
    except Exception:
        return None
    finally:
        _restore_colors(saved)
        for key, val in keep.items():
            try:
                cmd.set(key, val)
            except Exception:
                pass
        cmd.rebuild()

    if chain is None:
        return None
    if residue is None:
        residue = _np().zeros(inside.shape, bool)
    silhouette = _border_free(_dilate(~inside, 1) & inside)
    base = max(1.0, width_px)
    thick = max(1, int(round(base)))
    mid = max(1, int(round(base * 0.45)))
    thin = max(0, int(round(base * 0.2)) - 1)
    np = _np()
    residue = residue & ~chain
    if normal_edge is not None:
        residue = residue | (_despeckle(normal_edge, 3) & ~chain)
    residue = _close(_despeckle(residue, 2))

    # Interior contour is texture, not structure. Past roughly a tenth of the
    # body it stops describing form and reads as litter, so it is thinned until
    # it fits the budget rather than trusted to behave.
    body = float(inside.sum()) or 1.0
    tiers = _dilate(silhouette, thick) | _dilate(chain, mid)
    for attempt in range(4):
        grown = _dilate(residue, thin) if thin > 0 else residue
        cover = float((grown & inside & ~tiers).sum()) / body
        if cover <= INK_INTERIOR_CAP or not residue.any():
            break
        if thin > 0:
            thin -= 1
        else:
            residue = _despeckle(residue, 4 + attempt)
    return tiers | (_dilate(residue, thin) if thin > 0 else residue)


def _depth_ink_mask(w, h, inside, thresh_a, width_px, quiet=True):
    """Outline where the depth buffer jumps further than *thresh_a* Angstrom,
    plus every chain boundary.

    PyMOL's ray_trace_mode fires on normal discontinuities as well as depth, so
    in a space-filling model every atom gets its own ring - the one thing that
    separates a PyMOL render from a Goodsell illustration. Illustrate instead
    thresholds the depth difference in Angstrom, which leaves atoms inside a
    subunit smooth and draws the subunit. Fog over a white model gives us the
    depth buffer needed to do the same, and a flat one-colour-per-chain pass
    gives the region boundaries."""
    np = _np()
    saved = _capture_colors()
    keep = {}
    for key in ("ambient_occlusion_mode", "depth_cue", "ray_trace_fog", "fog",
                "fog_start", "antialias", "ray_opaque_background",
                "ray_trace_mode", "bg_rgb"):
        keep[key] = cmd.get(key)
    try:
        # ---- depth: white model, black background, full fog
        cmd.color("white", "all")
        cmd.set("ambient_occlusion_mode", 0)
        cmd.set("ray_trace_mode", 0)
        cmd.bg_color("black")
        cmd.set("ray_opaque_background", 1)
        cmd.set("depth_cue", 1)
        cmd.set("ray_trace_fog", 1)
        cmd.set("fog", 1.0)
        cmd.set("fog_start", 0.0)
        cmd.set("antialias", 0)
        cmd.rebuild()
        cmd.ray(w, h)
        tmp = os.path.join(_tmpdir(), "viz_depth_%d.png" % os.getpid())
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return None
        depth = 1.0 - _img_load(tmp)[:, :, :3].max(axis=2)
        os.remove(tmp)
        view = cmd.get_view()
        span = float(view[16] - view[15])
        if span <= 0:
            return None

        # ---- regions: one flat colour per chain, no shading
        cmd.set("depth_cue", 0)
        cmd.set("ray_trace_fog", 0)
        for i, (model, chain) in enumerate(_chain_keys("all")):
            n = i + 1
            name = "viz_id%d" % n
            cmd.set_color(name, [((n >> 0) & 7) / 7.0, ((n >> 3) & 7) / 7.0,
                                 ((n >> 6) & 7) / 7.0])
            cmd.color(name, 'model %s and chain "%s"' % (model, chain))
        cmd.rebuild()
        cmd.ray(w, h)
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return None
        ids = _img_load(tmp)[:, :, :3]
        os.remove(tmp)
    finally:
        _restore_colors(saved)
        for key, val in keep.items():
            try:
                cmd.set(key, val)
            except Exception:
                pass
        cmd.rebuild()

    edge = _despeckle((_neighbour_jump(depth) > thresh_a / span) & inside)
    for axis in (0, 1):
        for k in (1, -1):
            changed = np.abs(ids - _shift(ids, k, axis)).max(axis=2) > 0.05
            edge |= changed & inside
    silhouette = _border_free(_dilate(~inside, 1) & inside)
    return _dilate(edge | silhouette, max(1, int(round(width_px / 2.0))))


def _tmpdir():
    import tempfile
    return tempfile.gettempdir()


# Fraction of the short axis the subject should span. Below ~0.8 an image reads
# as a software default; above ~0.92 it crowds the frame.
TARGET_FILL = 0.88

# Share of the silhouette the per-residue ink tier may cover before it stops
# reading as texture and starts reading as damage.
INK_INTERIOR_CAP = 0.17


def _probe_fill(aspect, probe=320):
    """Render a cheap pass and measure how much of the frame the subject covers.

    Geometry alone cannot predict this: representations extend past their atoms
    by amounts that depend on settings, and PyMOL's perspective projection does
    not match the analytic field. Measuring the alpha channel of a small render
    is exact, cheap, and independent of background and post-processing."""
    np = _np()
    h = max(1, int(round(probe / max(aspect, 1e-6))))
    keep = {}
    for key in ("ray_trace_mode", "antialias", "ray_opaque_background"):
        keep[key] = cmd.get(key)
    tmp = os.path.join(_tmpdir(), "viz_probe_%d.png" % os.getpid())
    try:
        cmd.set("ray_trace_mode", 0)
        cmd.set("antialias", 0)
        cmd.set("ray_opaque_background", 0)
        cmd.ray(probe, h)
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return None
        alpha = _img_load(tmp)[:, :, 3] > 0.02
    except Exception:
        return None
    finally:
        for key, val in keep.items():
            try:
                cmd.set(key, val)
            except Exception:
                pass
        if os.path.exists(tmp):
            os.remove(tmp)
    if not alpha.any():
        return None
    ys, xs = np.where(alpha)
    return max((xs.max() - xs.min() + 1) / float(probe),
               (ys.max() - ys.min() + 1) / float(h))


def _fit_measured(aspect, target=TARGET_FILL, rounds=4, margin=0.04):
    """Correct the zoom until the subject spans *target* of the frame, then
    guarantee it does not touch the edge.

    Fitting to a measured fill overshoots as readily as it undershoots, and an
    amputated specimen is worse than a small one, so the margin is enforced
    afterwards rather than trusted."""
    ok = False
    for _ in range(rounds):
        fill = _probe_fill(aspect)
        if not fill:
            return False
        ok = True
        correction = fill / target
        if abs(correction - 1.0) < 0.02:
            break
        _scale_field(correction)
    if ok:
        _recentre_measured(aspect)
    for _ in range(4):
        touch = _probe_touches_edge(aspect, margin)
        if not touch:
            break
        _scale_field(1.0 + margin * 1.6)
    return ok


def _recentre_measured(aspect, probe=560):
    """Put the specimen in the middle of the frame, measured rather than assumed.

    Zooming is symmetric about the view centre, so a subject whose drawn extent
    is not centred on that point stays off-centre however well it is fitted -
    which is how a plate ends up with a fifth of its width empty on one side."""
    np = _np()
    h = max(1, int(round(probe / max(aspect, 1e-6))))
    keep = {k: cmd.get(k) for k in ("ray_trace_mode", "antialias",
                                    "ray_opaque_background")}
    tmp = os.path.join(_tmpdir(), "viz_ctr_%d.png" % os.getpid())
    try:
        cmd.set("ray_trace_mode", 0)
        cmd.set("antialias", 0)
        cmd.set("ray_opaque_background", 0)
        cmd.ray(probe, h)
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return False
        a = _img_load(tmp)[:, :, 3] > 0.004
    except Exception:
        return False
    finally:
        for k, v in keep.items():
            cmd.set(k, v)
        if os.path.exists(tmp):
            os.remove(tmp)
    rows, cols = np.where(a.any(1))[0], np.where(a.any(0))[0]
    if not len(rows) or not len(cols):
        return False
    dx = ((cols[0] + cols[-1]) / 2.0 - (probe - 1) / 2.0) / probe
    dy = ((rows[0] + rows[-1]) / 2.0 - (h - 1) / 2.0) / float(h)
    if abs(dx) < 0.006 and abs(dy) < 0.006:
        return True
    v = list(cmd.get_view())
    fov = cmd.get_setting_float("field_of_view")
    frame_h = 2.0 * (-v[11]) * math.tan(math.radians(fov) / 2.0)
    rot = v[0:9]
    right = (rot[0], rot[3], rot[6])
    up = (rot[1], rot[4], rot[7])
    ax, ay = dx * frame_h * aspect, -dy * frame_h
    for i in range(3):
        v[12 + i] += right[i] * ax + up[i] * ay
    cmd.set_view(v)
    return True


def _probe_touches_edge(aspect, margin, probe=560):
    """True if the subject reaches within *margin* of any frame edge."""
    np = _np()
    h = max(1, int(round(probe / max(aspect, 1e-6))))
    keep = {k: cmd.get(k) for k in ("ray_trace_mode", "antialias",
                                    "ray_opaque_background")}
    tmp = os.path.join(_tmpdir(), "viz_edge_%d.png" % os.getpid())
    try:
        cmd.set("ray_trace_mode", 0)
        cmd.set("antialias", 0)
        cmd.set("ray_opaque_background", 0)
        cmd.ray(probe, h)
        cmd.png(tmp)
        if not os.path.exists(tmp):
            return False
        # a thin tail is faint after downsampling, so the alpha gate is low
        a = _img_load(tmp)[:, :, 3] > 0.004
    except Exception:
        return False
    finally:
        for k, val in keep.items():
            try:
                cmd.set(k, val)
            except Exception:
                pass
        if os.path.exists(tmp):
            os.remove(tmp)
    if not a.any():
        return False
    mx = max(1, int(round(margin * probe)))
    my = max(1, int(round(margin * h)))
    return bool(a[:my, :].any() or a[-my:, :].any()
                or a[:, :mx].any() or a[:, -mx:].any())


def _post_chain(rgba, opts, w, h):
    """Run the post-processing chain and return RGB (or RGBA if transparent)."""
    np = _np()
    post = dict(opts.get("post") or {})
    bg_spec = opts.get("bg_spec")
    transparent = opts.get("transparent")
    alpha = rgba[:, :, 3]

    if transparent or bg_spec is None:
        rgb = rgba[:, :, :3].copy()
    else:
        bg = _make_bg(bg_spec, w, h)
        halo = post.get("halo")
        if halo:
            hw, hcol, hop = halo
            bg = _apply_halo(bg, rgba[:, :, 3], hw * min(w, h), hcol, hop)
        sh = post.get("shadow")
        if sh:
            dx, dy, blur, op = sh
            bg = _apply_shadow(rgba, bg, dx * w, dy * h, blur * min(w, h), op)
        rgb = _over(rgba, bg)

    bl = post.get("bloom")
    if bl:
        thr, rad, strength = bl
        rgb = _apply_bloom(rgb, thr, rad * min(w, h), strength,
                           alpha=alpha if transparent else None)
    if post.get("posterize"):
        rgb = _apply_posterize(rgb, post["posterize"])
    if post.get("vignette") and not transparent:
        rgb = _apply_vignette(rgb, float(post["vignette"]))
    if post.get("grade"):
        rgb = _apply_grade(rgb, **post["grade"])
    if post.get("sharpen"):
        rgb = _apply_sharpen(rgb, float(post["sharpen"]))
    if post.get("grain"):
        rgb = _apply_grain(rgb, float(post["grain"]))

    if transparent or bg_spec is None:
        return np.dstack([rgb, alpha])
    return np.dstack([rgb, np.ones_like(alpha)])


def _legend_entries(opts):
    """What the colours in this image mean, derived from the colouring that was
    actually applied. A quantitative ramp without a key is not interpretable,
    and a chain figure without one makes the reader guess."""
    coloring = opts.get("coloring", "")
    if coloring == "plddt":
        # four discrete bands, labelled as AlphaFold DB labels them: a
        # continuous bar would imply the colour interpolates, and the
        # band labels do not fit under a bar anyway
        return ("swatch", "Model confidence  pLDDT",
                [("#0053D6", "Very high  > 90"),
                 ("#65CBF3", "Confident  70-90"),
                 ("#FFDB13", "Low  50-70"),
                 ("#FF7D45", "Very low  < 50")])
    if coloring == "bfactor":
        lo, hi = opts.get("bfactor_range", (None, None))
        if lo is None:
            return None
        return ("ramp", u"B-factor  Å²",
                [(BFACTOR_RAMP[0], "%.0f" % lo)]
                + [(c, "") for c in BFACTOR_RAMP[1:-1]]
                + [(BFACTOR_RAMP[-1], "%.0f" % hi)])
    if coloring == "hydrophobicity":
        return ("ramp", "Hydropathy  Kyte-Doolittle",
                [(HYDROPATHY_RAMP[0], "-4.5 polar")]
                + [(c, "") for c in HYDROPATHY_RAMP[1:-1]]
                + [(HYDROPATHY_RAMP[-1], "+4.5 greasy")])
    if coloring == "charge":
        return ("swatch", "Residue class",
                [(c, n) for n, _, c in CHARGE_GROUPS])
    if coloring == "ss":
        return ("swatch", "Secondary structure",
                [(SS_COLORS["H"], "helix"), (SS_COLORS["S"], "sheet"),
                 (SS_COLORS["L"], "loop")])
    if coloring in ("assembly", "chain", "chain-carbon", "entity", "polymer"):
        groups = _resolve_groups(opts.get("colour_groups") or [],
                                 opts.get("rep", ""))
        if len(groups) < 2 or len(groups) > 8:
            return None
        return ("swatch", _s(opts.get("legend_title")) or
                ("Polymer" if coloring == "polymer" else "Chains"), groups)
    return None


def _legend_place(alpha, w, h, bw, bh, margin, avoid=(), fixed_y=None,
                  reserved=()):
    """Where to put a key so it does not print on the specimen.

    Pinning the panel to the emptiest *corner* only works when some corner is
    empty. On a subject that reaches all four, every corner is a bad corner and
    the key lands on the molecule anyway. So the panel is also allowed to slide
    along an edge, and the position with least subject under it wins; corners
    keep a small bonus so a clear corner is still preferred."""
    span_x = max(0, w - 2 * margin - bw)
    span_y = max(0, h - 2 * margin - bh)
    cands = []
    if fixed_y is not None:
        # the scale bar is anchored to one edge and only slides along it
        cands.append((margin + span_x, fixed_y, 0.0))
        cands.append((margin, fixed_y, 0.004))
        for i in range(1, 6):
            cands.append((margin + span_x * i / 6.0, fixed_y, 0.010))
    else:
        corners = {"tl": (margin, margin), "tr": (margin + span_x, margin),
                   "bl": (margin, margin + span_y),
                   "br": (margin + span_x, margin + span_y)}
        for name, (x, y) in corners.items():
            if name not in avoid:
                cands.append((x, y, 0.0))
        for i in range(1, 6):
            fx, fy = margin + span_x * i / 6.0, margin + span_y * i / 6.0
            for x, y in ((fx, margin), (fx, margin + span_y),
                         (margin, fy), (margin + span_x, fy)):
                cands.append((x, y, 0.010))
    if not cands:
        cands = [(margin + span_x, margin, 0.0)]

    np = _np()
    if alpha is None or np is None:
        return int(cands[0][0]), int(cands[0][1])
    # anything already printed counts as occupied: a key that clears the
    # molecule but lands on the subject name has not been placed, only moved
    a = alpha > 0.02
    sy, sx = a.shape[0] / float(h), a.shape[1] / float(w)
    if reserved:
        a = a.copy()
        for rx, ry, rw, rh in reserved:
            a[max(0, int(ry * sy)):int((ry + rh) * sy) + 1,
              max(0, int(rx * sx)):int((rx + rw) * sx) + 1] = True
    best, best_score = cands[0][:2], None
    for x, y, penalty in cands:
        y0, y1 = int(y * sy), max(int(y * sy) + 1, int((y + bh) * sy))
        x0, x1 = int(x * sx), max(int(x * sx) + 1, int((x + bw) * sx))
        score = float(a[y0:y1, x0:x1].mean()) + penalty
        if best_score is None or score < best_score:
            best, best_score = (x, y), score
    return int(best[0]), int(best[1])


def _draw_legend(rgba, opts, w, h):
    """Draw a colour key in the emptiest corner, on its own panel."""
    spec = _legend_entries(opts)
    if not spec:
        return rgba
    kind, title, items = spec
    if not items:
        return rgba
    dark = opts.get("dark_bg")
    fg = "#F2F2F2" if dark else "#1A1A1A"
    panel = "#000000" if dark else "#FFFFFF"
    margin = int(round(0.045 * min(w, h)))
    # text, not the swatch, must clear the journal floor: >=3 % of height puts
    # a 200 px panel at 6 px
    # measured at 1.3-1.9 % of image height when set from min(w, h); scale
    # from height so the number means what it says
    size = max(14, int(round(min(0.032 * h, 0.044 * w))))
    # a key with several entries grows until there is nowhere in the frame it
    # does not cover the specimen; past a quarter of the frame it has stopped
    # being an annotation and become a second subject
    rows = len(items)
    hi = 0.26 * h / max(1.0, (rows * 1.8 + 2.6))
    if size > hi:
        size = max(13, int(round(hi)))
    title_size = max(14, int(round(size * 1.12)))
    sw = int(round(size * 1.35))
    gap = int(round(size * 0.45))
    pad = int(round(size * 0.55))

    # measure first: the panel must fit the content and stay inside the frame
    labels = [lab for _, lab in items if lab]
    text_w = int(max([size * 0.62 * len(t) for t in labels] or [0]))
    title_w = int(title_size * 0.62 * len(title))
    if kind == "ramp":
        bar_w = int(round(size * 8.0))
        body_w = max(bar_w, text_w)
        body_h = int(size * 1.15) + int(size * 1.5)
    else:
        body_w = sw + gap + text_w
        body_h = len(items) * (sw + gap) - gap
    cap_w = int(w * 0.36)
    # the box was clamped to a cap while the title kept its full length, so on
    # a wide title the last characters were set on bare specimen outside the
    # panel. Shrink the title until it fits the box that will actually be drawn.
    while title_size > 11 and title_w + 2 * pad > cap_w:
        title_size -= 1
        title_w = int(title_size * 0.62 * len(title))
    block_w = min(max(body_w, title_w) + 2 * pad, cap_w)
    block_h = int(title_size * 1.7) + body_h + 2 * pad
    taken = list(opts.get("_taken_corners") or ())
    if opts.get("scalebar") and "br" not in taken:
        taken.append("br")
    if _s(opts.get("subject_name")) and not _s(opts.get("label")):
        taken.append("tl")          # the subject name lives there
    bx, by = _legend_place(opts.get("subject_alpha"), w, h, block_w, block_h,
                           margin, avoid=tuple(taken),
                           reserved=opts.get("_reserved") or ())
    right = bx > (w - block_w) / 2.0

    rects = [(bx, by, block_w, block_h, panel, 1.0),
             (bx, by, block_w, 1, fg, 0.30),
             (bx, by + block_h - 1, block_w, 1, fg, 0.30),
             (bx, by, 1, block_h, fg, 0.30),
             (bx + block_w - 1, by, 1, block_h, fg, 0.30)]
    texts = [dict(text=title, x=(bx + block_w - pad) if right else (bx + pad),
                  y=by + pad, size=title_size, color=fg,
                  align="right" if right else "left", bold=True)]
    y = by + pad + int(title_size * 1.7)

    if kind == "ramp":
        bar_w = block_w - 2 * pad
        bar_h = int(round(size * 1.15))
        bar_x = bx + pad
        n = len(items)
        seg = bar_w / float(n)
        for i, (hexcol, _) in enumerate(items):
            rects.append((bar_x + i * seg, y, seg + 1, bar_h, hexcol, 1.0))
        y += bar_h + int(size * 0.35)
        ends = [(0, items[0][1], "left"), (n - 1, items[-1][1], "right")]
        for i, label, align in ends:
            if not label:
                continue
            x = bar_x if align == "left" else bar_x + bar_w
            texts.append(dict(text=label, x=x, y=y, size=int(size * 0.82),
                              color=fg, align=align))
    else:
        for hexcol, label in items:
            if right:
                rects.append((bx + block_w - pad - sw, y, sw, sw, hexcol, 1.0))
                texts.append(dict(text=label, x=bx + block_w - pad - sw - gap,
                                  y=y + (sw - size) // 2, size=size,
                                  color=fg, align="right"))
            else:
                rects.append((bx + pad, y, sw, sw, hexcol, 1.0))
                texts.append(dict(text=label, x=bx + pad + sw + gap,
                                  y=y + (sw - size) // 2, size=size,
                                  color=fg, align="left"))
            y += sw + gap
    rgba = _draw_rects(rgba, rects)
    return _draw_text(rgba, texts)


GENERIC_NAMES = {"mol", "obj", "all", "structure", "prot", "protein",
                 "model", "tmp", "pdb"}


def _subject_name(sel):
    """A readable name for the thing in the picture.

    Nine plates in a comparison set can be two molecules, and a reader who
    cannot tell which is which learns nothing from the comparison."""
    try:
        objs = cmd.get_object_list(sel) or []
    except Exception:
        return ""
    if not objs:
        return ""
    obj = objs[0]
    # cmd.get_property is an incentive-build API and absent here, so the object
    # name is what there is. `fetch 1aon` names it 1AON, which is the name a
    # reader wants; a hand-typed placeholder is worse than nothing.
    title = ""
    try:
        title = (cmd.get_title(obj, 1) or "").strip()
    except Exception:
        pass
    if 3 < len(title) < 60:
        return title.title() if title.isupper() else title
    if obj.lower() in GENERIC_NAMES:
        return ""
    return obj.upper() if len(obj) <= 6 else obj


def _auto_scalebar(height_px, width_px=0):
    """A round bar length spanning roughly a fifth of the frame.

    Without a scale bar a 38 Angstrom protein and a 145 Angstrom complex look
    the same size, which is the mistake every non-specialist reader makes.

    The bar is drawn horizontally, so a fifth of the *width* is what a reader
    measures. Taking a fifth of the height instead put the bar at 9-12 % of
    the frame on every landscape canvas."""
    app = _angstrom_per_pixel(height_px)
    if app <= 0:
        return 0.0
    target = app * (width_px or height_px) * 0.20
    if target <= 0:
        return 0.0
    mag = 10.0 ** math.floor(math.log10(target))
    for step in (1.0, 2.0, 5.0, 10.0):
        if target <= step * mag * 1.4:
            return step * mag
    return 10.0 * mag


def _annotate(rgba, opts, w, h):
    """Scale bar, caption and panel label drawn on the finished image."""
    items, rects, bar_corners, reserved = [], [], [], []
    dark = opts.get("dark_bg")
    fg = "#FFFFFF" if dark else "#1A1A1A"
    margin = int(round(0.045 * min(w, h)))

    # the caption is drawn after the bar but occupies the same edge, so its
    # box has to exist before the bar chooses where to sit
    cap_pre = _s(opts.get("caption"))
    if cap_pre:
        cs = max(13, int(round(0.034 * min(w, h))))
        reserved.append((margin, h - margin - cs * 1.5,
                         cs * 0.62 * len(cap_pre) + margin, cs * 1.6))

    bar = opts.get("scalebar")
    if bar:
        length_a = float(bar)
        app = opts.get("angstrom_per_pixel") or 0.0
        if app > 0:
            px = length_a / app
            if px > 0.02 * w:
                bh = max(3, int(round(0.006 * min(w, h))))
                size = max(13, int(round(0.034 * h)))
                # the bar is pinned to the bottom of the frame but free to
                # slide along it: bottom-right is only the right place when
                # the subject is not already there
                need_h = int(bh + size * 2.5)
                by = h - margin - bh
                bx, _ = _legend_place(opts.get("subject_alpha"), w, h,
                                      px, need_h, margin,
                                      fixed_y=max(0, by + bh - need_h),
                                      reserved=tuple(reserved))
                rects.append((bx, by, px, bh, fg, 0.95))
                label = ("%g nm" % (length_a / 10.0)) if length_a >= 10 \
                    else (u"%g Å" % length_a)
                items.append(dict(text=label, x=bx + px / 2.0,
                                  y=by - size * 1.5, size=size, color=fg,
                                  align="center", bold=True))
                bar_corners.append("br" if bx + px / 2.0 > w / 2.0 else "bl")
                reserved.append((bx, by - size * 2.0, px, bh + size * 2.4))

    cap = _s(opts.get("caption"))
    if cap:
        size = max(13, int(round(0.034 * min(w, h))))
        items.append(dict(text=cap, x=margin, y=h - margin - size * 1.25,
                          size=size, color=fg, bold=False))
        reserved.append((margin, h - margin - size * 1.4,
                         size * 0.62 * len(cap), size * 1.4))
    name = _s(opts.get("subject_name"))
    if name and not _s(opts.get("label")):
        size = max(13, int(round(0.030 * min(w, h))))
        items.append(dict(text=name, x=margin, y=margin, size=size, color=fg,
                          bold=True))
        reserved.append((margin, margin, size * 0.62 * len(name), size * 1.4))
    lab = _s(opts.get("label"))
    if lab:
        size = max(16, int(round(0.062 * min(w, h))))
        items.append(dict(text=lab, x=margin, y=margin, size=size, color=fg,
                          bold=True))
        reserved.append((margin, margin, size * 0.62 * len(lab), size * 1.4))
    if rects:
        rgba = _draw_rects(rgba, rects)
    if items:
        rgba = _draw_text(rgba, items)
    if opts.get("legend"):
        rgba = _draw_legend(rgba, dict(opts, _taken_corners=bar_corners,
                                       _reserved=reserved), w, h)
    return rgba


def viz_render(filename="viz.png", size="", width=0, height=0, dpi=300,
               outline=-1.0, background="", transparent=0, scalebar=-1,
               caption="", label="", legend=-1, name="", antialias=-1, post=1,
               fit=1, quiet=0):
    """
DESCRIPTION

    Ray-trace the current scene to a file. Outlines are rendered as a separate
    pass and composited, so their weight stays constant in print as on screen,
    and post-processing (gradient backgrounds, glow, grading) is applied.

USAGE

    viz_render [filename [, size [, width [, height [, dpi [, outline
               [, background [, transparent [, scalebar [, caption
               [, label ]]]]]]]]]]]

ARGUMENTS

    filename    = output path; .png is added if missing
    size        = preset name (slide, column, dcolumn, hd, 4k, square, cover,
                  poster, story, preview, thumb), WxH such as 1600x900, or
                  "fit" to take the canvas shape from the subject itself so a
                  wide complex does not sit in a square with half the page
                  empty (width= sets the long edge)
    width/height= explicit pixels, override the preset
    dpi         = resolution metadata written into the PNG {default: 300}
    outline     = line weight as a fraction of image width; 0 disables,
                  -1 keeps the style default
    background  = background preset or #hex; overrides the style
    transparent = 0/1 keep the background transparent
    scalebar    = length in Angstrom of a scale bar, 0 for none, -1 to pick a
                  round length automatically {default: -1}
    legend      = 1 draw a colour key, 0 never, -1 automatic: drawn whenever
                  the colouring encodes a quantity or a small set of groups
    name        = subject name drawn top-left; empty derives it from the
                  structure, "-" suppresses it
    caption     = text drawn bottom-left
    label       = panel letter drawn top-left
    post        = 0/1 apply post-processing {default: 1}
    fit         = 0/1 widen the field when the target is narrower than the
                  viewport, so nothing is cropped {default: 1}

EXAMPLES

    viz_render ~/figure.png, column, scalebar=20
    viz_render ~/slide.png, slide, caption=GroEL/GroES chaperonin
    viz_render ~/logo.png, square, transparent=1
    """
    w, h = _resolve_size(size, width, height)
    path = os.path.expanduser(_s(filename, "viz.png"))
    if not os.path.splitext(path)[1]:
        path += ".png"
    dirname = os.path.dirname(os.path.abspath(path))
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname)

    st = dict(_LAST) if _LAST else {}
    o_frac = _f(outline, -1.0)
    if o_frac < 0:
        o_frac = float(st.get("outline", 0.0))
    transparent = _b(transparent)
    bg_txt = _s(background) or st.get("background", "")
    bg_spec = BACKGROUNDS.get(bg_txt.lower(), bg_txt) if bg_txt else \
        st.get("bg_spec", "#FFFFFF")
    if transparent:
        bg_spec = None
    post_spec = dict(st.get("post") or {}) if _b(post, True) else {}
    have_img = _img_backend()

    target = w / float(h)
    want_legend = _i(legend, -1)
    if want_legend < 0:
        annotation = (st.get("annotations") or {}).get("legend")
        if annotation is not None:
            want_legend = int(bool(annotation))
        else:
            groups = _resolve_groups(st.get("colour_groups") or [],
                                     st.get("rep", ""))
            # a reader cannot recover what a colour means without a key, and
            # the colour is doing the work in every multi-entity image
            want_legend = int(st.get("coloring") in DATA_COLORINGS
                              or st.get("coloring") in ("ss", "polymer")
                              or 2 <= len(groups) <= 8)

    cur = _viewport_aspect()
    if _b(fit):
        # Frame for the output aspect, not the viewport's. Without this a
        # square-ish fit rendered to 16:9 leaves the structure marooned in the
        # middle, and a narrower target crops it.
        fitted = False
        fit_sel = st.get("selection") or "all"
        if cmd.count_atoms(fit_sel):
            fitted = _fit_projected(_visible(fit_sel), 0.045,
                                    _rep_pad(st.get("rep", ""),
                                             st.get("blob", 1.4)),
                                    aspect=target)
        # then correct against a measured render, which no geometric estimate
        # can match
        # a key needs somewhere to live; fitting the subject to the whole
        # frame guarantees it lands on top of something
        fill_target = TARGET_FILL - (0.09 if want_legend else 0.0)
        if have_img and (not _s(st.get("focus")) or st.get("_enforce_margin")):
            if st.get("_enforce_margin"):
                for _ in range(4):
                    if not _probe_touches_edge(target, 0.04):
                        break
                    _scale_field(1.07)
            else:
                fitted = _fit_measured(target, fill_target) or fitted
        if not fitted and target < cur - 1e-3:
            _scale_field(cur / target)
    elif target < cur - 0.02 and not _b(quiet):
        print(" viz_render: note - target aspect %.2f is narrower than the "
              "viewport (%.2f); some width will be cropped. Use viz_frame "
              "first, or fit=1." % (target, cur))

    bar = _f(scalebar, -1.0)
    if bar < 0:
        annotation = (st.get("annotations") or {}).get("scalebar")
        bar = 0.0 if transparent or annotation == 0 else _auto_scalebar(h, w)
    # Annotations are drawn in post, so a style that needs no outline and no
    # effects must still take the post path or its scale bar, caption, panel
    # label and colour key silently vanish.
    annotated = bool(bar > 0 or _s(caption) or _s(label) or want_legend)
    use_post = have_img and (o_frac > 0 or post_spec or transparent
                            or not isinstance(bg_spec, str) or annotated)
    if annotated and not have_img and not _b(quiet):
        print(" viz_render: annotations need numpy and PyMOL's Qt build")
    if not have_img and not _b(quiet):
        print(" viz_render: post-processing unavailable (%s); rendering "
              "single-pass." % _IMG["why"])

    saved = {}
    for key in ("ray_trace_mode", "ray_trace_gain", "ray_trace_color",
                "antialias", "ray_opaque_background", "ray_trace_fog"):
        saved[key] = cmd.get(key)
    aa = _i(antialias, -1)

    try:
        # ---- colour pass
        if use_post:
            cmd.set("ray_trace_mode", 2 if st.get("lineart") else 0)
            cmd.set("ray_opaque_background", 0)
        cmd.set("antialias", aa if aa >= 0 else 2)
        if not _b(quiet):
            print(" viz_render: %dx%d ..." % (w, h))
        cmd.ray(w, h)
        if not use_post:
            cmd.png(path, dpi=_i(dpi, 300))
            if not _b(quiet):
                print(" viz_render: wrote %s" % path)
            return path

        tmp_color = path + ".viz_color.png"
        cmd.png(tmp_color)
        if not os.path.exists(tmp_color):
            raise CmdException("PyMOL did not produce an image; the ray trace "
                               "may have run out of memory at %dx%d" % (w, h))
        rgba = _img_load(tmp_color)
        os.remove(tmp_color)

        # ---- depth-thresholded ink: outlines subunits, not every atom
        if o_frac > 0 and st.get("ink") in ("depth", "tiered"):
            np = _np()
            inside = rgba[:, :, 3] > 0.35
            width_px = max(1.0, o_frac * w)
            if st.get("ink") == "tiered":
                mask = _ink_masks(w, h, inside, width_px)
            else:
                mask = _depth_ink_mask(w, h, inside,
                                       _f(st.get("ink_threshold"), 12.0),
                                       width_px)
            if mask is not None:
                ink = np.array(_hex2rgb(_ocolor_hex(
                    st.get("outline_color", "black"))), np.float32)
                # Illustrate grades its contours instead of thresholding them,
                # which is what makes them read as drawn lines rather than as a
                # binary edge-detect result. Soften the mask edge to match.
                m = np.clip(_blur(mask.astype(np.float32), 1.1) * 1.35,
                            0.0, 1.0)[:, :, None]
                rgba[:, :, :3] = rgba[:, :, :3] * (1 - m) + ink * m
                rgba[:, :, 3] = np.maximum(rgba[:, :, 3], m[:, :, 0])
                o_frac = 0.0
            elif not _b(quiet):
                print(" viz_render: depth ink unavailable, using edge outlines")

        # ---- outline pass at a fixed resolution, so weight is scale-free
        if o_frac > 0:
            line_w = int(round(3.0 / max(1e-4, o_frac)))
            line_w = max(220, min(line_w, w))
            div = w / float(line_w)
            line_h = max(120, int(round(h / div)))
            cmd.set("ray_trace_mode", 2)
            cmd.set("ray_trace_color", "black")
            cmd.set("antialias", 0)
            cmd.set("ray_opaque_background", 1)
            cmd.set("ray_trace_fog", 0)
            cmd.ray(line_w, line_h)
            tmp_line = path + ".viz_line.png"
            cmd.png(tmp_line)
            mask = _ink_mask(tmp_line, div, w, h)
            os.remove(tmp_line)
            inside_obj = rgba[:, :, 3] > 0.35
            body = float(inside_obj.sum()) or 1.0
            for _ in range(4):
                cover = float(((mask > 0.5) & inside_obj).sum()) / body
                if cover <= INK_INTERIOR_CAP * 1.6:
                    break
                mask = mask * 0.62
            np = _np()
            ink = np.array(_hex2rgb(_ocolor_hex(st.get("outline_color",
                                                       "black"))), np.float32)
            m = mask[:, :, None]
            rgba[:, :, :3] = rgba[:, :, :3] * (1 - m) + ink * m
            rgba[:, :, 3] = np.maximum(rgba[:, :, 3], mask)

        dof_amount = _f(st.get("dof"), 0.0)
        if dof_amount > 0:
            np = _np()
            inside = rgba[:, :, 3] > 0.35
            depth = _render_depth(w, h)
            if depth is not None and inside.any():
                focus = float(np.median(depth[inside]))
                if st.get("focus_depth") is not None:
                    focus = float(st["focus_depth"])
                rgba[:, :, :3] = _apply_dof(rgba[:, :, :3], depth, inside,
                                            focus, dof_amount)
        opts = {"post": post_spec, "bg_spec": bg_spec,
                "transparent": transparent,
                "dark_bg": _bg_is_dark(bg_spec),
                "scalebar": bar,
                "caption": _s(caption) or _s(st.get("auto_caption")),
                "label": label,
                "legend": want_legend,
                "coloring": st.get("coloring", ""),
                "colour_groups": st.get("colour_groups"),
                "legend_title": st.get("legend_title", ""),
                "rep": st.get("rep", ""),
                "bfactor_range": st.get("bfactor_range", (None, None)),
                # "-" is documented as the suppression token; it was being
                # taken as the name and printed as a stray dash
                "subject_name": "" if _s(name) == "-" else (
                    _s(name) or ("" if (st.get("annotations") or {}).get(
                        "name") == 0 else _subject_name(
                            st.get("selection") or "all"))),
                "subject_alpha": rgba[:, :, 3],
                "angstrom_per_pixel": _angstrom_per_pixel(h)}
        out = _post_chain(rgba, opts, w, h)
        out = _annotate(out, opts, w, h)
        _img_save(out, path, _i(dpi, 300))
        if not _b(quiet):
            print(" viz_render: wrote %s (%dx%d, %d dpi)" % (path, w, h,
                                                             _i(dpi, 300)))
        return path
    finally:
        for key, val in saved.items():
            try:
                cmd.set(key, val)
            except Exception:
                pass


def _ocolor_hex(name):
    """Map a PyMOL colour name or hex string to hex for post-processing."""
    txt = _s(name, "black")
    if txt.startswith("#"):
        return txt
    try:
        rgb = cmd.get_color_tuple(txt)
        if rgb:
            return _rgb2hex(rgb)
    except Exception:
        pass
    return "#000000"


def _bg_is_dark(spec):
    if spec is None:
        return False
    if isinstance(spec, (list, tuple)) and len(spec) == 3 and \
            isinstance(spec[0], str) and spec[0] in ("linear", "radial"):
        return _lum(_hex2rgb(spec[1])) < 0.45
    try:
        return _lum(_hex2rgb(spec)) < 0.45
    except Exception:
        return False


# ==========================================================================
# the main entry point
# ==========================================================================


def _pick_style(info):
    """Choose a style from what the structure actually contains."""
    if not info["protein"] and not info["nucleic"]:
        return "chem"
    if info["nucleic"] > info["protein"]:
        return "dna"
    if info["plddt_like"] and info["chains"] <= 2 and info["bmax"] > 20:
        return "plddt"
    if info["atoms"] > 40000 or info["chains"] >= 6:
        return "goodsell"
    if info["ligand"] >= 8 and info["residues"] <= 600 and info["chains"] <= 3:
        return "pocket"
    if info["residues"] > 1200:
        return "tube"
    return "publication"


def _merge_post(base, glow, vignette, contrast, saturation, grain, posterize,
                sharpen):
    """Style post-processing, with the user's overrides applied on top."""
    post = {k: (dict(v) if isinstance(v, dict) else v)
            for k, v in (base or {}).items()}
    if glow >= 0:
        if glow == 0:
            post.pop("bloom", None)
        else:
            thr, rad, _ = post.get("bloom", (0.60, 0.030, 0.5))
            post["bloom"] = (thr, rad, glow)
    if vignette >= 0:
        post["vignette"] = vignette
    if grain >= 0:
        post["grain"] = grain
    if sharpen >= 0:
        post["sharpen"] = sharpen
    if posterize >= 0:
        if posterize < 2:
            post.pop("posterize", None)
        else:
            post["posterize"] = int(posterize)
    if contrast >= 0 or saturation >= 0:
        grade = dict(post.get("grade", {}))
        if contrast >= 0:
            grade["contrast"] = contrast
        if saturation >= 0:
            grade["saturation"] = saturation
        post["grade"] = grade
    return post


def viz(style="auto", selection="", coloring="", palette="", outline=-1.0,
        outline_color="", ao=-1.0, blob=-1.0, background="", rep="", light="",
        fog=-1.0, hydrogens=0, waters=0, quality=1, view="", frame="",
        fit=-1, orient=-1, dof=-1.0, glow=-1.0, vignette=-1.0, contrast=-1.0,
        saturation=-1.0, grain=-1.0, posterize=-1, sharpen=-1.0, quiet=0):
    """
DESCRIPTION

    Apply a complete visual style: representation, colouring, lighting,
    ambient occlusion, outlines and background in one step.

    Outlines and ambient occlusion are baked at render time - run viz_render
    (or `ray`) to see the finished image.

USAGE

    viz [style [, selection [, coloring [, palette [, outline
        [, outline_color [, ao [, blob [, background [, rep [, light
        [, fog [, hydrogens [, waters [, quality [, view [, frame ]]]]]]]]]]]]]]]]]

ARGUMENTS

    style      = auto, a starter (paper | story | illustration | site |
                 confidence), or one of the presets listed by viz_list
    selection  = what to restyle {default: everything}
    coloring   = chain | chain-carbon | entity | spectrum | spectrum-chain |
                 ss | element | mono | bfactor | plddt | hydrophobicity |
                 charge | nucleic | pocket | keep
    palette    = a palette name, or your own colours separated by /
                 (commas are argument separators in PyMOL): #1B4965/#5FA8D3
    outline    = ink weight as a fraction of image width; 0 off, -1 style default
    ao         = ambient-occlusion strength multiplier, 0 disables
    blob       = solvent radius for surfaces; larger is blobbier
    background = background preset or #hex
    rep        = override the representation
    light      = override the lighting rig
    fog        = 0..1 depth fade
    hydrogens  = 0/1 show non-polar hydrogens
    waters     = 0/1 show waters
    quality    = 0 fast | 1 good | 2 maximum
    view       = apply a viz_view preset afterwards
    frame      = apply a viz_frame preset afterwards
    fit        = 1 refit the zoom, 0 keep the camera exactly, -1 refit only
                 when the representation changed {default: -1}
    orient     = 1 always orient, 0 never, -1 orient the first time this
                 selection is styled {default: -1}

    Post-processing, applied by viz_render. -1 keeps the style's own value.

    dof        = 0..1 depth-of-field strength; throws everything off the focal
                 plane progressively out of focus
    glow       = 0..2 bloom strength around bright areas, 0 disables
    vignette   = 0..1 darkening toward the corners
    contrast   = around 1.0
    saturation = around 1.0, 0 is greyscale
    grain      = 0..0.05 film grain
    posterize  = number of colour levels, 0 disables
    sharpen    = 0..2 unsharp mask

EXAMPLES

    viz                                     # pick a style automatically
    viz paper                               # clean journal figure
    viz story                               # cinematic slide or cover image
    viz site                                # binding-site close-up
    viz illustrative
    viz goodsell, palette=pastel, blob=3.5
    viz publication, coloring=ss
    viz hero, palette=neon, view=hero, frame=slide
    viz chem, organic                       # just the ligand

SEE ALSO

    viz_render, viz_auto, viz_color, viz_view, viz_frame, viz_gallery, viz_list
    """
    global _LAST_SCRIPT, _LAST

    sel = _s(selection)
    name = _s(style, "auto")
    # be forgiving: `viz polymer` should mean "auto style, this selection"
    if name.lower() not in STYLES and name.lower() not in STYLE_ALIASES \
            and name.lower() != "auto":
        try:
            if cmd.count_atoms(name) and not sel:
                sel, name = name, "auto"
        except Exception:
            pass
    if not sel:
        sel = "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)

    info = _survey(sel)
    if name.lower() == "auto":
        name = _pick_style(info)
    else:
        name = STYLE_ALIASES.get(name.lower(), name)
    st = _style(name)
    name = _resolve(name, STYLES, "style")

    asked_coloring = _s(coloring)
    coloring = asked_coloring or st["coloring"]
    # 21 unrelated hues on a 21-chain complex reads as a colouring bug; group
    # the copies instead, unless the user asked for something specific
    if not asked_coloring and coloring in ("chain", "chain-carbon") \
            and info["chains"] >= 6:
        coloring = "assembly"
    # CPK on a whole protein is the canonical software-default look: it buries
    # chains, folds and cofactors under confetti
    if not asked_coloring and coloring == "element" and info["residues"] > 40:
        coloring = "assembly"
    palette = _s(palette) or st["palette"]
    rep = _s(rep) or st["rep"]
    light = _resolve(_s(light) or st["light"], LIGHTING, "lighting rig")
    o_frac = _f(outline, -1.0)
    if o_frac < 0:
        o_frac = float(st["outline"])
    ocolor = _s(outline_color) or st["ocolor"]
    ao_mul = _f(ao, -1.0)
    blob = _f(blob, -1.0)
    if blob < 0:
        blob = float(st["blob"])
    fogv = _f(fog, -1.0)
    if fogv < 0:
        fogv = float(st["fog"])
    # Depth fade multiplies the rendered colour, so on a data-driven ramp it
    # silently turns a quantitative scale into a gradient: an AlphaFold tail
    # fades from orange toward the background and stops meaning 50 pLDDT.
    if coloring in DATA_COLORINGS and _f(fog, -1.0) < 0:
        fogv = 0.0
    q = _i(quality, 1)
    bg_txt = _s(background)
    bg_spec = BACKGROUNDS.get(bg_txt.lower(), bg_txt) if bg_txt else \
        BACKGROUNDS.get(st["bg"], st["bg"])
    dark = _bg_is_dark(bg_spec)

    # measured before this call touches anything: once the style has been
    # applied, every test for "is this the same subject as last time" is
    # answered by what this call just did
    subject_key = (sel, tuple(cmd.get_object_list(sel) or ()),
                   cmd.count_atoms(sel))
    rec = _Rec()
    rec.note("PyMOL Viz Suite %s - style '%s'" % (__version__, name))
    rec.note(st["desc"])
    rec.note()

    # start from a known state: geometry settings from a previous style must
    # not survive into this one
    for key in _STICKY:
        try:
            cmd.unset(key)
            cmd.unset(key, sel)
        except Exception:
            pass
    cmd.set("surface_carve_selection", "")
    cmd.delete("viz_contacts")
    cmd.delete("viz_gaps")
    _LAST.pop("legend_title", None)
    _LAST.pop("buried_area", None)
    _LAST.pop("auto_caption", None)
    _LAST.pop("interaction_focus", None)
    _LAST.pop("interaction_pair", None)
    _LAST.pop("interaction_mode", None)

    # ---- scene -----------------------------------------------------------
    rec.note("scene")
    base_col = bg_spec if isinstance(bg_spec, str) else (
        bg_spec[2] if bg_spec else "#FFFFFF")
    rec.bg(base_col if base_col else "#FFFFFF")
    rec.set("ray_opaque_background", 1)
    rec.set("antialias", 2 if q else 1)
    rec.set("orthoscopic", 1 if st["ortho"] else 0)
    rec.set("field_of_view", 20 if st["ortho"] else 33)
    rec.set("hash_max", 500 if info["atoms"] > 50000 else 300)
    if fogv > 0:
        rec.set("depth_cue", 1)
        rec.set("fog", round(fogv, 3))
        rec.set("fog_start", 0.42)
        rec.set("ray_trace_fog", 1)
    else:
        rec.set("depth_cue", 0)
        rec.set("ray_trace_fog", 0)
    rec.note()

    # ---- lighting --------------------------------------------------------
    rec.note("lighting rig '%s'" % light)
    for key, val in LIGHTING[light].items():
        rec.set(key, val)
    rec.note()

    # ---- ambient occlusion ----------------------------------------------
    rec.note("ambient occlusion")
    if st["ao"] and ao_mul != 0.0:
        mode, scale, smooth = st["ao"]
        mul = 1.0 if ao_mul < 0 else ao_mul
        rec.set("ambient_occlusion_mode", mode)
        rec.set("ambient_occlusion_scale", round(scale * mul, 2))
        rec.set("ambient_occlusion_smooth", _i(smooth, 15))
    else:
        rec.set("ambient_occlusion_mode", 0)
    rec.note()

    # ---- outlines --------------------------------------------------------
    rec.note("ink outline (composited by viz_render; ray shows a preview)")
    if st["lineart"]:
        rec.set("ray_trace_mode", 2)
    elif o_frac > 0:
        rec.set("ray_trace_mode", 1)
    else:
        rec.set("ray_trace_mode", 0)
    if o_frac > 0 or st["lineart"]:
        gain, depth, slope, disco = st["edge"] or EDGE_DEFAULT
        rec.set("ray_trace_gain", gain)
        rec.set("ray_trace_color", _color_name(ocolor))
        rec.set("ray_trace_depth_factor", depth)
        rec.set("ray_trace_slope_factor", slope)
        rec.set("ray_trace_disco_factor", disco)
    rec.note()

    # ---- geometry --------------------------------------------------------
    rec.note("representation")
    rec.set("surface_quality", 2 if q >= 2 else (1 if q else 0))
    rec.set("two_sided_lighting", 1)
    rec.set("transparency_mode", 3)
    for key, val in (st["set"] or {}).items():
        # a setting that takes a colour needs a registered name, not a hex string
        if isinstance(val, str) and val.startswith("#"):
            val = _color_name(val)
        rec.set(key, val)
    focus_sel = _focus_selection(sel) if st["focus"] == "ligand" else ""
    rep_used = _apply_rep(rec, sel, rep, blob=blob, hydrogens=_b(hydrogens),
                          waters=_b(waters), fine=q >= 1, focus=focus_sel,
                          shade_ribbon=not st.get("flat_ribbon"))
    if _f(outline, -1.0) < 0:
        base_rep = rep_used.split("+", 1)[1] if \
            _s(rep_used).startswith("nucleic+") else rep_used
        o_frac *= OUTLINE_REP_SCALE.get(base_rep, 0.6)
        # A line weight that flatters one domain turns a ribosome into black
        # lace, because the number of features per pixel goes up with the
        # subject. Two fixed steps were not enough at 250k atoms; taper
        # continuously instead, floored so the silhouette never disappears.
        if info["atoms"] > 30000:
            o_frac *= max(0.20, (30000.0 / info["atoms"]) ** 0.65)
    rec.note()

    # ---- colour ----------------------------------------------------------
    rec.note("colouring")
    # ligands read as chemistry in backbone styles, as part of the mass in
    # space-filling and surface styles
    het_cpk = rep_used in ("cartoon", "tube", "putty", "ribbon", "nucleic",
                           "cartoon+surface", "sticks", "ballstick", "lines")
    col_used = _apply_coloring(rec, sel, coloring, palette, het_cpk=het_cpk,
                               dark=dark, focus=focus_sel,
                               rep=rep_used,
                               pale_carbon=rep_used in ("spheres", "surface",
                                                        "ghost", "mesh",
                                                        "dots"))
    if dark and col_used == "mono":
        rec.set_color("viz_mono", _lighter(_palette(palette)[0], 0.25))
    if rep_used in ("cartoon", "cartoon+surface", "tube", "putty", "ribbon",
                    "nucleic", "mesh", "pocket") and not st.get("flat_ribbon"):
        _ribbon_shade(rec, sel, True)
    if st.get("gaps"):
        try:
            viz_gaps(sel, quiet=1)
        except Exception:
            pass
    interaction_focus = ""
    interaction_pair = None
    interaction_mode = ""
    contact_labels = ""
    contact_label_limit = 0
    if st.get("interface"):
        try:
            _apply_interface(rec, sel, st, blob, q >= 1)
            core = _LAST.pop("contact_core", "")
            interaction_focus = _LAST.pop("interaction_focus", "")
            interaction_pair = _LAST.pop("interaction_pair", None)
            interaction_mode = _LAST.pop("interaction_mode", "")
            if core:
                # A residue-level figure framed on the whole complex is not a
                # residue-level figure; and looking down the line between the
                # partners stacks them on top of each other, so lay that line
                # across the frame instead and the two sides separate.
                if not _orient_across(_LAST.get("contact_pair"), core):
                    cmd.orient(core)
                cmd.zoom(core, 2.5)
                contact_labels = core
                contact_label_limit = _i(_LAST.pop("contact_label_limit", 0))
        except CmdException as exc:
            if not _b(quiet):
                print(" viz: %s" % exc)
        except Exception:
            pass
    rec.note()

    rec.rebuild()

    # A file opens in whatever orientation it was deposited in, which for a DNA
    # duplex means looking straight down the helix axis at a meaningless wheel.
    # Orient the first time a selection is styled; afterwards leave the camera
    # alone so restyling does not throw away a view the user set up.
    want_orient = _i(orient, -1)
    if want_orient < 0:
        # keyed on what the selection *contains*, not on its text: "all" names
        # a different molecule after a delete-and-load, and comparing the
        # string alone left the new structure in its deposited orientation.
        # Reloading the *same* file is indistinguishable from restyling it, so
        # pass orient=1 when a driver knows the subject is new.
        want_orient = int(not _LAST or _LAST.get("subject_key") != subject_key)
    frame_core = st["focus"] == "core" and want_orient
    close_up = st.get("interface") in ("contacts", "epitope", "peptide")
    if want_orient and not _s(view) and not focus_sel and not frame_core \
            and not close_up:
        partner = None
        if st.get("interface"):
            # the partner has to face the reader, or the figure shows the back
            # of the receptor and the interaction is a sliver at the edge
            try:
                if _PINNED.get("partners"):
                    x, y = _PINNED["partners"]
                    partner = y if cmd.count_atoms(y) <= cmd.count_atoms(x) else x
                else:
                    _big, partner = _partners(sel, warn=not _b(quiet))
            except Exception:
                partner = None
        if not (partner and _orient_pocket(sel, partner)):
            if not _orient_symmetry(sel):
                cmd.orient(_visible(sel))

    # a new representation has a different extent, so a zoom computed for the
    # old one leaves the structure cropped or lost in the middle of the frame
    want_fit = _i(fit, -1)
    if want_fit < 0:
        want_fit = int(_LAST.get("rep") != rep_used or not _LAST or want_orient)
    if want_fit and not _s(view) and not focus_sel and not frame_core \
            and not close_up:
        shown = _visible(sel)
        cmd.zoom(shown, 0.0, complete=1)
        if not _fit_projected(shown, 0.045, _rep_pad(rep_used, blob)):
            _scale_field(1.08)
    elif frame_core:
        # a disordered AlphaFold tail is half the bounding box and a tenth of
        # the model; framing on it leaves the fold too small to read. But it
        # still may not be cut by the frame.
        viz_view("core", sel, quiet=1)

    if _s(frame):
        viz_frame(frame, sel, quiet=1)
    if _s(view):
        viz_view(view, sel, quiet=1)
    elif interaction_focus:
        # Interaction modes are close-ups by definition. A footprint viewed
        # from the side is a thin orange sliver; a contact map viewed from the
        # whole assembly is an unreadable nest of labels.
        if interaction_mode in ("epitope", "peptide") and interaction_pair:
            if not _orient_pocket(interaction_pair[0], interaction_pair[1]):
                cmd.orient(interaction_focus)
        elif interaction_pair:
            if not _orient_across(interaction_pair, interaction_focus):
                cmd.orient(interaction_focus)
        else:
            cmd.orient(interaction_focus)
        cmd.zoom(interaction_focus, 2.8)
    elif focus_sel:
        # a close-up style is meaningless framed from across the whole complex
        pocket = "(%s) or byres ((%s) and polymer within 7 of (%s))" \
            % (focus_sel, sel, focus_sel)
        if not _orient_pocket(sel, focus_sel):
            cmd.orient(pocket)
        cmd.zoom(pocket, 3.0)

    if contact_labels:
        try:
            viz_label("residues", contact_labels, size=13, quiet=1,
                      max_labels=contact_label_limit)
        except Exception:
            pass

    _LAST_SCRIPT = rec.lines
    _LAST = {
        "legend_title": _LAST.get("legend_title", ""),
        "auto_caption": _LAST.get("auto_caption", ""),
        "buried_area": _LAST.get("buried_area", 0.0),
        "style": name, "selection": sel, "subject_key": subject_key,
        "coloring": col_used,
        "palette": palette, "rep": rep_used, "light": light,
        "outline": o_frac, "outline_color": ocolor, "blob": blob,
        "background": bg_txt, "bg_spec": bg_spec,
        "post": _merge_post(st["post"], _f(glow, -1.0), _f(vignette, -1.0),
                            _f(contrast, -1.0), _f(saturation, -1.0),
                            _f(grain, -1.0), _i(posterize, -1),
                            _f(sharpen, -1.0)),
        "lineart": st["lineart"], "fog": fogv,
        "ink": st["ink"], "ink_threshold": st["ink_threshold"],
        "annotations": dict(st.get("annotations") or {}),
        "_enforce_margin": bool(frame_core),
        "dof": float(st["dof"]) if _f(dof, -1.0) < 0 else _f(dof, 0.0),
        "colour_groups": list(_LAST_GROUPS),
        "bfactor_range": _bfactor_range(sel) if col_used == "bfactor"
        else (None, None),
        "dark_bg": dark, "info": info,
    }
    if not _b(quiet):
        print(" viz: '%s' on %d atoms - %s / %s / %s"
              % (name, info["atoms"], rep_used, col_used, light))
        print(" viz: viz_render to write the finished image.")
    return _LAST


def viz_auto(selection="", quiet=0):
    """
DESCRIPTION

    Look at the structure, report what it contains, and apply the style that
    suits it. The zero-decision entry point.
    """
    sel = _s(selection) or "all"
    info = _survey(sel)
    pick = _pick_style(info)
    if not _b(quiet):
        kinds = []
        for key, word in (("protein", "protein"), ("nucleic", "nucleic acid"),
                          ("ligand", "ligand"), ("ion", "ion"),
                          ("water", "water")):
            if info[key]:
                kinds.append("%s (%d atoms)" % (word, info[key]))
        print(" viz_auto: %d atoms, %d chains, %d residues, %.0f A across"
              % (info["atoms"], info["chains"], info["residues"], info["span"]))
        print(" viz_auto: contains %s" % (", ".join(kinds) or "nothing known"))
        if info["plddt_like"]:
            print(" viz_auto: b-factors look like AlphaFold pLDDT")
        print(" viz_auto: choosing style '%s'" % pick)
    out = viz(pick, sel, quiet=1)
    # a floppy tail in the bounding box leaves the fold too small to read
    core = _core_selection(sel)
    loose = False
    if core:
        loose = cmd.get_extent(core) and \
            max(_extent_span(core)) < 0.72 * max(_extent_span(sel))
        cmd.delete(core)
    viz_view("core" if loose else "best", sel, quiet=1)
    if not _b(quiet):
        if loose:
            print(" viz_auto: framed on the compact core; low-confidence or "
                  "flexible parts extend past the frame")
        print(" viz_auto: done - try viz_render, or viz_gallery to compare "
              "styles.")
    return out


def viz_color(coloring="chain", palette="", selection="", quiet=0):
    """
DESCRIPTION

    Recolour without touching the representation or lighting.

USAGE

    viz_color [coloring [, palette [, selection ]]]
    """
    sel = _s(selection) or _LAST.get("selection", "all")
    palette = _s(palette) or _LAST.get("palette", "molstar")
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    rec = _Rec()
    used = _apply_coloring(rec, sel, coloring, palette)
    rec.rebuild()
    if _LAST:
        _LAST["coloring"] = used
        _LAST["palette"] = palette
    if not _b(quiet):
        print(" viz_color: %s / %s" % (used, palette))
    return used


# Two labels whose anchors project within this many pixels of each other will
# overlap on the page whatever the type size, so the second one is not drawn.
LABEL_MIN_SEP = 0.055


def _thin_labels(target, min_sep=LABEL_MIN_SEP, limit=0):
    """Drop labels that would land on top of one another.

    PyMOL places a label at its atom and does nothing about collisions, so a
    crowded binding site prints a stack of half-readable words. Anchors are
    projected to the screen and any residue landing too near one already
    chosen is left unlabelled - a figure with five readable names beats one
    with nine unreadable ones."""
    try:
        import numpy
        rows = []
        cmd.iterate_state(1, "(%s) and name CA+C1'" % target,
                          "rows.append((model, segi, chain, resi, x, y, z))",
                          space={"rows": rows})
        if len(rows) < 2:
            return target
        v = cmd.get_view()
        rot = numpy.array(v[0:9], dtype=float).reshape(3, 3)
        org = numpy.array(v[12:15], dtype=float)
        pts = (numpy.array([r[4:] for r in rows], dtype=float) - org).dot(rot)
    except Exception:
        return target
    span = float(max(numpy.ptp(pts[:, 0]), numpy.ptp(pts[:, 1]))) or 1.0
    gap = min_sep * span * 4.0
    keep, taken = [], []
    order = sorted(range(len(rows)), key=lambda i: -pts[i][2])   # nearest first
    for i in order:
        xy = pts[i][:2]
        if any(float(numpy.linalg.norm(xy - t)) < gap for t in taken):
            continue
        taken.append(xy)
        keep.append('(%s and segi "%s" and chain "%s" and resi %s)'
                    % (rows[i][0], rows[i][1], rows[i][2], rows[i][3]))
    if limit:
        keep = keep[:max(1, int(limit))]
    if not keep or len(keep) == len(rows):
        return target
    return "(%s) and (%s)" % (target, " or ".join(keep))


def viz_label(what="residues", selection="", size=0, color="", quiet=0,
              max_labels=0):
    """
DESCRIPTION

    Label the structure so a referee can check it.

    A binding-site figure without residue names and numbers cannot be verified
    against the text, which is why hand-finishing in Illustrator is otherwise
    unavoidable.

USAGE

    viz_label [what [, selection [, size [, color ]]]]

ARGUMENTS

    what      = residues | chains | termini | ligands | off
    selection = what to label {default: the current subject}
    size      = label size in points, 0 for automatic
    color     = label colour, empty for automatic

EXAMPLES

    viz_label residues, byres (polymer within 4.5 of organic)
    viz_label chains
    viz_label termini
    viz_label off
    """
    kind = _s(what, "residues").lower()
    sel = _s(selection) or _LAST.get("selection") or "all"
    if kind in ("off", "none", "hide"):
        cmd.label("all", "")
        if not _b(quiet):
            print(" viz_label: labels cleared")
        return 0
    dark = _LAST.get("dark_bg")
    col = _s(color) or ("#F2F2F2" if dark else "#1A1A1A")
    pts = _i(size, 0) or 16
    cmd.set("label_size", pts)
    cmd.set("label_font_id", 7)
    cmd.set("label_color", _color_name(col if _s(color) else "#1A1A1A"))
    cmd.set("label_outline_color", _color_name("#000000" if dark else "#FFFFFF"))
    # A one-pixel outline does not survive a ribbon passing behind the glyphs:
    # half the labels on a crowded site read as fragments. An opaque plate
    # behind the text is what makes them legible over the model.
    cmd.set("label_bg_color", _color_name("#101010" if dark else "#FFFFFF"))
    cmd.set("label_bg_transparency", 0.12)
    cmd.set("label_bg_outline", 1)
    cmd.set("label_connector", 1)
    cmd.set("label_connector_mode", 1)
    cmd.set("label_connector_color", _color_name("#9A9488"))
    cmd.set("label_connector_width", 1)
    cmd.set("label_position", [0.0, 0.0, 3.0])

    if kind.startswith("res"):
        target = "(%s) and name CA+C1'" % sel
        if not cmd.count_atoms(target):
            target = "(%s) and guide" % sel
        target = _thin_labels(target, limit=_i(max_labels, 0))
        cmd.label(target, '"%s%s" % (resn.capitalize(), resi)')
    elif kind.startswith("chain"):
        cmd.label("all", "")
        for model, chain in _chain_keys("(%s) and polymer" % sel):
            one = _sel_chain("(%s) and polymer" % sel, model, chain)
            cmd.label("first ((%s) and guide)" % one, '"Chain %s" % chain')
        cmd.set("label_size", pts + 6)
    elif kind.startswith("term"):
        cmd.label("all", "")
        for model, chain in _chain_keys("(%s) and polymer" % sel):
            one = _sel_chain("(%s) and polymer" % sel, model, chain)
            cmd.label("first ((%s) and guide)" % one, '"N"')
            cmd.label("last ((%s) and guide)" % one, '"C"')
        cmd.set("label_size", pts + 8)
    elif kind.startswith("lig"):
        cmd.label("all", "")
        lig = _focus_selection(sel)
        if lig:
            cmd.label("first (%s)" % lig, "resn")
            cmd.set("label_size", pts + 4)
    else:
        raise CmdException("unknown label kind '%s' (residues, chains, "
                           "termini, ligands, off)" % what)
    n = cmd.count_atoms("(%s) and not label ''" % sel) if False else 0
    if not _b(quiet):
        print(" viz_label: %s labelled on '%s'" % (kind, sel))
    return n


def viz_focus(selection="", context_fade=0.72, quiet=0):
    """
DESCRIPTION

    Make one selection the subject and push everything else back.

    An image where every part is equally saturated and equally emphasised has
    no subject, which is the single clearest signature of a software default.
    This desaturates and lightens the context so the eye lands on the
    selection, the way published figures grey out the invariant scaffold and
    colour only what the figure is about.

USAGE

    viz_focus selection [, context_fade]

ARGUMENTS

    selection    = what to emphasise
    context_fade = 0..1 how far the rest is pushed back {default: 0.72}

EXAMPLES

    viz_focus chain A
    viz_focus organic, 0.85
    viz_focus resi 145-166
    """
    sel = _s(selection)
    if not sel:
        raise CmdException("viz_focus needs a selection to emphasise")
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    fade = max(0.0, min(1.0, _f(context_fade, 0.72)))
    context = "not (%s)" % sel
    if not cmd.count_atoms(context):
        if not _b(quiet):
            print(" viz_focus: nothing outside the selection to fade")
        return 0

    # read each context atom's colour and mix it toward the page, preserving
    # relative differences instead of flattening everything to one grey
    seen = {}
    idx = []
    cmd.iterate(context, "idx.append(color)", space={"idx": idx})
    for c in set(idx):
        try:
            rgb = cmd.get_color_tuple(c)
        except Exception:
            continue
        if not rgb:
            continue
        lum = _lum(rgb)
        target = (0.86, 0.87, 0.88) if lum < 0.86 else (0.78, 0.79, 0.80)
        name = "viz_fade%d" % c
        cmd.set_color(name, list(_mix(rgb, target, fade)))
        seen[c] = cmd.get_color_index(name)
    if seen:
        it = {"m": seen}
        cmd.alter(context, "color = m.get(color, color)", space=it["m"] and
                  {"m": seen})
        cmd.recolor()
    n = cmd.count_atoms(sel)
    if not _b(quiet):
        print(" viz_focus: %d atoms in subject, context faded %d%%"
              % (n, int(fade * 100)))
    return n


def viz_gaps(selection="", color="", quiet=0):
    """
DESCRIPTION

    Draw a dotted line across every chain break.

    A crystallographic model is not the molecule: disordered loops are simply
    absent, and a cartoon draws the two ordered ends as if nothing were
    missing. A reader cannot tell a genuine short connection from twenty
    residues nobody could see. Published schematics mark the difference with a
    dotted line, which says "something is here and it was not modelled"
    without inventing a path for it.

USAGE

    viz_gaps [selection [, color]]

ARGUMENTS

    selection = what to check {default: everything}
    color     = dash colour; empty follows the background

EXAMPLES

    viz_gaps
    viz_gaps chain A, grey40
    """
    sel = _s(selection) or "all"
    cmd.delete("viz_gaps")
    pairs = _chain_breaks(sel)
    if not pairs:
        if not _b(quiet):
            print(" viz_gaps: no chain breaks found in '%s'" % sel)
        return 0
    rgb = _hex2rgb(_s(color)) if _s(color).startswith("#") else _hex2rgb("#5A564E")
    try:
        import numpy
        centre = numpy.array(cmd.get_coords(sel)).mean(axis=0)
    except Exception:
        return 0
    cgo = []
    for a, b in pairs:
        pa, pb = cmd.get_coords(a), cmd.get_coords(b)
        if pa is None or pb is None or not len(pa) or not len(pb):
            continue
        cgo.extend(_gap_arc(numpy.array(pa[0], dtype=float),
                            numpy.array(pb[0], dtype=float), centre, rgb))
    if not cgo:
        return 0
    cmd.load_cgo(cgo, "viz_gaps")
    if not _b(quiet):
        print(" viz_gaps: %d chain break%s marked"
              % (len(pairs), "" if len(pairs) == 1 else "s"))
    return len(pairs)


def _gap_arc(p1, p2, centre, rgb, radius=0.32):
    """Dashes along an arc that bulges away from the structure.

    A straight chord between the two ordered ends passes through the middle of
    the protein and is hidden by it, which is exactly where a missing loop is
    not. Bulging the path outward puts the dashes in clear space, the way a
    published schematic draws them, and makes no claim about the real path
    beyond the two points that are known."""
    import numpy
    import math
    span = float(numpy.linalg.norm(p2 - p1))
    if span <= 0.1:
        return []
    mid = (p1 + p2) / 2.0
    out = mid - centre
    n = float(numpy.linalg.norm(out))
    if n < 1e-3:
        axis = p2 - p1
        out = numpy.cross(axis, [0.0, 0.0, 1.0])
        n = float(numpy.linalg.norm(out)) or 1.0
    out = out / n
    ctrl = mid + out * max(3.0, min(0.55 * span, 22.0))
    steps = max(10, int(span * 1.6))
    pts = []
    for i in range(steps + 1):
        t = i / float(steps)
        u = 1.0 - t
        pts.append(u * u * p1 + 2 * u * t * ctrl + t * t * p2)
    cgo = []
    for i in range(steps):
        if i % 2:
            continue                      # every other segment is the gap
        a, b = pts[i], pts[i + 1]
        cgo += [9.0, float(a[0]), float(a[1]), float(a[2]),
                float(b[0]), float(b[1]), float(b[2]), radius,
                rgb[0], rgb[1], rgb[2], rgb[0], rgb[1], rgb[2]]
    return cgo


def viz_highlight(selection="", color="", base="", quiet=0):
    """
DESCRIPTION

    Paint one set of residues onto a neutral structure.

    The figure that says "these are the positions that changed" wants the whole
    fold in one quiet colour and the changed residues in one loud one, so the
    eye counts them without reading a legend. Unlike viz_focus, which fades the
    context but keeps its colours, this flattens everything to a single neutral
    first, so the highlight is the only colour in the picture.

USAGE

    viz_highlight selection [, color [, base]]

ARGUMENTS

    selection = the residues to bring forward
    color     = their colour {default: the reserved accent}
    base      = colour for everything else {default: a neutral grey}

EXAMPLES

    viz_highlight resi 224+227+228+231+232+238+241+245
    viz_highlight mutations, #D6446B
    viz_highlight chain B, marine, grey90
    """
    sel = _s(selection)
    if not sel:
        raise CmdException("viz_highlight needs a selection to bring forward")
    n = cmd.count_atoms(sel)
    if not n:
        raise CmdException("selection '%s' is empty" % sel)
    base_c = _s(base) or "#C9C6BE"
    hit_c = _s(color) or HET_ACCENT
    cmd.color(_color_name(base_c), "polymer")
    cmd.color(_color_name(hit_c), "byres (%s)" % sel)
    _LAST_GROUPS[:] = [(base_c, "unchanged", "polymer and not (%s)" % sel),
                       (hit_c, "highlighted", "byres (%s)" % sel)]
    _LAST["colour_groups"] = list(_LAST_GROUPS)
    _LAST["legend_title"] = "Key"
    _refresh_ribbon_shade()
    if not _b(quiet):
        print(" viz_highlight: %d atoms brought forward on a neutral fold" % n)
    return n


def viz_super(mobile="", target="", quiet=0):
    """
DESCRIPTION

    Superpose one structure on another and colour the comparison.

    The target keeps a quiet neutral so it reads as the reference; the mobile
    structure takes a spectrum along its sequence, which is what makes a
    remote-homology comparison legible - you can see which end went where.
    Uses cmd.super, which aligns on structure rather than sequence and so works
    where the two share a fold and little else.

USAGE

    viz_super mobile, target

EXAMPLES

    viz_super model_1, 1ubq
    viz_super prediction and chain A, reference and chain A
    """
    mob, tgt = _s(mobile), _s(target)
    if not mob or not tgt:
        raise CmdException("viz_super needs a mobile and a target selection")
    for label, sel in (("mobile", mob), ("target", tgt)):
        if not cmd.count_atoms(sel):
            raise CmdException("%s selection '%s' is empty" % (label, sel))
    try:
        res = cmd.super(mob, tgt)
    except Exception as exc:
        raise CmdException("superposition failed: %s" % exc)
    rms, n_atom = (res[0], res[1]) if res else (float("nan"), 0)
    cmd.color(_color_name("#CFCCC4"), tgt)
    cmd.spectrum("count", "rainbow", "(%s) and polymer" % mob)
    _LAST_GROUPS[:] = [("#CFCCC4", "reference", tgt)]
    _LAST["colour_groups"] = list(_LAST_GROUPS)
    _LAST["legend_title"] = "Superposition"
    _refresh_ribbon_shade()
    if not _b(quiet):
        print(" viz_super: %.2f A RMSD over %d atoms" % (rms, n_atom))
    return rms


INTERFACE_CUT = 4.5
# beyond this the smaller partner is a domain, not a peptide, and drawing every
# side chain of it produces a solid mass rather than a binding event
PEPTIDE_MAX = 40


def _chains_of(sel):
    """The chain identifiers in a selection, for saying what was chosen."""
    seen = set()
    try:
        cmd.iterate(sel, "s.add(chain)", space={"s": seen})
    except Exception:
        return ""
    ids = sorted(c for c in seen if c)
    return ("chain " + "+".join(ids)) if ids else ""


def _partners(sel, warn=False):
    """Split a selection into two interacting parts.

    Chains, unless there is only one chain, in which case a short stretch of
    it is being shown as a peptide bound to the rest. Returns the larger part
    first, since that is the one a reader reads as the receptor."""
    groups = []
    for members in _entity_groups(sel):
        for grp in _spatial_split(members, sel):
            g = " or ".join(_sel_chain(sel, m, c) for m, c in grp)
            n = cmd.count_atoms("(%s) and polymer" % g)
            if n:
                groups.append(("(%s)" % g, n))
    if len(groups) < 2:
        # A homodimer is one entity, so entity grouping alone finds nothing to
        # compare - and a homodimeric interface is about half of all of them.
        # Fall back to the individual chains of the single group.
        chains = []
        for members in _entity_groups(sel):
            for m, c in members:
                g = _sel_chain(sel, m, c)
                n = cmd.count_atoms("(%s) and polymer" % g)
                if n:
                    chains.append(("(%s)" % g, n))
        if len(chains) < 2:
            return None, None
        groups = chains
    groups.sort(key=lambda t: -t[1])
    if len(groups) > 2:
        # With three or more parts there is no way to know which grouping the
        # figure is about - an antibody is two chains and its antigen a third,
        # and taking the largest part as one side splits the antibody. Say what
        # was chosen, every time, so a wrong guess cannot pass unnoticed.
        print(" viz: %d separate parts here, so the split is a guess: "
              "%s against the rest. Set it with viz_partners a, b."
              % (len(groups), _chains_of(groups[0][0]) or "the largest part"))
    big = groups[0][0]
    # everything that is not the largest part is the partner, so a receptor
    # with two copies of a peptide still reads as receptor plus peptide
    rest = " or ".join(g for g, _ in groups[1:])
    return big, "(%s)" % rest


def _interface(a, b, cut=INTERFACE_CUT):
    """Whole residues of each partner that come within *cut* of the other."""
    fa = "byres ((%s) and polymer within %.2f of (%s))" % (a, cut, b)
    fb = "byres ((%s) and polymer within %.2f of (%s))" % (b, cut, a)
    return fa, fb


def _dominant_interface_region(a, b, fa, fb, radius=13.0):
    """Return the most coherent contact patch across two partners.

    Crystal asymmetric units often contain several copies of one complex. A
    contact close-up that tries to show every copy becomes a labelled map of
    unrelated sites. Cluster contact residues in 3D and choose the largest
    physical patch; the full interface remains available through the regular
    `interface` style and `viz_contact_table`.
    """
    try:
        import numpy
        rows = []
        cmd.iterate_state(1, "((%s) or (%s)) and name CA+C1'" % (fa, fb),
                          "rows.append((model, segi, chain, resi, x, y, z))",
                          space={"rows": rows})
        if len(rows) < 3:
            return "(%s) or (%s)" % (fa, fb)
        pts = numpy.array([r[4:] for r in rows], dtype=float)
        near = numpy.sum((pts[:, None, :] - pts[None, :, :]) ** 2,
                         axis=2) <= radius * radius
        unseen, groups = set(range(len(rows))), []
        while unseen:
            todo, group = [unseen.pop()], []
            while todo:
                i = todo.pop()
                group.append(i)
                neighbours = set(numpy.where(near[i])[0]) & unseen
                unseen.difference_update(neighbours)
                todo.extend(neighbours)
            groups.append(group)
        chosen = max(groups, key=len)
        terms = []
        for i in chosen:
            model, segi, chain, resi = rows[i][:4]
            terms.append('(model "%s" and segi "%s" and chain "%s" and resi %s)'
                         % (model, segi, chain, resi))
        return "byres (%s)" % " or ".join(terms)
    except Exception:
        return "(%s) or (%s)" % (fa, fb)


def _buried_atoms(a, b, name="viz_buried", cut=1.0):
    """Atoms that actually lose solvent-accessible area on binding.

    Whole residues within 4.5 A is the easy definition and the wrong one for a
    surface: it paints the far side of every contact residue too. Measured on
    MDM2 it covers 31% of the surface where 12% is what binding buries. This
    marks only the atoms whose own area drops, which is what a footprint is."""
    keep = {}
    try:
        for k in ("dot_solvent", "dot_density"):
            keep[k] = cmd.get(k)
        cmd.set("dot_solvent", 1)
        cmd.set("dot_density", 3)
        cmd.create("viz_free", a)
        cmd.create("viz_partner", b)
        cmd.create("viz_bound", "viz_free or viz_partner")
        for obj in ("viz_free", "viz_partner", "viz_bound"):
            cmd.flag("ignore", obj, "clear")
        for obj in ("viz_free", "viz_bound"):
            cmd.get_area(obj, load_b=1)
        free = {}
        cmd.iterate("viz_free", "d[(segi, chain, resi, name)] = b",
                    space={"d": free})
        lost = []
        cmd.iterate("viz_bound",
                    "lost.append((segi, chain, resi, name, b))",
                    space={"lost": lost})
        marked = [t[:4] for t in lost if free.get(t[:4], 0.0) - t[4] > cut]
    except Exception:
        return None
    finally:
        for obj in ("viz_free", "viz_partner", "viz_bound"):
            try:
                cmd.delete(obj)
            except Exception:
                pass
        for k, v in keep.items():
            try:
                cmd.set(k, v)
            except Exception:
                pass
    if not marked:
        return None
    cmd.select(name, "none")
    step = 400
    for i in range(0, len(marked), step):
        expr = " or ".join(
            '(segi "%s" and chain "%s" and resi %s and name %s)' % t
            for t in marked[i:i + step])
        cmd.select(name, "(%s) or ((%s) and (%s))" % (name, a, expr))
    return name


def _apply_interface(rec, sel, st, blob, fine):
    """Geometry and colour for the interaction styles.

    Each of the three answers a different question at a different scale, so
    each gives the two partners a different pair of representations, but all
    three agree on what the interface is and how it is coloured."""
    mode = st.get("interface")
    pinned = _PINNED.get("partners")
    if pinned:
        big, small = pinned
    else:
        big, small = _partners(sel)
    if not big:
        raise CmdException("this style needs two parts to compare; it found "
                           "one. Use viz_interface a, b to name them.")
    fa, fb = _interface(big, small)
    # PyMOL computes a surface in the context of every atom in the object, so
    # the patch the partner covers is simply absent and the groove renders as
    # a hole. Mode 3 builds each selection's own surface.
    rec.set("surface_mode", 3)
    if mode in ("epitope", "peptide"):
        rec.hide("everything", "(%s)" % sel)
    if mode == "peptide" and _residue_count(small) > PEPTIDE_MAX:
        mode = "interface"
    if mode == "epitope":
        # With `viz_partners host, guest`, the first named selection is the
        # molecular surface that bears the footprint. Size is not biology:
        # antigens are frequently larger than their binders.
        host, guest = big, small
        fh, _fg = _interface(host, guest)
        measured = _buried_atoms(host, guest)
        if measured:
            fh = measured
        focus = _dominant_interface_region(host, guest, fh,
                                           _interface(guest, host)[0])
        host_context = "byres ((%s) and polymer within 20 of (%s))" \
                       % (host, focus)
        _apply_rep(rec, host_context, "surface", blob=blob, fine=fine)
        # The footprint is the evidence in this view.  Showing the bound
        # partner over it makes a colourful obstruction rather than a clear
        # epitope; role context belongs in the figure caption or an opt-in
        # render label.
        cmd.color(_color_name("#CFD3D0"), host_context)
        cmd.color(_color_name("#C85433"), fh)
        groups = [("#CFD3D0", "host surface", host_context),
                  ("#C85433", "contact footprint", fh)]
        _LAST["interaction_focus"] = focus
        _LAST["interaction_pair"] = (host, guest)
        _LAST["interaction_mode"] = "epitope"
    elif mode == "contacts":
        # Only the residues that touch, drawn as chemistry: a close-up of an
        # interface is a list of interactions, and the reader has to be able
        # to name each one and see how far apart the partners are.
        rec.hide("everything", "(%s)" % sel)
        core = _dominant_interface_region(big, small, fa, fb)
        context = "byres ((%s) and polymer within 6 of (%s))" % (sel, core)
        rec.show("cartoon", context)
        rec.show("sticks", "(%s) and (sidechain or name CA)" % core)
        cmd.color(_color_name("#9BB0C6"), big)
        cmd.color(_color_name("#D8C7A8"), small)
        cmd.color(_color_name("#2F5F8F"), "(%s) and elem C" % fa)
        cmd.color(_color_name("#B4622F"), "(%s) and elem C" % fb)
        rec.do("util.cnc('(%s) and not elem C')" % core,
               lambda: util.cnc("(%s) and not elem C" % core, _self=cmd))
        _polar_contacts(rec, fa, fb)
        groups = [("#2F5F8F", "partner 1 contacts", fa),
                  ("#B4622F", "partner 2 contacts", fb)]
        _LAST["contact_core"] = core
        _LAST["contact_pair"] = (fa, fb)
        _LAST["contact_label_limit"] = 4
    elif mode == "peptide":
        n_res = _residue_count(small)
        if n_res > PEPTIDE_MAX:
            # falling back beats a hairball, and beats raising into a caller
            # that catches and carries on with a half-built scene
            print(" viz: 'peptide' draws every side chain of the smaller "
                  "partner and this one is %d residues, so it would be a "
                  "hairball. Drawing it as 'interface' instead; name a real "
                  "peptide with viz_partners if that is not what you meant."
                  % n_res)
            mode = "interface"
        # Keep the groove and peptide, not the entire receptor: a full opaque
        # surface turns the peptide into a few disconnected orange fragments.
        rec.hide("everything", "(%s)" % sel)
        core = _dominant_interface_region(big, small, fa, fb)
        receptor_context = "byres ((%s) and polymer within 16 of (%s))" \
                           % (big, core)
        _apply_rep(rec, receptor_context, "surface", blob=blob, fine=fine)
        _apply_rep(rec, small, "cartoon", blob=blob, fine=fine)
        rec.show("sticks", "(%s) and sidechain" % small)
        rec.show("sticks", "(%s) and sidechain" % fa)
        cmd.color(_color_name("#D5D1C7"), receptor_context)
        cmd.color(_color_name("#B6A98F"), fa)
        cmd.color(_color_name("#C7522B"), small)
        groups = [("#D5D1C7", "receptor", receptor_context),
                  ("#B6A98F", "groove", fa),
                  ("#C7522B", "peptide", small)]
        # At this overview scale, unlabelled dashed contacts are visual noise.
        # `viz contacts` is the dedicated, labelled residue-level answer.
        _LAST["interaction_focus"] = core
        _LAST["interaction_pair"] = (big, small)
        _LAST["interaction_mode"] = "peptide"
    else:
        # One physical interface is the subject. Keeping the entire
        # crystallographic assembly in a contact overview leaves detached
        # chains and duplicate copies competing with the actual interface.
        rec.hide("everything", "(%s)" % sel)
        focus = _dominant_interface_region(big, small, fa, fb)
        big_context = "byres ((%s) and polymer within 22 of (%s))" % (big, focus)
        small_context = "byres ((%s) and polymer within 16 of (%s))" % (small, focus)
        _apply_rep(rec, big_context, "surface", blob=blob, fine=fine)
        rec.show("cartoon", small_context)
        cmd.color(_color_name("#9FB8D1"), big_context)
        cmd.color(_color_name("#C9956A"), small_context)
        cmd.color(_color_name("#235B8F"), fa)
        cmd.color(_color_name("#C85433"), fb)
        groups = [("#9FB8D1", "partner 1", big_context),
                  ("#235B8F", "its interface", fa),
                  ("#C9956A", "partner 2", small_context),
                  ("#C85433", "its interface", fb)]
        _LAST["interaction_focus"] = focus
        _LAST["interaction_pair"] = (big, small)
        _LAST["interaction_mode"] = "interface"
    del _LAST_GROUPS[:]
    _LAST_GROUPS.extend(groups)
    _LAST["colour_groups"] = list(_LAST_GROUPS)
    _LAST["legend_title"] = "Interface"
    area = _buried_area(big, small)
    if area:
        _LAST["buried_area"] = area
        # The measurement belongs in the caption or contact table, not across
        # the bottom of a close-up where it competes with the contact itself.
        if mode == "interface":
            _LAST["auto_caption"] = ""
    _refresh_ribbon_shade(sel)


def viz_openbook(gap=0.0, quiet=0):
    """
DESCRIPTION

    Open the complex like a book so both contact surfaces face the reader.

    An interface figure has a geometric problem: whichever partner you turn
    toward the reader stands in front of the mark it made on the other, so
    half of what the figure is about is always hidden. Opening the two apart
    and turning one of them over puts both footprints in view at once. This is
    the standard layout for an epitope or a docking surface.

    It moves the coordinates. Reload the structure to undo it.

USAGE

    viz_openbook [gap]

ARGUMENTS

    gap = separation in Angstrom; 0 picks one from the size of the partners

EXAMPLES

    viz_openbook
    viz_partners chain H+L, chain Y
    viz epitope
    viz_openbook 25
    """
    try:
        import numpy
    except Exception:
        raise CmdException("viz_openbook needs numpy")
    pinned = _PINNED.get("partners")
    a, b = pinned if pinned else _partners("all")
    if not a:
        raise CmdException("viz_openbook needs two partners; name them with "
                           "viz_partners a, b")
    # `viz epitope` deliberately hides the binder so its surface footprint is
    # unobscured.  An open-book view has the opposite job: show both matching
    # faces.  Rebuild that simple two-surface scene before moving either half;
    # after they separate, a distance-based interface selection would vanish.
    fa, fb = _interface(a, b)
    footprint = _buried_atoms(a, b, name="viz_openbook_footprint") or fa
    cmd.hide("everything", "all")
    cmd.set("surface_mode", 3)
    cmd.show("surface", a)
    cmd.show("surface", b)
    cmd.color(_color_name("#CFD3D0"), a)
    cmd.color(_color_name("#D8C7A8"), b)
    cmd.color(_color_name("#C85433"), footprint)
    cmd.color(_color_name("#255B87"), fb)
    ca = numpy.array(cmd.get_coords(a)).mean(axis=0)
    cb = numpy.array(cmd.get_coords(b)).mean(axis=0)
    n = cb - ca
    d = float(numpy.linalg.norm(n))
    if d < 1.0:
        raise CmdException("the two partners share a centre; nothing to open")
    n = n / d
    # an axis lying in the interface plane: turning about it flips the partner
    # over so the face that was against A now faces the same way A's does
    up = numpy.array([0.0, 0.0, 1.0])
    if abs(float(n.dot(up))) > 0.9:
        up = numpy.array([0.0, 1.0, 0.0])
    u = numpy.cross(n, up)
    u = u / float(numpy.linalg.norm(u))     # hinge, lying in the interface
    w = numpy.cross(u, n)                   # completes the frame

    # Both faces have to end up pointing at the reader, which takes a quarter
    # turn each in opposite directions - a single half turn of one partner
    # leaves the two faces pointing the same way as each other but sideways to
    # the camera, which shows the reader nothing.
    hinge = [float(t) for t in u]
    cmd.rotate(hinge, -90.0, a, camera=0, origin=[float(t) for t in ca])
    cmd.rotate(hinge, 90.0, b, camera=0, origin=[float(t) for t in cb])

    span = 0.0
    try:
        ea, eb = cmd.get_extent(a), cmd.get_extent(b)
        span = max(max(ea[1][i] - ea[0][i] for i in range(3)),
                   max(eb[1][i] - eb[0][i] for i in range(3)))
    except Exception:
        span = d
    move = _f(gap, 0.0) or max(6.0, 0.12 * span)
    cmd.translate([float(t) for t in (-u * (0.5 * span + move))], a, camera=0)
    cmd.translate([float(t) for t in (u * (0.5 * span + move))], b, camera=0)

    # Rotation about independent molecular centres leaves the two faces at
    # arbitrary heights.  A useful open-book panel is a comparison, not two
    # drifting thumbnails: place their centres on one baseline and leave one
    # deliberate gutter between them.
    ca2 = numpy.array(cmd.get_coords(a)).mean(axis=0)
    cb2 = numpy.array(cmd.get_coords(b)).mean(axis=0)
    mid = 0.5 * (ca2 + cb2)
    half_gap = 0.36 * span + 0.5 * move
    cmd.translate([float(t) for t in (mid - u * half_gap - ca2)], a, camera=0)
    cmd.translate([float(t) for t in (mid + u * half_gap - cb2)], b, camera=0)

    # look straight at the two faces, with the hinge across the frame
    v = list(cmd.get_view())
    z = -w / float(numpy.linalg.norm(w))
    y = numpy.cross(z, u)
    m = numpy.column_stack([u, y / float(numpy.linalg.norm(y)), z])
    v[0:9] = [float(t) for t in m.flatten()]
    cmd.set_view(v)
    cmd.zoom("(%s) or (%s)" % (a, b), 0.0, complete=1)
    cmd.rebuild()
    _LAST["selection"] = "(%s) or (%s)" % (a, b)
    _LAST["_enforce_margin"] = True
    _LAST["colour_groups"] = [
        ("#CFD3D0", "host surface", a),
        ("#C85433", "host footprint", footprint),
        ("#D8C7A8", "binder surface", b),
        ("#255B87", "binder interface", fb),
    ]
    if not _b(quiet):
        print(" viz_openbook: opened by %.0f A; coordinates moved, reload to "
              "undo" % move)
    return move


def viz_contact_table(a="", b="", cut=0.0, filename="", quiet=0):
    """
DESCRIPTION

    List the residue pairs across an interface, with distances.

    The table a referee asks for and that usually becomes a supplementary
    file. Pairs are the closest heavy-atom approach between two residues on
    opposite sides, sorted by distance.

USAGE

    viz_contact_table [a [, b [, cut [, filename]]]]

EXAMPLES

    viz_contact_table
    viz_contact_table chain H+L, chain Y, 4.0, ~/contacts.tsv
    """
    sa, sb = _s(a), _s(b)
    if not sa or not sb:
        pinned = _PINNED.get("partners")
        sa, sb = pinned if pinned else _partners("all")
        if not sa:
            raise CmdException("name the two partners: viz_contact_table a, b")
    cutoff = _f(cut, 0.0) or INTERFACE_CUT
    pairs = {}
    model = {"m": None}
    rows_a, rows_b = [], []
    for sel, out in ((sa, rows_a), (sb, rows_b)):
        cmd.iterate_state(1, "(%s) and polymer and not hydro" % sel,
                          "out.append((chain, resi, resn, x, y, z))",
                          space={"out": out})
    try:
        import numpy
        pa = numpy.array([r[3:] for r in rows_a])
        pb = numpy.array([r[3:] for r in rows_b])
    except Exception:
        raise CmdException("viz_contact_table needs numpy")
    if not len(pa) or not len(pb):
        raise CmdException("one side has no atoms")
    for i in range(len(pa)):
        d = numpy.linalg.norm(pb - pa[i], axis=1)
        for j in numpy.where(d <= cutoff)[0]:
            ka = "%s %s%s" % (rows_a[i][0], rows_a[i][2].capitalize(),
                              rows_a[i][1])
            kb = "%s %s%s" % (rows_b[j][0], rows_b[j][2].capitalize(),
                              rows_b[j][1])
            key = (ka, kb)
            if key not in pairs or d[j] < pairs[key]:
                pairs[key] = float(d[j])
    if not pairs:
        raise CmdException("no contacts within %.1f A" % cutoff)
    ordered = sorted(pairs.items(), key=lambda kv: kv[1])
    lines = ["partner_1	partner_2	distance_A"]
    lines += ["%s	%s	%.2f" % (k[0], k[1], v) for k, v in ordered]
    path = _s(filename)
    if path:
        path = os.path.expanduser(path)
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        if not _b(quiet):
            print(" viz_contact_table: %d residue pairs -> %s"
                  % (len(ordered), path))
    elif not _b(quiet):
        for line in lines[:41]:
            print("  " + line.replace("\t", "  "))
        if len(lines) > 41:
            print("  ... %d more; pass a filename to write them all"
                  % (len(lines) - 41))
    return len(ordered)


def viz_partners(a="", b="", quiet=0):
    """
DESCRIPTION

    Say which two parts of the structure are the partners.

    The interaction styles work out the split themselves, and with more than
    two chain groups present that is a guess - an antibody is two chains and
    its antigen is a third. Set it once here and `viz interface`, `viz epitope`
    and `viz peptide` will use it instead of guessing.

USAGE

    viz_partners a, b        # set
    viz_partners             # clear, back to guessing

EXAMPLES

    viz_partners chain H+L, chain Y
    viz epitope
    """
    sa, sb = _s(a), _s(b)
    if not sa and not sb:
        _LAST.pop("partners", None)
        _PINNED.pop("partners", None)
        if not _b(quiet):
            print(" viz_partners: cleared; the styles will split it themselves")
        return 0
    if not sa or not sb:
        raise CmdException("viz_partners needs both partners, or neither")
    for label, sel in (("a", sa), ("b", sb)):
        if not cmd.count_atoms(sel):
            raise CmdException("partner %s ('%s') is empty" % (label, sel))
    _PINNED["partners"] = (sa, sb)
    if not _b(quiet):
        print(" viz_partners: %d and %d atoms"
              % (cmd.count_atoms(sa), cmd.count_atoms(sb)))
    return 2


def viz_interface(a="", b="", cut=0.0, quiet=0):
    """
DESCRIPTION

    Colour a protein-protein interface and report how big it is.

    Each partner keeps its own hue; the residues that actually touch the other
    are brought forward in a shared accent, so the reader sees one interface
    rather than two unrelated coloured patches. The buried area is measured
    rather than described: it is the difference between the partners' areas
    apart and together, halved, which is the number a paper quotes.

USAGE

    viz_interface [a [, b [, cut]]]

ARGUMENTS

    a, b = the two partners; empty splits the structure into its two largest
           parts by chain, which is what a two-body complex usually is
    cut  = contact distance in Angstrom {default: 4.5}

EXAMPLES

    viz_interface
    viz_interface chain A, chain B
    viz_interface receptor, peptide, 5.0
    """
    sa, sb = _s(a), _s(b)
    if not sa or not sb:
        sa, sb = _partners("all")
        if not sa:
            raise CmdException(
                "viz_interface could not find two parts to compare; name them "
                "explicitly, as in: viz_interface chain A, chain B")
    for name, sel in (("a", sa), ("b", sb)):
        if not cmd.count_atoms(sel):
            raise CmdException("partner %s ('%s') is empty" % (name, sel))
    cutoff = _f(cut, 0.0) or INTERFACE_CUT
    fa, fb = _interface(sa, sb, cutoff)
    na, nb = cmd.count_atoms(fa), cmd.count_atoms(fb)
    if not na or not nb:
        raise CmdException("no residues within %.1f A across the interface"
                           % cutoff)
    buried = _buried_area(sa, sb)
    cmd.color(_color_name("#8FA9C4"), sa)
    cmd.color(_color_name("#C9B79A"), sb)
    cmd.color(_color_name("#3D6E9C"), fa)
    cmd.color(_color_name("#C06B3E"), fb)
    _LAST_GROUPS[:] = [("#8FA9C4", "partner 1", sa),
                       ("#3D6E9C", "interface 1", fa),
                       ("#C9B79A", "partner 2", sb),
                       ("#C06B3E", "interface 2", fb)]
    _LAST["colour_groups"] = list(_LAST_GROUPS)
    _LAST["legend_title"] = "Interface"
    _refresh_ribbon_shade()
    if not _b(quiet):
        print(" viz_interface: %d + %d residues in contact within %.1f A"
              % (_residue_count(fa), _residue_count(fb), cutoff))
        if buried:
            print(" viz_interface: %.0f A^2 buried per partner" % buried)
    return buried or 0.0


def _buried_area(a, b):
    """Solvent-accessible area lost by each partner on forming the complex."""
    keep = {}
    try:
        for k in ("dot_solvent", "dot_density"):
            keep[k] = cmd.get(k)
        cmd.set("dot_solvent", 1)
        cmd.set("dot_density", 3)
        cmd.create("viz_ifa", a)
        cmd.create("viz_ifb", b)
        # built from the two copies by name, never from the original
        # selection: a plain selection like "chain A" still matches the copies
        # that were just made, so the complex came out counted three times
        cmd.create("viz_ifab", "viz_ifa or viz_ifb")
        # get_area honours the ignore flag, which PyMOL sets on HETATM, so a
        # cofactor at the interface would be measured as absent
        for name in ("viz_ifa", "viz_ifb", "viz_ifab"):
            cmd.flag("ignore", name, "clear")
        # measured on objects, never on a selection: a selection still matches
        # the temporary copies, so the union counted the complex three times
        area = (cmd.get_area("viz_ifa") + cmd.get_area("viz_ifb")
                - cmd.get_area("viz_ifab")) / 2.0
    except Exception:
        area = 0.0
    finally:
        for name in ("viz_ifa", "viz_ifb", "viz_ifab"):
            try:
                cmd.delete(name)
            except Exception:
                pass
        for k, v in keep.items():
            try:
                cmd.set(k, v)
            except Exception:
                pass
    return max(0.0, float(area))


def viz_mix(spec="", selection="", quiet=0):
    """
DESCRIPTION

    Draw different parts of a structure in different representations.

    One idiom rarely suits a whole complex: the body of a transporter wants a
    surface, the nucleic acid it holds wants its rings drawn, and the ligand
    wants sticks. Rules are applied in order and each one only claims what no
    earlier rule took, so overlapping selections do not double-draw.

USAGE

    viz_mix spec [, selection]

ARGUMENTS

    spec      = 'selection=representation' pairs separated by / or |
                (PyMOL's parser eats commas, so / is the separator)
    selection = restrict the whole spec to this {default: everything}

    Selections are ordinary PyMOL selections. These words are also accepted:
    protein, nucleic, dna, rna, ligand, ions, solvent, polymer, het, all,
    and `rest` for whatever no earlier rule claimed.

EXAMPLES

    viz_mix protein=ghost / nucleic=cartoon / ligand=ballstick
    viz_mix chain A=surface / chain B=cartoon / rest=lines
    viz_mix resi 1-120=cartoon / rest=tube
    """
    pairs = _parse_spec(spec, "viz_mix")
    scope = _s(selection) or "all"
    rules = _spec_selections(pairs, scope)
    if not rules:
        raise CmdException("viz_mix: no rule matched any atom")
    rec = _Rec()
    rec.hide("everything", "(%s)" % scope)
    blob = _f(_LAST.get("blob"), 1.4)
    used = []
    for sub, rep, n in rules:
        applied = _apply_rep(rec, sub, rep, blob=blob, fine=True)
        used.append((applied, n))
    _LAST["rep"] = "mix"
    _LAST["mix"] = [(sub, rep) for sub, rep, _ in rules]
    if not _b(quiet):
        for (rep, n), (sub, _, _) in zip(used, rules):
            print(" viz_mix: %-16s %7d atoms" % (rep, n))
    return len(rules)


def viz_paint(spec="", selection="", quiet=0):
    """
DESCRIPTION

    Colour named parts of a structure, everything else quiet.

    The review-figure idiom: two domains carry colour, the rest of the fold is
    near-white, and the reader's eye goes only where the author pointed it.
    Rules apply in order and each claims only what earlier rules did not, and
    the colours become the figure's key.

USAGE

    viz_paint spec [, selection]

ARGUMENTS

    spec      = 'selection=colour' pairs separated by / or |; colours are
                #hex or PyMOL colour names, and the label shown in the key is
                the selection unless you write 'selection=colour=label'
    selection = restrict the whole spec to this {default: everything}

EXAMPLES

    viz_paint resi 1-90=#B7D3C3 / resi 91-200=#7E9CC2 / rest=#EDEAE4
    viz_paint chain A=#B7D3C3=transporter / chain B=#7E9CC2=scaffold
    viz_paint ligand=#D6446B / rest=grey80
    """
    pairs = _parse_spec(spec, "viz_paint")
    scope = _s(selection) or "all"
    labels = []
    clean = []
    for sel, val in pairs:
        if "=" in val:
            col, lab = val.split("=", 1)
            clean.append((sel, col.strip()))
            labels.append(lab.strip())
        else:
            clean.append((sel, val))
            labels.append("rest" if sel.lower() == "rest" else sel)
    rules = _spec_selections(clean, scope)
    if not rules:
        raise CmdException("viz_paint: no rule matched any atom")
    del _LAST_GROUPS[:]
    for i, ((sub, col, n), lab) in enumerate(zip(rules, labels)):
        name = _color_name(col)
        cmd.color(name, sub)
        try:
            rgb = cmd.get_color_tuple(cmd.get_color_index(name))
            hexcol = _rgb2hex(rgb) if rgb else col
        except Exception:
            hexcol = col
        _LAST_GROUPS.append((hexcol, lab, sub))
        if not _b(quiet):
            print(" viz_paint: %-22s %-9s %7d atoms" % (lab[:22], col, n))
    _LAST["colour_groups"] = list(_LAST_GROUPS)
    _LAST["coloring"] = "chain"
    _LAST["legend_title"] = "Key"
    _refresh_ribbon_shade(scope)
    return len(rules)


def viz_cutaway(depth=0.0, selection="", quiet=0):
    """
DESCRIPTION

    Cut the front off the scene to reveal an interior.

    A chaperonin folding chamber, a capsid lumen or a buried pocket cannot be
    shown from outside at all. This centres a viewing slab on the structure and
    colours the cut faces so they read as sectioned material rather than holes.

USAGE

    viz_cutaway [depth [, selection ]]

ARGUMENTS

    depth     = thickness of the retained slab in Angstrom; 0 picks half the
                structure's depth, which sections through the middle
    selection = what to centre the slab on {default: everything}

EXAMPLES

    viz_cutaway                  # section through the middle
    viz_cutaway 30
    viz_cutaway 0, chain A
    """
    sel = _s(selection) or "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    span = max(_extent_span(_visible(sel)))
    d = _f(depth, 0.0)
    if d <= 0:
        d = span * 0.5
    v = list(cmd.get_view())
    dist = -v[11]
    half = max(2.0, d / 2.0)
    v[15] = dist - half
    v[16] = dist + half
    cmd.set_view(v)
    # cut faces take a warm interior tone so a section does not read as a hole
    cmd.set("ray_interior_color", _color_name("#C4A882"))
    cmd.set("two_sided_lighting", 1)
    if not _b(quiet):
        print(" viz_cutaway: %.0f A slab through a %.0f A structure" % (d, span))
    return d


def viz_membrane(thickness=30.0, selection="", color="", quiet=0):
    """
DESCRIPTION

    Draw the lipid bilayer as two parallel planes.

    A transmembrane fold means nothing without them: the planes turn an
    abstract helical bundle into an oriented object with an inside and an
    outside, which is why published membrane-protein figures nearly always
    include them.

USAGE

    viz_membrane [thickness [, selection [, color ]]]

ARGUMENTS

    thickness = bilayer thickness in Angstrom {default: 30}
    selection = what to centre the bilayer on {default: everything}
    color     = plane colour, empty for a neutral grey

EXAMPLES

    viz_membrane
    viz_membrane 34, polymer
    """
    from pymol import cgo
    sel = _s(selection) or "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    t = max(4.0, _f(thickness, 30.0))
    ext = cmd.get_extent(_visible(sel))
    cx = (ext[0][0] + ext[1][0]) / 2.0
    cy = (ext[0][1] + ext[1][1]) / 2.0
    cz = (ext[0][2] + ext[1][2]) / 2.0
    # the bilayer normal is the view's vertical axis, so the planes read as
    # horizontal lines in the rendered image
    half_x = (ext[1][0] - ext[0][0]) / 2.0 * 1.35 + 6.0
    half_z = (ext[1][2] - ext[0][2]) / 2.0 * 1.35 + 6.0
    rgb = list(_hex2rgb(_s(color) or "#8A8578"))
    obj = []
    for sign in (-1.0, 1.0):
        y = cy + sign * t / 2.0
        obj += [cgo.BEGIN, cgo.LINES, cgo.LINEWIDTH, 3.0,
                cgo.COLOR] + rgb
        for zz in (cz - half_z, cz + half_z):
            obj += [cgo.VERTEX, cx - half_x, y, zz,
                    cgo.VERTEX, cx + half_x, y, zz]
        for xx in (cx - half_x, cx + half_x):
            obj += [cgo.VERTEX, xx, y, cz - half_z,
                    cgo.VERTEX, xx, y, cz + half_z]
        obj += [cgo.END]
    cmd.delete("viz_membrane")
    cmd.load_cgo(obj, "viz_membrane")
    if not _b(quiet):
        print(" viz_membrane: %.0f A bilayer centred on the structure" % t)
    return t


def viz_bg(background="white", quiet=0):
    """
DESCRIPTION

    Change the background. Gradient presets are composited at render time, so
    the viewport shows their base colour.

USAGE

    viz_bg [background]

    Presets: %s
    """
    txt = _s(background, "white")
    spec = BACKGROUNDS.get(txt.lower(), txt)
    base = spec if isinstance(spec, str) else (spec[2] if spec else "#FFFFFF")
    cmd.bg_color(_color_name(base or "#FFFFFF"))
    if _LAST:
        _LAST["background"] = txt
        _LAST["bg_spec"] = spec
        _LAST["dark_bg"] = _bg_is_dark(spec)
    if not _b(quiet):
        kind = "gradient" if not isinstance(spec, str) else "flat"
        print(" viz_bg: %s (%s)" % (txt, kind))


viz_bg.__doc__ = viz_bg.__doc__ % ", ".join(sorted(BACKGROUNDS))


def viz_reset(selection="all", quiet=0):
    """
DESCRIPTION

    Undo the suite: restore PyMOL's default settings and a plain cartoon.
    """
    for name in _TOUCHED:
        try:
            cmd.unset(name)
        except Exception:
            pass
    sel = _s(selection, "all")
    for name in ("sphere_scale", "transparency", "cartoon_transparency",
                 "stick_radius", "surface_quality"):
        try:
            cmd.unset(name, sel)
        except Exception:
            pass
    for helper in ("viz_contacts", "viz_core", "viz_core_centre",
                   "viz_membrane"):
        cmd.delete(helper)
    cmd.bg_color("black")
    cmd.hide("everything", sel)
    cmd.show("cartoon", "(%s) and polymer" % sel)
    cmd.show("sticks", "(%s) and %s" % (sel, SEL_LIG))
    cmd.show("nonbonded", "(%s) and %s" % (sel, SEL_ION))
    cmd.color("green", "(%s) and elem C" % sel)
    try:
        util.cnc("(%s) and not elem C" % sel, _self=cmd)
    except Exception:
        pass
    cmd.rebuild()
    _LAST.clear()
    if not _b(quiet):
        print(" viz_reset: PyMOL defaults restored.")


def viz_script(filename="", quiet=0):
    """
DESCRIPTION

    Print or save the .pml script equivalent to the last viz call, so the look
    can be reproduced without the plugin.
    """
    if not _LAST_SCRIPT:
        print(" viz_script: nothing to export - run viz first.")
        return ""
    text = "\n".join(_LAST_SCRIPT) + "\n"
    name = _s(filename)
    if name:
        name = os.path.expanduser(name)
        with open(name, "w") as fh:
            fh.write(text)
        if not _b(quiet):
            print(" viz_script: wrote %s" % name)
    else:
        print(text)
    return text


def _srgb_grey(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    enc = 12.92 * y if y <= 0.0031308 else 1.055 * y ** (1 / 2.4) - 0.055
    return 255.0 * enc


def _lab(rgb):
    """CIELAB under D65, for perceptual colour distance."""
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    x = 0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = 0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)
    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def _lab2rgb(lab):
    """Inverse of _lab, clamped into sRGB."""
    L, a, b = lab
    fy = (L + 16.0) / 116.0
    fx, fz = fy + a / 500.0, fy - b / 200.0

    def g(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16.0 / 116.0) / 7.787
    x, y, z = g(fx) * 0.95047, g(fy) * 1.0, g(fz) * 1.08883
    lin = (3.2406 * x - 1.5372 * y - 0.4986 * z,
           -0.9689 * x + 1.8758 * y + 0.0415 * z,
           0.0557 * x - 0.2040 * y + 1.0570 * z)
    out = []
    for c in lin:
        c = max(0.0, min(1.0, c))
        out.append(c * 12.92 if c <= 0.0031308
                   else 1.055 * c ** (1.0 / 2.4) - 0.055)
    return tuple(out)


def _delta_e(a, b):
    la, lb = _lab(a), _lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def _deuteranope(rgb):
    """Vienot/Brettel/Mollon dichromat simulation, applied in linear RGB."""
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    m = ((0.29275, 0.66826, 0.03899), (0.29275, 0.66826, 0.03899),
         (-0.02234, 0.06144, 0.96090))
    out = []
    for row in m:
        v = max(0.0, min(1.0, sum(a * b for a, b in zip(row, lin))))
        out.append(12.92 * v if v <= 0.0031308
                   else 1.055 * v ** (1 / 2.4) - 0.055)
    return out


def viz_check_palettes(chains=4, quiet=0):
    """
DESCRIPTION

    Measure every palette for greyscale-print and colour-blind separation.

    A palette whose colours differ only in hue looks fine on screen and merges
    the moment the figure is printed in black and white or read by someone with
    deuteranopia. This reports the worst pair in each palette for the first
    *chains* slots, so a regression is visible rather than shipped.

USAGE

    viz_check_palettes [chains]
    """
    n = max(2, _i(chains, 4))
    print("\n Worst pair among the first %d slots" % n)
    print(" %-14s %-9s %-9s %s" % ("palette", "greyscale", "dE deut", ""))
    bad = []
    for name in PALETTES:
        cols = _palette(name)[:n]
        greys = [_srgb_grey(c) for c in cols]
        sims = [_deuteranope(c) for c in cols]
        dg = min(abs(greys[i] - greys[j])
                 for i in range(len(cols)) for j in range(i + 1, len(cols)))
        dd = min(_delta_e(sims[i], sims[j])
                 for i in range(len(cols)) for j in range(i + 1, len(cols)))
        ok = dg >= 18.0 and dd >= 15.0
        if not ok:
            bad.append(name)
        print(" %-14s %6.0f    %6.1f    %s" % (name, dg, dd,
                                               "ok" if ok else "MERGES"))
    print("\n Thresholds: >=18/255 greyscale, >=15 CIE76 dE after deuteranopia")
    print(" simulation. An earlier version measured this distance in")
    print(" gamma-encoded sRGB, which inflated a real dE of 9 into '40'.")
    if bad:
        print(" Merging at %d slots: %s" % (n, ", ".join(bad)))
        print(" These stay available on purpose - some are meant to be loud, and")
        print(" beyond about six categories no palette can satisfy both limits.")
    return bad


def viz_list(what="", quiet=0):
    """
DESCRIPTION

    List the available styles, palettes, colourings, backgrounds and presets.

USAGE

    viz_list [styles | palettes | colorings | backgrounds | sizes | views]
    """
    key = _s(what).lower()
    show_all = not key

    if show_all or key.startswith("style"):
        print("\n START HERE")
        for alias, name in STYLE_ALIASES.items():
            print("   %-14s %s" % (alias, STYLES[name]["desc"].split(". ")[0]))
        print("\n STYLES")
        for group, names in STYLE_GROUPS:
            print("   [%s]" % group)
            for n in names:
                print("     %-14s %s" % (n, STYLES[n]["desc"].split(". ")[0]))
    if show_all or key.startswith("palette"):
        print("\n PALETTES")
        line = []
        for n in PALETTES:
            line.append(n)
            if len(line) == 5:
                print("   " + ", ".join(line))
                line = []
        if line:
            print("   " + ", ".join(line))
        print("   (or pass your own: palette=#1B4965/#5FA8D3/#CAE9FF)")
    if show_all or key.startswith("color"):
        print("\n COLOURINGS\n   " + ", ".join(COLORINGS))
    if show_all or key.startswith("background") or key.startswith("bg"):
        print("\n BACKGROUNDS\n   " + ", ".join(sorted(BACKGROUNDS)))
    if show_all or key.startswith("size"):
        print("\n RENDER SIZES")
        for n, (w, h) in SIZES.items():
            print("   %-10s %dx%d" % (n, w, h))
    if show_all or key.startswith("view") or key.startswith("frame"):
        print("\n VIEWS\n   " + ", ".join(VIEWS))
        print(" FRAMES\n   " + ", ".join(FRAMES))
    if show_all:
        print("\n Start: viz paper     then  viz_render ~/figure.png, fit, width=2400")
        print("        viz story     then  viz_render ~/slide.png, slide")
        print(" Explore: viz_gallery     to compare the full catalogue\n")


# ==========================================================================
# figure composition
# ==========================================================================


def _compose(panels, cols=0, tile=0, gap=0.03, bg="#FFFFFF", labels=True,
             title="", label_style="letter"):
    """Lay rendered panels out on a grid. panels: list of (path, caption)."""
    np = _np()
    n = len(panels)
    if not n:
        raise CmdException("nothing to compose")
    cols = _i(cols) or int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / float(cols)))
    imgs = [_img_load(p) for p, _ in panels]
    tw = _i(tile) or max(im.shape[1] for im in imgs)
    th = int(round(tw * max(im.shape[0] / float(im.shape[1]) for im in imgs)))
    pad = int(round(gap * tw))
    cap_h = int(round(0.085 * tw)) if labels else 0
    title_h = int(round(0.11 * tw)) if _s(title) else 0
    W = cols * tw + (cols + 1) * pad
    H = title_h + rows * (th + cap_h) + (rows + 1) * pad
    bg_rgb = np.array(_hex2rgb(bg), np.float32)
    canvas = np.empty((H, W, 4), np.float32)
    canvas[:, :, :3] = bg_rgb
    canvas[:, :, 3] = 1.0
    dark = _lum(_hex2rgb(bg)) < 0.45
    fg = "#F2F2F2" if dark else "#111111"
    items = []

    if title_h:
        items.append(dict(text=_s(title), x=pad, y=int(pad * 0.6),
                          size=int(title_h * 0.52), color=fg, bold=True))
    for i, (im, (_, caption)) in enumerate(zip(imgs, panels)):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = title_h + pad + r * (th + cap_h + pad)
        scaled = _img_resize(im, tw, th)
        rgb = scaled[:, :, :3]
        a = scaled[:, :, 3:4]
        canvas[y:y + th, x:x + tw, :3] = rgb * a + bg_rgb * (1 - a)
        if labels:
            size = int(cap_h * 0.44)
            tag = ""
            if label_style == "letter":
                tag = chr(ord("A") + i) + "  "
            elif label_style == "number":
                tag = "%d  " % (i + 1)
            items.append(dict(text=tag + _s(caption), x=x,
                              y=y + th + int(cap_h * 0.18), size=size,
                              color=fg, bold=True))
    if items:
        canvas = _draw_text(canvas, items)
    return canvas


def _style_fits(name, info):
    """Skip styles that cannot say anything about this structure."""
    if name == "dna":
        return info["nucleic"] > 0
    if name == "chem":
        return info["residues"] <= 12 or info["protein"] + info["nucleic"] == 0
    if name == "licorice":
        return info["residues"] <= 40 or info["protein"] + info["nucleic"] == 0
    if name == "pocket":
        return info["ligand"] >= 6 or info["ion"] >= 1
    if name == "plddt":
        return info["plddt_like"] and info["bmax"] > 20
    if name in ("hydrophobic", "charge"):
        return info["protein"] > 0
    if name in ("putty",):
        return info["bmax"] - info["bmin"] > 2.0
    if name in ("topology",):
        return info["protein"] > 0
    return True


def viz_gallery(selection="", filename="", styles="", cols=0, tile=560,
                size="preview", background="", all=0, quiet=0):
    """
DESCRIPTION

    Render the current structure in every style and lay the results out as a
    labelled contact sheet, so you can pick a look by eye.

USAGE

    viz_gallery [selection [, filename [, styles [, cols [, tile [, size ]]]]]]

ARGUMENTS

    selection = what to render {default: everything}
    filename  = output PNG {default: ~/viz_gallery.png}
    styles    = comma-separated style names, or a group name
                (illustrative, publication, presentation, molecules, analysis),
                or empty for all of them
    tile      = panel width in the sheet {default: 560}
    size      = render size preset for each panel {default: preview}

EXAMPLES

    viz_gallery
    viz_gallery polymer, ~/looks.png, styles=illustrative
    viz_gallery all, ~/dark.png, styles=hero,neon,noir
    """
    if not _img_backend():
        raise CmdException("viz_gallery needs numpy and PyMOL's Qt build (%s)"
                           % _IMG["why"])
    sel = _s(selection) or "all"
    if not cmd.count_atoms(sel):
        raise CmdException("selection '%s' is empty" % sel)
    txt = _s(styles)
    groups = dict(STYLE_GROUPS)
    explicit = True
    if not txt:
        names = [n for _, lst in STYLE_GROUPS for n in lst]
        explicit = False
    elif txt.lower() in groups:
        names = list(groups[txt.lower()])
        explicit = False
    else:
        names = [_resolve(STYLE_ALIASES.get(p.lower(), p), STYLES, "style")
                 for p in re.split(r"[,\s]+", txt) if p]
    if not explicit and not _b(all):
        info = _survey(sel)
        kept = [n for n in names if _style_fits(n, info)]
        dropped = [n for n in names if n not in kept]
        if dropped and not _b(quiet):
            print(" viz_gallery: skipping styles that do not apply here (%s); "
                  "pass all=1 to include them." % ", ".join(dropped))
        names = kept or names

    out = os.path.expanduser(_s(filename) or "~/viz_gallery.png")
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(out)),
                          ".viz_gallery_%d" % os.getpid())
    if not os.path.isdir(tmpdir):
        os.makedirs(tmpdir)
    view = cmd.get_view()
    panels = []
    for i, name in enumerate(names):
        if not _b(quiet):
            print(" viz_gallery: [%d/%d] %s" % (i + 1, len(names), name))
        try:
            viz(name, sel, background=background, quiet=1)
            # close-up styles keep the view they framed for themselves
            if not _style(name)["focus"]:
                cmd.set_view(view)
            path = os.path.join(tmpdir, "%02d_%s.png" % (i, name))
            viz_render(path, size=size, fit=0, quiet=1)
            panels.append((path, name))
        except Exception as exc:
            print(" viz_gallery: %s failed (%s)" % (name, exc))
    if not panels:
        raise CmdException("every style failed")
    canvas = _compose(panels, cols=cols, tile=_i(tile, 560), gap=0.035,
                      bg="#20242B", labels=True, label_style="none",
                      title="Viz Suite - %s" % sel)
    _img_save(canvas, out, 150)
    for path, _ in panels:
        try:
            os.remove(path)
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass
    cmd.set_view(view)
    if not _b(quiet):
        print(" viz_gallery: wrote %s" % out)
    return out


def viz_figure(panels="", filename="figure.png", cols=0, tile=0, title="",
               background="white", labels=1, captions="", quiet=0):
    """
DESCRIPTION

    Compose already-rendered PNGs into a publication figure: even gutters,
    panel letters, optional captions and title.

USAGE

    viz_figure panels, [filename [, cols [, tile [, title [, captions ]]]]]

ARGUMENTS

    panels   = image paths, separated by spaces or | (PyMOL treats commas as
               argument separators, so they cannot be used here). Shell
               wildcards are expanded.
    captions = panel captions separated by | , in panel order. Alternatively
               append ":caption" to each path.
    cols     = columns {default: near-square}
    tile     = panel width in pixels {default: the widest input}
    title    = figure title drawn above the grid

EXAMPLES

    viz_figure ~/a.png ~/b.png, ~/figure1.png, cols=2, captions=apo|holo
    viz_figure ~/panels/*.png, ~/figure1.png, title=Figure 1
    viz_figure ~/a.png:apo | ~/b.png:holo, ~/figure1.png
    """
    if not _img_backend():
        raise CmdException("viz_figure needs numpy and PyMOL's Qt build (%s)"
                           % _IMG["why"])
    import glob

    text = _s(panels)
    if "|" in text:
        chunks = text.split("|")
    else:
        # split on whitespace, but let multi-word captions glue back onto the
        # path they belong to
        chunks = []
        for tok in re.split(r"\s+", text):
            if not tok:
                continue
            if chunks and not re.search(r"\.(png|jpg|jpeg|tif|tiff)\b", tok, re.I):
                chunks[-1] += " " + tok
            else:
                chunks.append(tok)
    items = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        path, sep, caption = chunk.rpartition(":")
        if not sep or not os.path.splitext(path)[1]:
            path, caption = chunk, ""
        path = os.path.expanduser(path.strip())
        hits = sorted(glob.glob(path)) or [path]
        for hit in hits:
            if not os.path.exists(hit):
                raise CmdException("no such image: %s" % hit)
            items.append((hit, caption.strip()))
    if not items:
        raise CmdException("viz_figure needs at least one panel")
    given = [c.strip() for c in _s(captions).split("|")] if _s(captions) else []
    if given:
        items = [(p, given[i] if i < len(given) else c)
                 for i, (p, c) in enumerate(items)]
    bg = BACKGROUNDS.get(_s(background, "white").lower(), _s(background, "white"))
    if not isinstance(bg, str):
        bg = bg[2]
    canvas = _compose(items, cols=cols, tile=tile, bg=bg or "#FFFFFF",
                      labels=_b(labels, True), title=title)
    out = os.path.expanduser(_s(filename, "figure.png"))
    _img_save(canvas, out, 300)
    if not _b(quiet):
        print(" viz_figure: wrote %s (%d panels)" % (out, len(items)))
    return out


def viz_scalebar(length=0, selection="", quiet=0):
    """
DESCRIPTION

    Report the scale of the current view and the pixel length a scale bar will
    have. Pass the result to viz_render's scalebar argument to draw it.

USAGE

    viz_scalebar [length [, selection ]]
    """
    vp = cmd.get_viewport()
    app = _angstrom_per_pixel(vp[1] if vp else 800)
    length = _f(length, 0.0)
    if length <= 0:
        span = _survey(_s(selection) or "all")["span"]
        length = float(max(5, int(round(span / 4.0 / 5.0)) * 5))
    if not _b(quiet):
        print(" viz_scalebar: view spans %.1f A vertically (%.4f A/pixel)"
              % (app * (vp[1] if vp else 800), app))
        print(" viz_scalebar: suggested bar %g A -> viz_render ..., scalebar=%g"
              % (length, length))
    return length


def _project(sel, w, h):
    """Where a selection lands in the rendered image, in pixels.

    Exact for orthoscopic projection, close enough under perspective to anchor a
    callout box."""
    try:
        import numpy
        coords = cmd.get_coords(sel)
    except Exception:
        return None
    if coords is None or len(coords) < 1:
        return None
    v = list(cmd.get_view())
    rot = numpy.array(v[0:9], dtype=float).reshape(3, 3)
    origin = numpy.array(v[12:15], dtype=float)
    seen = (coords - origin).dot(rot)
    app = _angstrom_per_pixel(h)
    if app <= 0:
        return None
    # view[9:11] is the camera's lateral offset from the rotation origin, so
    # the screen centre is not the origin: ignoring it shifts every box
    xs = w / 2.0 + (seen[:, 0] - v[9]) / app
    ys = h / 2.0 - (seen[:, 1] - v[10]) / app
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))


def _dash_rect(rects, x0, y0, x1, y1, hexcol, thick, dash=9, gap=7):
    """A dashed rectangle built from short filled runs."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    step = dash + gap
    for x in range(x0, x1, step):
        run = min(dash, x1 - x)
        rects.append((x, y0, run, thick, hexcol, 1.0))
        rects.append((x, y1 - thick, run, thick, hexcol, 1.0))
    for y in range(y0, y1, step):
        run = min(dash, y1 - y)
        rects.append((x0, y, thick, run, hexcol, 1.0))
        rects.append((x1 - thick, y, thick, run, hexcol, 1.0))


def _dash_line(rects, x0, y0, x1, y1, hexcol, thick, dash=9, gap=7):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) / float(dash + gap)) or 1
    for i in range(n):
        t0 = i / float(n)
        t1 = t0 + dash / float((dash + gap) * n)
        ax, ay = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
        bx, by = x0 + (x1 - x0) * min(t1, 1.0), y0 + (y1 - y0) * min(t1, 1.0)
        steps = max(2, int(max(abs(bx - ax), abs(by - ay))))
        for k in range(steps):
            u = k / float(steps)
            rects.append((int(ax + (bx - ax) * u), int(ay + (by - ay) * u),
                          thick, thick, hexcol, 1.0))


def viz_inset(selection="", filename="inset.png", size="", zoom=6.0,
              corner="", scale=0.42, quiet=0):
    """
DESCRIPTION

    An overview with a magnified callout of one region, boxed on the overview
    and joined to the panel by dashed leaders.

    This is how a figure spans two scales at once: the reader sees where the
    detail sits before they read the detail. Doing it by hand in Illustrator is
    the usual reason a figure takes an afternoon.

USAGE

    viz_inset selection [, filename [, size [, zoom [, corner [, scale ]]]]]

ARGUMENTS

    selection = the region to magnify
    filename  = output PNG
    size      = size preset or WxH for the overview
    zoom      = Angstrom of padding around the selection in the detail panel
    corner    = tl | tr | bl | br, empty to pick the emptiest
    scale     = panel width as a fraction of the overview {default: 0.42}

EXAMPLES

    viz_inset organic, ~/figure.png, dcolumn
    viz_inset resi 145+41+164, ~/site.png, slide, zoom=4, corner=tr
    """
    if not _img_backend():
        raise CmdException("viz_inset needs numpy and PyMOL's Qt build (%s)"
                           % _IMG["why"])
    np = _np()
    sel = _s(selection)
    if not sel or not cmd.count_atoms(sel):
        raise CmdException("viz_inset needs a non-empty selection to magnify")
    w, h = _resolve_size(size, 0, 0)
    path = os.path.expanduser(_s(filename, "inset.png"))
    view = cmd.get_view()
    dark = _LAST.get("dark_bg")
    line = "#F2F2F2" if dark else "#1A1A1A"

    tmp_over = path + ".viz_over.png"
    tmp_det = path + ".viz_det.png"
    # the callout box has to land exactly on the feature it rings, and the
    # projection is only exact under orthoscopic projection
    was_ortho = cmd.get("orthoscopic")
    cmd.set("orthoscopic", 1)
    try:
        # The panel is a large opaque object that has to go somewhere, and
        # fitting the overview to the whole frame guarantees it lands on the
        # specimen. Fit cheaply first, back the camera off by the panel's
        # share of the frame, then render without refitting.
        viz_render(tmp_over, size="%dx%d" % (max(240, w // 4),
                                             max(160, h // 4)),
                   scalebar=0, legend=0, quiet=1)
        _scale_field(1.0 + 0.68 * max(0.2, min(0.6, _f(scale, 0.42))))
        viz_render(tmp_over, size="%dx%d" % (w, h), scalebar=0, legend=0,
                   fit=0, quiet=1)
        # projected after the render, so the fit that render applied is included
        box = _project(sel, w, h)

        pw = int(w * max(0.2, min(0.6, _f(scale, 0.42))))
        ph = int(pw * 0.82)
        cmd.orient(sel)
        cmd.zoom(sel, _f(zoom, 6.0))
        viz_render(tmp_det, size="%dx%d" % (pw, ph), scalebar=0, legend=0,
                   name="-", fit=0, quiet=1)

        over = _img_load(tmp_over)
        det = _img_load(tmp_det)
        if det.shape[0] != ph or det.shape[1] != pw:
            det = _img_resize(det, pw, ph)

        pad = int(0.035 * min(w, h))
        pick = _s(corner).lower()
        if pick in ("tl", "tr", "bl", "br"):
            px = (w - pad - pw) if pick.endswith("r") else pad
            py = pad if pick.startswith("t") else (h - pad - ph)
        else:
            px, py = _legend_place(over[:, :, 3], w, h, pw, ph, pad)

        rects, border = [], max(2, int(0.0022 * w))
        if box:
            x0 = max(0, box[0] - 0.02 * w)
            y0 = max(0, box[1] - 0.02 * h)
            x1 = min(w, box[2] + 0.02 * w)
            y1 = min(h, box[3] + 0.02 * h)
            _dash_rect(rects, x0, y0, x1, y1, line, border)
            bcx, bcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            ax = px if px > bcx else px + pw
            _dash_line(rects, (x1 if ax > bcx else x0), y0, ax, py, line,
                       max(1, border - 1))
            _dash_line(rects, (x1 if ax > bcx else x0), y1, ax, py + ph, line,
                       max(1, border - 1))
        out = over.copy()
        if rects:
            out = _draw_rects(out, rects)
        # the panel sits on an opaque plate so the overview cannot show through
        plate = np.ones((ph + 2 * border, pw + 2 * border, 4), np.float32)
        plate[:, :, :3] = np.array(_hex2rgb(line), np.float32)
        oy, ox = py - border, px - border
        oy = max(0, min(oy, h - plate.shape[0]))
        ox = max(0, min(ox, w - plate.shape[1]))
        out[oy:oy + plate.shape[0], ox:ox + plate.shape[1]] = plate
        out[oy + border:oy + border + ph, ox + border:ox + border + pw] = det
        out[:, :, 3] = 1.0
        _img_save(out, path, 300)
        if not _b(quiet):
            print(" viz_inset: wrote %s (%dx%d, panel %s)" % (path, w, h, pick))
        return path
    finally:
        for f in (tmp_over, tmp_det):
            if os.path.exists(f):
                os.remove(f)
        try:
            cmd.set("orthoscopic", was_ortho)
        except Exception:
            pass
        cmd.set_view(view)


def viz_turntable(prefix="frame", frames=36, size="preview", axis="y",
                  quiet=0):
    """
DESCRIPTION

    Render a full rotation as a numbered PNG sequence, ready for a movie or an
    animated GIF made elsewhere.

USAGE

    viz_turntable [prefix [, frames [, size [, axis ]]]]
    """
    n = max(2, _i(frames, 36))
    prefix = os.path.expanduser(_s(prefix, "frame"))
    step = 360.0 / n
    ax = _s(axis, "y")
    out = []
    for i in range(n):
        path = "%s_%04d.png" % (prefix, i)
        viz_render(path, size=size, fit=0, quiet=1)
        out.append(path)
        cmd.turn(ax, step)
        if not _b(quiet):
            print(" viz_turntable: %d/%d" % (i + 1, n))
    if not _b(quiet):
        print(" viz_turntable: wrote %d frames as %s_0000.png ..." % (n, prefix))
    return out


# ==========================================================================
# registration
# ==========================================================================

_COMMANDS = {
    "viz": viz,
    "viz_auto": viz_auto,
    "viz_render": viz_render,
    "viz_color": viz_color,
    "viz_view": viz_view,
    "viz_frame": viz_frame,
    "viz_bg": viz_bg,
    "viz_gallery": viz_gallery,
    "viz_figure": viz_figure,
    "viz_scalebar": viz_scalebar,
    "viz_turntable": viz_turntable,
    "viz_script": viz_script,
    "viz_reset": viz_reset,
    "viz_list": viz_list,
    "viz_check_palettes": viz_check_palettes,
    "viz_focus": viz_focus,
    "viz_label": viz_label,
    "viz_membrane": viz_membrane,
    "viz_inset": viz_inset,
    "viz_pose": viz_pose,
    "viz_cutaway": viz_cutaway,
    "viz_gaps": viz_gaps,
    "viz_mix": viz_mix,
    "viz_interface": viz_interface,
    "viz_partners": viz_partners,
    "viz_openbook": viz_openbook,
    "viz_contact_table": viz_contact_table,
    "viz_paint": viz_paint,
    "viz_highlight": viz_highlight,
    "viz_super": viz_super,
}

for _name, _fn in _COMMANDS.items():
    cmd.extend(_name, _fn)

cmd.auto_arg[0]["viz"] = [lambda: cmd.Shortcut(
    ["auto"] + list(STYLE_ALIASES) + list(STYLES)),
                          "style", ", "]
cmd.auto_arg[1]["viz"] = cmd.auto_arg[0]["zoom"]
cmd.auto_arg[0]["viz_color"] = [lambda: cmd.Shortcut(list(COLORINGS)),
                                "coloring", ", "]
cmd.auto_arg[1]["viz_color"] = [lambda: cmd.Shortcut(list(PALETTES)),
                                "palette", ", "]
cmd.auto_arg[0]["viz_view"] = [lambda: cmd.Shortcut(list(VIEWS)),
                               "view preset", ", "]
cmd.auto_arg[0]["viz_frame"] = [lambda: cmd.Shortcut(list(FRAMES)),
                                "frame preset", ", "]
cmd.auto_arg[0]["viz_bg"] = [lambda: cmd.Shortcut(list(BACKGROUNDS)),
                             "background", ", "]
cmd.auto_arg[0]["viz_auto"] = cmd.auto_arg[0]["zoom"]
cmd.auto_arg[0]["viz_reset"] = cmd.auto_arg[0]["zoom"]
cmd.auto_arg[1]["viz_render"] = [lambda: cmd.Shortcut(list(SIZES)),
                                 "size preset", ", "]

# ==========================================================================
# Qt panel
# ==========================================================================

_dialog = None


def __init_plugin__(app=None):
    try:
        from pymol.plugins import addmenuitemqt
        addmenuitemqt("Viz Suite", run_plugin_gui)
    except Exception as exc:          # pragma: no cover - headless PyMOL
        print("pymol_vizsuite: no Qt menu in this PyMOL build%s; the viz "
              "commands are available." % ((": %s" % exc) if str(exc) else ""))


def run_plugin_gui():
    global _dialog
    if _dialog is None:
        _dialog = _make_dialog()
    _dialog.show()
    _dialog.raise_()


def viz_gui(quiet=0):
    """
DESCRIPTION

    Open the Viz Suite panel: style gallery, palette picker, sliders, and
    Apply / Render / Gallery buttons.

    The Plugin menu entry only exists when the suite is installed through the
    Plugin Manager. Loaded with `run`, this command is how you open the panel.
    """
    run_plugin_gui()


cmd.extend("viz_gui", viz_gui)


def _swatch_icon(QtGui, QtCore, colors, w=64, h=14):
    """A palette preview strip for the palette combo box."""
    img = QtGui.QPixmap(w, h)
    img.fill(QtGui.QColor(0, 0, 0, 0))
    p = QtGui.QPainter(img)
    n = max(1, min(len(colors), 8))
    step = w / float(n)
    for i in range(n):
        c = colors[i]
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(*[int(round(v * 255)) for v in c]))
        p.drawRect(int(i * step), 0, int(step) + 1, h)
    p.end()
    return QtGui.QIcon(img)


def _make_dialog():
    from pymol.Qt import QtCore, QtGui, QtWidgets

    dlg = QtWidgets.QDialog()
    dlg.setWindowTitle("PyMOL Viz Suite %s" % __version__)
    dlg.setMinimumWidth(460)
    outer = QtWidgets.QVBoxLayout(dlg)

    # ---- header ----------------------------------------------------------
    head = QtWidgets.QHBoxLayout()
    b_auto = QtWidgets.QPushButton("Auto")
    b_auto.setToolTip("Inspect the structure and pick a style for it")
    w_sel = QtWidgets.QLineEdit("")
    w_sel.setPlaceholderText("selection (blank = everything)")
    head.addWidget(QtWidgets.QLabel("Selection"))
    head.addWidget(w_sel, 1)
    head.addWidget(b_auto)
    outer.addLayout(head)

    tabs = QtWidgets.QTabWidget()
    outer.addWidget(tabs)

    # ---- style tab -------------------------------------------------------
    style_page = QtWidgets.QWidget()
    sp = QtWidgets.QVBoxLayout(style_page)
    w_style = QtWidgets.QListWidget()
    w_style.setAlternatingRowColors(True)
    for group, names in STYLE_GROUPS:
        head_item = QtWidgets.QListWidgetItem("— %s —" % group)
        head_item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        f = head_item.font()
        f.setBold(True)
        head_item.setFont(f)
        w_style.addItem(head_item)
        for n in names:
            item = QtWidgets.QListWidgetItem("   " + n)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, n)
            item.setToolTip(STYLES[n]["desc"])
            w_style.addItem(item)
    w_style.setMinimumHeight(210)
    sp.addWidget(w_style)
    w_desc = QtWidgets.QLabel("Pick a style, or press Auto.")
    w_desc.setWordWrap(True)
    w_desc.setStyleSheet("color: grey;")
    w_desc.setMinimumHeight(44)
    sp.addWidget(w_desc)
    tabs.addTab(style_page, "Style")

    # ---- look tab --------------------------------------------------------
    look_page = QtWidgets.QWidget()
    form = QtWidgets.QFormLayout(look_page)

    w_color = QtWidgets.QComboBox()
    w_color.addItem("(style default)")
    w_color.addItems(list(COLORINGS))
    form.addRow("Colouring", w_color)

    w_palette = QtWidgets.QComboBox()
    w_palette.addItem("(style default)")
    for name in PALETTES:
        w_palette.addItem(_swatch_icon(QtGui, QtCore, _palette(name)), name)
    w_palette.setIconSize(QtCore.QSize(64, 14))
    form.addRow("Palette", w_palette)

    w_bg = QtWidgets.QComboBox()
    w_bg.addItem("(style default)")
    w_bg.addItems(sorted(BACKGROUNDS))
    w_bg.setEditable(True)
    form.addRow("Background", w_bg)

    w_rep = QtWidgets.QComboBox()
    w_rep.addItem("(style default)")
    w_rep.addItems(list(REPS) + ["nucleic+" + r for r in
                                ("surface", "cartoon", "spheres", "tube")])
    form.addRow("Representation", w_rep)

    w_light = QtWidgets.QComboBox()
    w_light.addItem("(style default)")
    w_light.addItems(list(LIGHTING))
    form.addRow("Lighting", w_light)

    def slider(lo, hi, val, step=1):
        s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSingleStep(step)
        return s

    w_outline = slider(0, 120, -1)
    w_outline_lbl = QtWidgets.QLabel("style default")
    row = QtWidgets.QHBoxLayout()
    row.addWidget(w_outline, 1)
    row.addWidget(w_outline_lbl)
    w_outline.setValue(0)
    w_outline_use = QtWidgets.QCheckBox("override")
    row.addWidget(w_outline_use)
    form.addRow("Ink outline", row)

    w_ao = slider(0, 200, 100)
    w_ao_lbl = QtWidgets.QLabel("1.00x")
    row2 = QtWidgets.QHBoxLayout()
    row2.addWidget(w_ao, 1)
    row2.addWidget(w_ao_lbl)
    form.addRow("Occlusion", row2)

    w_blob = slider(10, 60, 14)
    w_blob_lbl = QtWidgets.QLabel("1.4 A")
    row3 = QtWidgets.QHBoxLayout()
    row3.addWidget(w_blob, 1)
    row3.addWidget(w_blob_lbl)
    form.addRow("Surface blob", row3)

    w_fog = slider(0, 100, -1)
    w_fog.setValue(0)
    w_fog_use = QtWidgets.QCheckBox("override")
    row4 = QtWidgets.QHBoxLayout()
    row4.addWidget(w_fog, 1)
    row4.addWidget(w_fog_use)
    form.addRow("Depth fade", row4)

    w_glow = slider(0, 200, 0)
    w_glow_use = QtWidgets.QCheckBox("override")
    row5 = QtWidgets.QHBoxLayout()
    row5.addWidget(w_glow, 1)
    row5.addWidget(w_glow_use)
    form.addRow("Glow", row5)

    w_vig = slider(0, 100, 0)
    w_vig_use = QtWidgets.QCheckBox("override")
    row6 = QtWidgets.QHBoxLayout()
    row6.addWidget(w_vig, 1)
    row6.addWidget(w_vig_use)
    form.addRow("Vignette", row6)

    w_sat = slider(0, 250, 100)
    w_sat_use = QtWidgets.QCheckBox("override")
    row7 = QtWidgets.QHBoxLayout()
    row7.addWidget(w_sat, 1)
    row7.addWidget(w_sat_use)
    form.addRow("Saturation", row7)

    opts = QtWidgets.QHBoxLayout()
    w_hydro = QtWidgets.QCheckBox("hydrogens")
    w_water = QtWidgets.QCheckBox("waters")
    w_live = QtWidgets.QCheckBox("live apply")
    w_live.setChecked(True)
    for wdg in (w_hydro, w_water, w_live):
        opts.addWidget(wdg)
    opts.addStretch(1)
    form.addRow("Show", opts)
    tabs.addTab(look_page, "Look")

    # ---- output tab ------------------------------------------------------
    out_page = QtWidgets.QWidget()
    of = QtWidgets.QFormLayout(out_page)

    w_view = QtWidgets.QComboBox()
    w_view.addItem("(keep camera)")
    w_view.addItems(list(VIEWS))
    of.addRow("Camera", w_view)

    w_frame = QtWidgets.QComboBox()
    w_frame.addItem("(keep frame)")
    w_frame.addItems(list(FRAMES))
    of.addRow("Aspect", w_frame)

    w_size = QtWidgets.QComboBox()
    w_size.addItems(list(SIZES))
    w_size.setCurrentText("slide")
    of.addRow("Render size", w_size)

    w_dpi = QtWidgets.QSpinBox()
    w_dpi.setRange(72, 1200)
    w_dpi.setValue(300)
    of.addRow("DPI", w_dpi)

    w_bar = QtWidgets.QDoubleSpinBox()
    w_bar.setRange(0.0, 1000.0)
    w_bar.setSingleStep(5.0)
    w_bar.setValue(0.0)
    w_bar.setToolTip("Scale bar length in Angstrom; 0 for none")
    of.addRow("Scale bar", w_bar)

    w_cap = QtWidgets.QLineEdit("")
    w_cap.setPlaceholderText("caption drawn bottom-left")
    of.addRow("Caption", w_cap)

    w_lab = QtWidgets.QLineEdit("")
    w_lab.setPlaceholderText("panel letter, e.g. A")
    of.addRow("Panel label", w_lab)

    w_trans = QtWidgets.QCheckBox("transparent background")
    of.addRow("", w_trans)
    tabs.addTab(out_page, "Output")

    hint = QtWidgets.QLabel(
        "Ink outlines and ambient occlusion are baked at render time. The "
        "viewport shows a preview; press Render for the finished image.")
    hint.setWordWrap(True)
    hint.setStyleSheet("color: grey; font-size: 11px;")
    outer.addWidget(hint)

    status = QtWidgets.QLabel("")
    status.setWordWrap(True)
    status.setStyleSheet("color: #2A7; font-size: 11px;")
    outer.addWidget(status)

    # ---- buttons ---------------------------------------------------------
    btns = QtWidgets.QHBoxLayout()
    b_apply = QtWidgets.QPushButton("Apply")
    b_ray = QtWidgets.QPushButton("Preview ray")
    b_render = QtWidgets.QPushButton("Render...")
    b_gallery = QtWidgets.QPushButton("Gallery...")
    b_script = QtWidgets.QPushButton("Save .pml...")
    b_reset = QtWidgets.QPushButton("Reset")
    for b in (b_apply, b_ray, b_render, b_gallery, b_script, b_reset):
        btns.addWidget(b)
    outer.addLayout(btns)

    # ---- behaviour -------------------------------------------------------
    def current_style():
        item = w_style.currentItem()
        if item is None:
            return ""
        return item.data(QtCore.Qt.ItemDataRole.UserRole) or ""

    def sync_labels():
        w_outline_lbl.setText("%.4f" % (w_outline.value() / 10000.0)
                              if w_outline_use.isChecked() else "style default")
        w_ao_lbl.setText("%.2fx" % (w_ao.value() / 100.0))
        w_blob_lbl.setText("%.1f A" % (w_blob.value() / 10.0))

    def on_style_changed():
        name = current_style()
        if not name:
            return
        st = _style(name)
        w_desc.setText(st["desc"])
        w_blob.setValue(int(round(st["blob"] * 10)))
        w_outline.setValue(int(round(st["outline"] * 10000)))
        sync_labels()
        if w_live.isChecked():
            do_apply()

    def kwargs():
        kw = dict(selection=w_sel.text().strip(), quiet=1)
        if w_color.currentIndex() > 0:
            kw["coloring"] = w_color.currentText()
        if w_palette.currentIndex() > 0:
            kw["palette"] = w_palette.currentText()
        if w_bg.currentIndex() > 0 or w_bg.currentText().startswith("#"):
            kw["background"] = w_bg.currentText().strip()
        if w_rep.currentIndex() > 0:
            kw["rep"] = w_rep.currentText()
        if w_light.currentIndex() > 0:
            kw["light"] = w_light.currentText()
        if w_outline_use.isChecked():
            kw["outline"] = w_outline.value() / 10000.0
        if w_fog_use.isChecked():
            kw["fog"] = w_fog.value() / 100.0
        if w_glow_use.isChecked():
            kw["glow"] = w_glow.value() / 100.0
        if w_vig_use.isChecked():
            kw["vignette"] = w_vig.value() / 100.0
        if w_sat_use.isChecked():
            kw["saturation"] = w_sat.value() / 100.0
        kw["ao"] = w_ao.value() / 100.0
        kw["blob"] = w_blob.value() / 10.0
        kw["hydrogens"] = 1 if w_hydro.isChecked() else 0
        kw["waters"] = 1 if w_water.isChecked() else 0
        if w_view.currentIndex() > 0:
            kw["view"] = w_view.currentText()
        if w_frame.currentIndex() > 0:
            kw["frame"] = w_frame.currentText()
        return kw

    def guard(fn):
        try:
            fn()
        except Exception as exc:
            status.setStyleSheet("color: #C33; font-size: 11px;")
            status.setText(str(exc))
        else:
            status.setStyleSheet("color: #2A7; font-size: 11px;")

    def do_apply():
        name = current_style() or "auto"

        def run():
            viz(name, **kwargs())
            status.setText("applied '%s'" % _LAST.get("style", name))
        guard(run)

    def do_auto():
        def run():
            viz_auto(w_sel.text().strip(), quiet=1)
            name = _LAST.get("style", "")
            for i in range(w_style.count()):
                if w_style.item(i).data(QtCore.Qt.ItemDataRole.UserRole) == name:
                    w_style.setCurrentRow(i)
                    break
            status.setText("auto-selected '%s'" % name)
        guard(run)

    def do_ray():
        guard(lambda: cmd.ray())

    def render_kwargs():
        kw = dict(size=w_size.currentText(), dpi=w_dpi.value(),
                  scalebar=w_bar.value(), caption=w_cap.text().strip(),
                  label=w_lab.text().strip(),
                  transparent=1 if w_trans.isChecked() else 0, quiet=1)
        return kw

    def do_render():
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            dlg, "Render image", "figure.png", "PNG (*.png)")
        if not path:
            return

        def run():
            if not _LAST:
                do_apply()
            viz_render(path, **render_kwargs())
            status.setText("wrote %s" % path)
        guard(run)

    def do_gallery():
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            dlg, "Save style gallery", "viz_gallery.png", "PNG (*.png)")
        if not path:
            return

        def run():
            viz_gallery(w_sel.text().strip(), path, quiet=1)
            status.setText("wrote %s" % path)
        guard(run)

    def do_script():
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            dlg, "Save PyMOL script", "viz.pml", "PyMOL script (*.pml)")
        if not path:
            return

        def run():
            if not _LAST_SCRIPT:
                do_apply()
            viz_script(path, quiet=1)
            status.setText("wrote %s" % path)
        guard(run)

    def do_reset():
        def run():
            viz_reset(w_sel.text().strip() or "all", quiet=1)
            status.setText("reset to PyMOL defaults")
        guard(run)

    def live(_=None):
        sync_labels()
        if w_live.isChecked() and current_style():
            do_apply()

    w_style.currentItemChanged.connect(lambda *_: on_style_changed())
    for wdg in (w_color, w_palette, w_rep, w_light, w_bg):
        wdg.currentIndexChanged.connect(live)
    for wdg in (w_outline, w_ao, w_blob, w_fog, w_glow, w_vig, w_sat):
        wdg.sliderReleased.connect(live)
        wdg.valueChanged.connect(lambda *_: sync_labels())
    for wdg in (w_hydro, w_water, w_outline_use, w_fog_use, w_glow_use,
                w_vig_use, w_sat_use):
        wdg.stateChanged.connect(live)
    b_apply.clicked.connect(do_apply)
    b_auto.clicked.connect(do_auto)
    b_ray.clicked.connect(do_ray)
    b_render.clicked.connect(do_render)
    b_gallery.clicked.connect(do_gallery)
    b_script.clicked.connect(do_script)
    b_reset.clicked.connect(do_reset)

    sync_labels()
    return dlg
