# KLayout and gdsfactory, explained plainly

Written for myself before the Sivers Photonics CAD Designer interview, September 2026.
The aim is to be able to say what each tool is, who uses it and why, without bluffing.

## First, what a layout file is

A chip is made layer by layer. Each lithography step needs a two-dimensional drawing of
where material stays and where it goes. The drawing is a set of polygons, each tagged
with a **layer number** (and a **datatype**) that the fab maps onto a process step:
ridge etch, isolation, contact, metal, and so on. That mapping is the fab's **layer map**
and it belongs to the process, not to the drawing.

The drawings are stored in **GDSII** (the 1980s industry standard, still universal) or
**OASIS** (its newer, much smaller replacement). Both hold **cells**: a cell is a named
piece of geometry that can be placed many times as an **instance**. A die is a cell. A
wafer map is one die cell instanced across the wafer. Change the cell and every instance
follows. That is hierarchy, and it is why a layout file for a million-device wafer can be
a few megabytes.

Coordinates are integers in a **database unit**, usually 1 nm. Every tool asks you to
think in microns and quietly multiplies by a thousand. Mixing the two is the easiest
mistake to make.

## KLayout

**What it is.** A free, open-source layout editor and viewer, written by Matthias Koefferlein
since 2006. Runs on Windows, Linux and macOS. It reads and writes GDSII, OASIS, DXF,
CIF and more.

**Who uses it and why.** Almost every fab and design group has it installed, even the
ones that draw in something else, because it is the fastest way to open a GDS file and
look at it. Smaller fabs, universities and photonics groups use it as their main editor.

**What it does.**

- Interactive drawing: boxes, paths, polygons, text, with rulers and snapping.
- **Layer panel and cell tree**: you see the hierarchy, not just a picture.
- **Scripting** in Python and Ruby. The whole database is available as objects:
  `Layout`, `Cell`, `Region`, `Box`, `Polygon`. A layout can be generated entirely from
  code with no GUI, which is what my scripts do.
- **Boolean operations on layers**: union, difference, intersection, sizing. My THz
  script derives the etched gap layer as "the CPW window minus the metal", which is
  how a negative mask comes out of a positive drawing.
- **Design rule checking (DRC)**: a built-in engine with its own script language, and
  the same checks callable from Python (`width_check`, `space_check`, enclosure and so
  on). It reports violations as edge pairs you can click on.
- **PCells** (parametric cells): cells generated from parameters in the GUI, so a ring
  with a different gap is a number change, not a redraw.
- **Headless rendering**: `klayout.lay.LayoutView` draws to PNG without a window, which
  is what a batch report or a CI job would use.
- Netlist extraction and layout-versus-schematic for electronic designs, which I have
  not used.

**What I found out the hard way.** The width check has an angle limit, default 90
degrees. A taper end face meeting a slanted edge at 89.6 degrees was reported as a
narrow feature. Real rule decks set the limit lower.

## gdsfactory

**What it is.** An open-source Python library for building layouts from code, aimed
mainly at photonics. It started at MIT and Berkeley groups and is now maintained by a
company of the same name. Under the hood it uses KLayout's database (through a wrapper
called kfactory), so anything it makes, KLayout opens.

**Who uses it and why.** Photonics research groups and several foundries publish
**process design kits (PDKs)** for it: the layer map, the design rules, the standard
waveguide cross-sections and a library of components that already obey the rules.
A designer then assembles a chip in Python instead of drawing it.

**The ideas that matter.**

- **Components are functions.** `straight(length=80)`, `ring_single(gap=0.2, radius=10)`,
  `taper(length=10, width1=0.5, width2=0.8)`. Decorate with `@gf.cell` and the result is
  cached and named from its parameters, so two identical calls give one cell.
- **Cross-sections.** A waveguide is a cross-section (which layers, what widths, what
  offsets) swept along a path. My CPW is one cross-section: signal on the metal layer,
  two slots on the gap layer.
- **Ports.** Every component has named ports with a position, width, direction and
  layer. Components are joined with `connect()`, by port name, not by coordinate.
  Mis-matched widths or layers raise an error instead of a silent gap.
- **PDK activation.** Nothing builds until a PDK is active. The generic one ships with
  the package; a fab supplies its own.
- **Output.** `write_gds()` and `write_oas()`, plus netlists, 3D views and simulation
  hooks that I have not touched.

## How they relate

gdsfactory generates; KLayout edits, views and checks. In practice you write a
gdsfactory script, look at the result in KLayout, run DRC there, and iterate. The
advert's "GDS Factory" is this library.

## Against the other two tools in the advert

- **L-Edit** (Tanner, now Siemens) is the paid, GUI-first equivalent of KLayout, common
  in compound semiconductor and MEMS fabs. Its parametric cells are called T-Cells. The
  concepts are the same; I have not used it.
- **AutoCAD** is 2D drafting for the physical world: cleanroom layouts, tool footprints,
  brackets and jigs. It exchanges DXF, which KLayout can also read and write. I have not
  used it either.

## Words to be able to use correctly

GDSII, OASIS, DXF; layer and datatype; cell, instance, hierarchy; PCell; cross-section;
port; PDK; DRC and LVS; Boolean; database unit; mask polarity (dark field or clear field);
alignment mark; reticle; wafer map.

## What I have actually done in each

- KLayout, Python API: a six-layer photonics test die with a width and gap sweep, a DRC
  pass, a wafer-map array, GDS and OASIS export; and a mask-style layout of my own MSc
  terahertz CPW cavities, including a Boolean-derived gap layer, a trench layer, a
  design-rule check that flags which interdigitated capacitor variants need e-beam, and
  DXF export.
- gdsfactory: the same test structures from PDK cells joined by port, and the CPW
  cavities from a custom cross-section.
- Not done: PCells in the KLayout GUI, a real foundry PDK, a KLayout DRC script file,
  mask data preparation, L-Edit, AutoCAD.
