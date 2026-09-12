"""Mask layout of the terahertz coplanar waveguide (CPW) cavities from my MSc
dissertation, "Development of Terahertz Cavities for Quantum Engineering and 6G
Communications" (University of Glasgow, 2026), rebuilt in KLayout's Python API.

The dissertation simulated these structures in Ansys Lumerical FDTD. This script draws
the same geometry the way a fab would need it: the metal, the etched gap derived from
the metal by a Boolean, the trench openings as their own layer, alignment marks and
labels. It then runs design-rule checks and writes GDSII, OASIS and DXF.

Dimensions are the dissertation's own (Tables 3.1, 3.3, 3.5 and 3.6):
  signal width s = 10 um, slot width w = 5 um, cavity length l = 120 um,
  coupling gaps 7, 10, 15, 20, 30, 40 and 50 um,
  trench width wt = 5 um at edge offset wedge = 5 um (depth dt = 50 um is a process
  parameter, not a layout one),
  interdigitated capacitor (IDC) region L_IDC = 12 um with Nf = 2, 4, 6, 8, 10 fingers
  and p = S / (2 Nf - 1) for finger width, spacing and tip clearance.

Units: database unit 1 nm, helpers take microns.
"""
import os
import klayout.db as db

# ---------------------------------------------------------------- settings ---
DBU_UM = 0.001

S_UM = 10.0            # signal (centre conductor) width
W_UM = 5.0             # CPW slot width
L_CAV_UM = 120.0       # cavity length between coupling gaps
FEED_UM = 200.0        # feed line length each side
GROUND_UM = 60.0       # ground plane width drawn each side of the slot
GAPS_UM = [7.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0]   # coupling gap sweep
WEDGE_UM = 5.0         # trench edge offset from the outer slot edge
WT_UM = 5.0            # trench width
L_IDC_UM = 12.0        # IDC coupling region length
IDC_FINGERS = [2, 4, 6, 8, 10]                        # Nf family from Table 3.4
ROW_PITCH_UM = 180.0
MIN_FEATURE_UM = 1.0   # an i-line contact lithography style rule for the DRC below

LAYERS = {
    "METAL":  (1, 0),   # top metal as drawn (positive)
    "GAP":    (2, 0),   # etched gap, derived from METAL by a Boolean (negative)
    "TRENCH": (3, 0),   # substrate trench openings
    "ALIGN":  (10, 0),
    "TEXT":   (20, 0),
    "FRAME":  (99, 0),
}


def um(x):
    return int(round(x / DBU_UM))


def rect(x0, y0, x1, y1):
    return db.Box(um(x0), um(y0), um(x1), um(y1))


def label(text, x, y, height_um=12.0):
    gen = db.TextGenerator.default_generator()
    reg = gen.text(text, DBU_UM, height_um / (gen.height() * gen.dbu()))
    reg.move(um(x), um(y))
    return reg


# ---------------------------------------------------------------- devices ---
def cpw_ground(cell, lay, x0, x1, y0):
    """Ground planes on both sides of the slot, from x0 to x1, centred on y0."""
    inner = S_UM / 2 + W_UM
    outer = inner + GROUND_UM
    cell.shapes(lay["METAL"]).insert(rect(x0, y0 + inner, x1, y0 + outer))
    cell.shapes(lay["METAL"]).insert(rect(x0, y0 - outer, x1, y0 - inner))
    return -outer, outer


def gap_cavity(layout, lay, gap, trenched=False):
    """Gap-capacitor cavity: feed | gap | cavity | gap | feed, with ground planes
    and, optionally, the two trench openings outside the slots."""
    name = f"{'TRENCH' if trenched else 'GAPCAP'}_G{gap:g}UM"
    cell = layout.create_cell(name)
    total = 2 * FEED_UM + 2 * gap + L_CAV_UM
    x0 = -total / 2
    xa = x0 + FEED_UM                 # left feed end
    xb = xa + gap                     # cavity start
    xc = xb + L_CAV_UM                # cavity end
    xd = xc + gap                     # right feed start
    half = S_UM / 2
    for a, b in [(x0, xa), (xb, xc), (xd, x0 + total)]:
        cell.shapes(lay["METAL"]).insert(rect(a, -half, b, half))
    cpw_ground(cell, lay, x0, x0 + total, 0.0)
    if trenched:
        t0 = S_UM / 2 + W_UM + WEDGE_UM
        cell.shapes(lay["TRENCH"]).insert(rect(x0, t0, x0 + total, t0 + WT_UM))
        cell.shapes(lay["TRENCH"]).insert(rect(x0, -t0 - WT_UM, x0 + total, -t0))
    return cell, total


def idc_cavity(layout, lay, n_fingers):
    """Cavity coupled through interdigitated capacitors. Nf fingers and Nf - 1 gaps
    close the signal width exactly, so p = S / (2 Nf - 1) is finger width, spacing
    and tip clearance at once. Finger length is L_IDC - p."""
    p = S_UM / (2 * n_fingers - 1)
    lf = L_IDC_UM - p
    cell = layout.create_cell(f"IDC_N{n_fingers}")
    total = 2 * FEED_UM + 2 * L_IDC_UM + L_CAV_UM
    x0 = -total / 2
    half = S_UM / 2
    xa = x0 + FEED_UM                 # left feed end, left IDC starts
    xb = xa + L_IDC_UM                # cavity start
    xc = xb + L_CAV_UM                # cavity end, right IDC starts
    xd = xc + L_IDC_UM                # right feed start
    for a, b in [(x0, xa), (xb, xc), (xd, x0 + total)]:
        cell.shapes(lay["METAL"]).insert(rect(a, -half, b, half))

    def fingers(x_left, x_right):
        """Interleaved combs between a strip ending at x_left and one starting at
        x_right. Even-index fingers belong to the left strip, odd to the right."""
        for k in range(n_fingers):
            y0 = -half + k * 2 * p
            y1 = y0 + p
            if k % 2 == 0:
                cell.shapes(lay["METAL"]).insert(rect(x_left, y0, x_left + lf, y1))
            else:
                cell.shapes(lay["METAL"]).insert(rect(x_right - lf, y0, x_right, y1))

    fingers(xa, xb)
    fingers(xc, xd)
    cpw_ground(cell, lay, x0, x0 + total, 0.0)
    return cell, total, p


# -------------------------------------------------------------- derivation ---
def derive_gap_layer(layout, lay, cell, total):
    """The etched gap is everything inside the CPW window that is not metal. This
    is how a negative (etch) mask is produced from a positive metal drawing."""
    outer = S_UM / 2 + W_UM + GROUND_UM
    window = db.Region(rect(-total / 2, -outer, total / 2, outer))
    metal = db.Region(cell.begin_shapes_rec(lay["METAL"]))
    gap = window - metal
    cell.shapes(lay["GAP"]).insert(gap)
    return gap


def check_min_feature(cell, lay, layer_name):
    reg = db.Region(cell.begin_shapes_rec(lay[layer_name]))
    reg.merge()
    viol = reg.width_check(um(MIN_FEATURE_UM), False, db.Region.Euclidian, 80.0)
    return len(viol)


# -------------------------------------------------------------------- top ---
def build(layout):
    lay = {n: layout.layer(*ld) for n, ld in LAYERS.items()}
    top = layout.create_cell("THZ_CPW_CHIP")
    report = []

    # Row 1: plain gap-capacitor sweep. Row 2: the trenched matched pair.
    x_col = 0.0
    for trenched in (False, True):
        y = 0.0 if not trenched else -ROW_PITCH_UM * (len(GAPS_UM) + 0.5)
        for gap in GAPS_UM:
            cell, total = gap_cavity(layout, lay, gap, trenched)
            derive_gap_layer(layout, lay, cell, total)
            top.insert(db.CellInstArray(cell.cell_index(), db.Trans(db.Vector(um(x_col), um(y)))))
            tag = "trenched" if trenched else "plain"
            top.shapes(lay["TEXT"]).insert(label(f"{tag} gap {gap:g}um", -total / 2, y + 95))
            report.append((cell.name, check_min_feature(cell, lay, "METAL"),
                           check_min_feature(cell, lay, "GAP"), None))
            y -= ROW_PITCH_UM

    # Row 3: IDC family, to the right of the sweeps.
    x_col = 900.0
    y = 0.0
    for nf in IDC_FINGERS:
        cell, total, p = idc_cavity(layout, lay, nf)
        derive_gap_layer(layout, lay, cell, total)
        top.insert(db.CellInstArray(cell.cell_index(), db.Trans(db.Vector(um(x_col), um(y)))))
        top.shapes(lay["TEXT"]).insert(label(f"IDC Nf={nf} p={p:.3f}um", x_col - total / 2, y + 95))
        report.append((cell.name, check_min_feature(cell, lay, "METAL"),
                       check_min_feature(cell, lay, "GAP"), p))
        y -= ROW_PITCH_UM

    # Frame, alignment marks and title
    bb = top.bbox()
    m = um(150.0)
    frame = db.Box(bb.left - m, bb.bottom - m, bb.right + m, bb.top + m)
    top.shapes(lay["FRAME"]).insert(frame)
    for cx, cy in [(frame.left, frame.bottom), (frame.right, frame.bottom),
                   (frame.left, frame.top), (frame.right, frame.top)]:
        sx = 1 if cx == frame.left else -1
        sy = 1 if cy == frame.bottom else -1
        cx2, cy2 = cx + sx * um(60), cy + sy * um(60)
        top.shapes(lay["ALIGN"]).insert(db.Box(cx2 - um(40), cy2 - um(3), cx2 + um(40), cy2 + um(3)))
        top.shapes(lay["ALIGN"]).insert(db.Box(cx2 - um(3), cy2 - um(40), cx2 + um(3), cy2 + um(40)))
    top.shapes(lay["TEXT"]).insert(label("THZ CPW CAVITIES  s10 w5 l120  ALKABBAWI 2026",
                                         bb.left * DBU_UM, frame.top * DBU_UM - 60, 24))
    return top, lay, report


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    layout = db.Layout()
    layout.dbu = DBU_UM
    top, lay, report = build(layout)

    print(f"{'cell':16s} {'metal<1um':>10s} {'gap<1um':>8s}  note")
    for name, n_metal, n_gap, p in report:
        note = ""
        if p is not None:
            note = f"finger pitch p = {p:.3f} um" + ("  FAILS a 1 um rule, needs e-beam" if p < MIN_FEATURE_UM else "")
        print(f"{name:16s} {n_metal:10d} {n_gap:8d}  {note}")

    layout.write("output/thz_cpw_chip.gds")
    for fmt, ext in [("OASIS", "oas"), ("DXF", "dxf")]:
        opts = db.SaveLayoutOptions()
        opts.format = fmt
        layout.write(f"output/thz_cpw_chip.{ext}", opts)
    bb = top.bbox()
    print(f"top cell '{top.name}': {layout.cells()} cells, "
          f"{bb.width() * DBU_UM / 1000:.2f} x {bb.height() * DBU_UM / 1000:.2f} mm")
    print("wrote output/thz_cpw_chip.gds, .oas and .dxf")
