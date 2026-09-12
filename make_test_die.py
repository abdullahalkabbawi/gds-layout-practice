"""Build a small photonics test die with KLayout's Python API (klayout.db), run two
design-rule checks on it, then write GDSII and OASIS.

First KLayout script, written the weekend before the Sivers Photonics interview
(September 2026). Everything is parametric so the same code regenerates the die with
different widths, gaps or die sizes. The database unit is 1 nm and every helper takes
microns.
"""
import math
import os
import klayout.db as db

# ---------------------------------------------------------------- settings ---
DBU_UM = 0.001                          # database unit in microns (1 nm)
DIE_W_UM, DIE_H_UM = 2000.0, 1500.0
WG_WIDTHS_UM = [1.5, 2.0, 2.5, 3.0]     # ridge width sweep (a small design of experiments)
RING_GAPS_UM = [0.20, 0.30, 0.40]       # ring to bus coupling gap sweep
RING_RADIUS_UM = 40.0
MIN_WIDTH_UM = 1.0                      # design rules used by the checks below
MIN_SPACE_UM = 0.15

# Layer map: (GDS layer, datatype). In a real fab this comes from the process design
# kit, not from the layout script.
LAYERS = {
    "WG":    (1, 0),    # waveguide ridge etch
    "MET":   (2, 0),    # top metal contact
    "ISO":   (3, 0),    # isolation trench
    "ALIGN": (10, 0),   # lithography alignment marks
    "TEXT":  (20, 0),   # labels, not on any mask
    "FRAME": (99, 0),   # die outline, for the wafer map only
}


def um(x):
    """Microns to database units."""
    return int(round(x / DBU_UM))


# --------------------------------------------------------------- geometry ---
def rect(x0, y0, x1, y1):
    return db.Box(um(x0), um(y0), um(x1), um(y1))


def straight_waveguide(width, length, x0=0.0, y0=0.0):
    """A straight ridge of the given width starting at (x0, y0) and running in +x."""
    return rect(x0, y0 - width / 2, x0 + length, y0 + width / 2)


def taper(w_in, w_out, length, x0=0.0, y0=0.0):
    """A linear taper from w_in to w_out along +x."""
    pts = [
        db.Point(um(x0), um(y0 - w_in / 2)),
        db.Point(um(x0 + length), um(y0 - w_out / 2)),
        db.Point(um(x0 + length), um(y0 + w_out / 2)),
        db.Point(um(x0), um(y0 + w_in / 2)),
    ]
    return db.Polygon(pts)


def ring(cx, cy, radius, width, n_pts=256):
    """An annulus of mean radius `radius` and ring width `width`, built as the
    difference of two circle polygons. Returned as a Region so it can hold the hole."""
    def circle(r):
        return db.Polygon([
            db.Point(um(cx + r * math.cos(2 * math.pi * i / n_pts)),
                     um(cy + r * math.sin(2 * math.pi * i / n_pts)))
            for i in range(n_pts)
        ])
    return db.Region(circle(radius + width / 2)) - db.Region(circle(radius - width / 2))


def alignment_cross(cx, cy, arm=50.0, line=4.0):
    """A plus-shaped alignment mark."""
    return [rect(cx - arm, cy - line / 2, cx + arm, cy + line / 2),
            rect(cx - line / 2, cy - arm, cx + line / 2, cy + arm)]


def label(text, x, y, height_um=20.0):
    """Text as polygons using KLayout's built-in default font."""
    gen = db.TextGenerator.default_generator()
    font_height_um = gen.height() * gen.dbu()
    reg = gen.text(text, DBU_UM, height_um / font_height_um)
    reg.move(um(x), um(y))
    return reg


# ------------------------------------------------------------------ build ---
def build_die(layout):
    lay = {name: layout.layer(*ld) for name, ld in LAYERS.items()}
    die = layout.create_cell("TEST_DIE")

    # Die outline on the frame layer (not a mask layer)
    die.shapes(lay["FRAME"]).insert(rect(0, 0, DIE_W_UM, DIE_H_UM))

    # Alignment marks in the four corners
    for cx, cy in [(100, 100), (DIE_W_UM - 100, 100),
                   (100, DIE_H_UM - 100), (DIE_W_UM - 100, DIE_H_UM - 100)]:
        for box in alignment_cross(cx, cy):
            die.shapes(lay["ALIGN"]).insert(box)

    # Block 1: straight waveguide width sweep. Each ridge gets input and output tapers,
    # a metal contact over the middle and a probe pad, so every device can be tested.
    y, pitch = 300.0, 120.0
    x_start, taper_len, wg_len = 200.0, 100.0, 1200.0
    for w in WG_WIDTHS_UM:
        die.shapes(lay["WG"]).insert(taper(3.0, w, taper_len, x_start, y))
        die.shapes(lay["WG"]).insert(straight_waveguide(w, wg_len, x_start + taper_len, y))
        die.shapes(lay["WG"]).insert(taper(w, 3.0, taper_len, x_start + taper_len + wg_len, y))
        xm = x_start + taper_len + wg_len / 2
        die.shapes(lay["MET"]).insert(rect(xm - 200, y - w / 2 - 1, xm + 200, y + w / 2 + 1))
        die.shapes(lay["MET"]).insert(rect(xm - 40, y + 20, xm + 40, y + 100))
        die.shapes(lay["MET"]).insert(rect(xm - 4, y, xm + 4, y + 20))
        die.shapes(lay["TEXT"]).insert(label(f"WG {w:.1f}um", x_start, y + 30, 15))
        y += pitch

    # Block 2: ring resonators with a coupling gap sweep on a shared bus width
    bus_w, y, x = 2.0, 900.0, 300.0
    for gap in RING_GAPS_UM:
        cy = y + bus_w / 2 + gap + bus_w / 2 + RING_RADIUS_UM
        die.shapes(lay["WG"]).insert(straight_waveguide(bus_w, 300.0, x, y))
        die.shapes(lay["WG"]).insert(ring(x + 150.0, cy, RING_RADIUS_UM, bus_w))
        die.shapes(lay["TEXT"]).insert(label(f"RING gap {gap:.2f}um", x, y - 40, 15))
        x += 450.0

    # Isolation trench around the ring block, and a die label
    die.shapes(lay["ISO"]).insert(rect(250, 850, 1650, 1100))
    die.shapes(lay["TEXT"]).insert(label("SIVERS PREP DIE R1", 700, 1350, 40))
    return die, lay


def build_wafer_map(layout, die, nx=3, ny=2, street=150.0):
    """Step the die into a small array to show hierarchy: one die cell, many instances.
    A real wafer map would use the reticle and wafer geometry from the fab."""
    top = layout.create_cell("WAFER_MAP")
    arr = db.CellInstArray(die.cell_index(), db.Trans(db.Vector(0, 0)),
                           db.Vector(um(DIE_W_UM + street), 0),
                           db.Vector(0, um(DIE_H_UM + street)), nx, ny)
    top.insert(arr)
    return top


# ------------------------------------------------------------------- DRC ---
def run_checks(die, lay):
    """Two rules on the waveguide layer: minimum width and minimum space. These are
    the Region checks that KLayout's DRC engine wraps.

    The width check is run twice. With KLayout's default angle limit of 90 degrees
    it reports 12 false positives, all at the wide end faces of the tapers: the
    slanted taper edge meets the vertical end face at 89.6 degrees, which is just
    under the limit, so the corner is measured as a narrow feature. Real design-rule
    decks set a lower angle limit for exactly this reason, so the second run uses
    80 degrees and reports the true count."""
    wg = db.Region(die.begin_shapes_rec(lay["WG"]))
    wg.merge()
    width_default = wg.width_check(um(MIN_WIDTH_UM))
    width_angle80 = wg.width_check(um(MIN_WIDTH_UM), False, db.Region.Euclidian, 80.0)
    space_viol = wg.space_check(um(MIN_SPACE_UM))
    return len(width_default), len(width_angle80), len(space_viol), wg.count()


# ------------------------------------------------------------------- main ---
if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    layout = db.Layout()
    layout.dbu = DBU_UM
    die, lay = build_die(layout)
    top = build_wafer_map(layout, die)

    n_w90, n_w80, n_space, n_wg = run_checks(die, lay)
    print(f"die cell '{die.name}': {n_wg} merged waveguide polygons")
    print(f"width check (< {MIN_WIDTH_UM} um), default 90 deg angle limit: {n_w90} "
          f"(false positives at taper end faces)")
    print(f"width check (< {MIN_WIDTH_UM} um), 80 deg angle limit: {n_w80} violations")
    print(f"space check (< {MIN_SPACE_UM} um): {n_space} violations")
    for name, ld in LAYERS.items():
        print(f"  layer {name:6s} {ld}: {die.shapes(lay[name]).size()} shapes")

    layout.write("output/test_die.gds")
    opts = db.SaveLayoutOptions()
    opts.format = "OASIS"
    layout.write("output/test_die.oas", opts)
    bb = top.bbox()
    print(f"top cell '{top.name}' bbox: {bb.width() * DBU_UM / 1000:.2f} x "
          f"{bb.height() * DBU_UM / 1000:.2f} mm")
    print("wrote output/test_die.gds and output/test_die.oas")
