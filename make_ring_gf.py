"""The same idea as make_test_die.py, but in gdsfactory: parametric cells from a
process design kit (here the built-in generic PDK) placed and connected by port,
instead of polygons drawn by hand.

First gdsfactory script, September 2026. Builds a ring resonator gap sweep and a
waveguide width sweep, labels each device, and writes GDSII.
"""
import os

import gdsfactory as gf

# gdsfactory 9 needs a process design kit activated before any component is built.
# The generic PDK ships with gdsfactory; a fab would supply its own.
try:
    from gdsfactory.gpdk import PDK as _PDK
except ImportError:  # older layout of the package
    from gdsfactory.generic_tech import get_generic_pdk
    _PDK = get_generic_pdk()
_PDK.activate()

RING_GAPS_UM = [0.20, 0.30, 0.40]
RING_RADIUS_UM = 10.0
WG_WIDTHS_UM = [0.4, 0.5, 0.6, 0.8]
TEXT_LAYER = (66, 0)       # generic PDK text layer


@gf.cell
def sivers_prep_chip() -> gf.Component:
    c = gf.Component()

    # Row 1: ring resonators with a coupling gap sweep. ring_single is a parametric
    # cell from the PDK: change gap or radius and the whole device regenerates.
    x = 0.0
    for gap in RING_GAPS_UM:
        ring = c << gf.components.ring_single(gap=gap, radius=RING_RADIUS_UM,
                                              length_x=4.0, length_y=0.6)
        ring.move((x, 0.0))
        lbl = c << gf.components.text(f"gap {gap:.2f}", size=3.0, layer=TEXT_LAYER)
        lbl.move((x, -12.0))
        x += 60.0

    # Row 2: straight waveguides with a width sweep, each with tapers to a common
    # 0.5 um port width so they can be connected to the same test structure.
    y = 40.0
    for w in WG_WIDTHS_UM:
        xs = gf.cross_section.strip(width=w)
        t_in = c << gf.components.taper(length=10.0, width1=0.5, width2=w)
        wg = c << gf.components.straight(length=80.0, cross_section=xs)
        t_out = c << gf.components.taper(length=10.0, width1=w, width2=0.5)
        t_in.move((0.0, y))
        wg.connect("o1", t_in.ports["o2"])       # connect by port, not by coordinate
        t_out.connect("o1", wg.ports["o2"])
        lbl = c << gf.components.text(f"w {w:.1f}", size=3.0, layer=TEXT_LAYER)
        lbl.move((110.0, y - 1.5))
        y += 12.0

    title = c << gf.components.text("SIVERS PREP GF", size=6.0, layer=TEXT_LAYER)
    title.move((0.0, y + 5.0))
    return c


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    chip = sivers_prep_chip()
    path = chip.write_gds("output/ring_gf.gds")
    print(f"gdsfactory {gf.__version__}, active PDK: {gf.get_active_pdk().name}")
    print(f"top cell '{chip.name}', bbox {chip.dxsize:.1f} x {chip.dysize:.1f} um")
    print(f"wrote {path}")
