"""The gap-capacitor CPW cavities from my MSc dissertation, built in gdsfactory.

Where make_thz_cpw_cavity.py draws rectangles, this version defines a coplanar
waveguide as a cross-section (signal on the metal layer, two slots on the gap layer)
and builds each cavity from parametric cells joined by electrical ports:
feed | coupling gap | cavity | coupling gap | feed. Change a number at the top and
every device regenerates. gdsfactory's own meandered resonator_cpw is placed
alongside for comparison.

Dimensions from the dissertation: s = 10 um, w = 5 um, l = 120 um, gaps 7 to 50 um.
"""
import os

import gdsfactory as gf

try:
    from gdsfactory.gpdk import PDK as _PDK
except ImportError:
    from gdsfactory.generic_tech import get_generic_pdk
    _PDK = get_generic_pdk()
_PDK.activate()

LAYER_METAL = (1, 0)
LAYER_GAP = (2, 0)
LAYER_TEXT = (20, 0)

S_UM, W_UM, L_CAV_UM, FEED_UM = 10.0, 5.0, 120.0, 200.0
GAPS_UM = [7.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0]
ROW_PITCH_UM = 60.0


def cpw_cross_section(s: float = S_UM, w: float = W_UM) -> gf.CrossSection:
    """Signal strip on METAL plus two slots on GAP, with electrical ports."""
    return gf.cross_section.cross_section(
        width=s,
        layer=LAYER_METAL,
        sections=(
            gf.Section(width=w, offset=+(s / 2 + w / 2), layer=LAYER_GAP, name="slot_top"),
            gf.Section(width=w, offset=-(s / 2 + w / 2), layer=LAYER_GAP, name="slot_bot"),
        ),
        port_names=("e1", "e2"),
        port_types=("electrical", "electrical"),
    )


@gf.cell
def coupling_gap(gap: float, s: float = S_UM, w: float = W_UM) -> gf.Component:
    """A series break in the signal strip: the etched region spans the strip and both
    slots. Ports sit on the strip axis so the cell connects to the CPW straights."""
    c = gf.Component()
    h = s / 2 + w
    c.add_polygon([(0, -h), (gap, -h), (gap, h), (0, h)], layer=LAYER_GAP)
    c.add_port("e1", center=(0, 0), width=s, orientation=180, layer=LAYER_METAL,
               port_type="electrical")
    c.add_port("e2", center=(gap, 0), width=s, orientation=0, layer=LAYER_METAL,
               port_type="electrical")
    return c


@gf.cell
def gap_cavity(gap: float) -> gf.Component:
    """feed | gap | cavity | gap | feed, connected by port rather than by coordinate."""
    c = gf.Component()
    xs = cpw_cross_section()
    feed_l = c << gf.components.straight(length=FEED_UM, cross_section=xs)
    g1 = c << coupling_gap(gap=gap)
    cav = c << gf.components.straight(length=L_CAV_UM, cross_section=xs)
    g2 = c << coupling_gap(gap=gap)
    feed_r = c << gf.components.straight(length=FEED_UM, cross_section=xs)
    g1.connect("e1", feed_l.ports["e2"])
    cav.connect("e1", g1.ports["e2"])
    g2.connect("e1", cav.ports["e2"])
    feed_r.connect("e1", g2.ports["e2"])
    c.add_port("e1", port=feed_l.ports["e1"])
    c.add_port("e2", port=feed_r.ports["e2"])
    return c


@gf.cell
def thz_cpw_chip() -> gf.Component:
    c = gf.Component()
    y = 0.0
    for gap in GAPS_UM:
        dev = c << gap_cavity(gap=gap)
        dev.move((0.0, y))
        lbl = c << gf.components.text(f"gap {gap:g} um", size=8.0, layer=LAYER_TEXT)
        lbl.move((-FEED_UM - 120.0, y - 4.0))
        y -= ROW_PITCH_UM

    # gdsfactory's own CPW resonator PCell (a meandered quarter-wave style resonator
    # as used for superconducting circuits), for comparison with the straight THz cavity.
    ref = c << gf.components.resonator_cpw(length=1000.0, width=S_UM, gap=W_UM,
                                           coupling_gap=7.0, coupling_length=100.0,
                                           layer_metal=LAYER_METAL, layer_gap=LAYER_GAP)
    ref.move((450.0, y - 150.0))
    lbl = c << gf.components.text("gdsfactory resonator_cpw, for comparison", size=8.0,
                                  layer=LAYER_TEXT)
    lbl.move((450.0, y - 170.0))

    title = c << gf.components.text("THZ CPW GAP-CAPACITOR CAVITIES (gdsfactory)", size=12.0,
                                    layer=LAYER_TEXT)
    title.move((-FEED_UM - 120.0, 40.0))
    return c


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    chip = thz_cpw_chip()
    path = chip.write_gds("output/thz_cpw_gf.gds")
    print(f"gdsfactory {gf.__version__}: top cell '{chip.name}', "
          f"bbox {chip.dxsize:.1f} x {chip.dysize:.1f} um, wrote {path}")
