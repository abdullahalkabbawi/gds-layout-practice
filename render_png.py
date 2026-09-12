"""Render a GDS or OASIS file to PNG without opening the KLayout GUI, using the
klayout.lay module's headless LayoutView.

Usage: python render_png.py output/test_die.gds output/test_die.png [width] [height]
"""
import sys
import klayout.lay as lay


def render(src, dst, width=1800, height=1350):
    view = lay.LayoutView()
    view.load_layout(src, True)
    view.max_hier()                     # show every hierarchy level
    view.set_config("background-color", "#ffffff")
    view.set_config("grid-visible", "false")
    view.zoom_fit()
    view.save_image(dst, width, height)
    print(f"rendered {src} -> {dst} ({width}x{height})")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "output/test_die.gds"
    dst = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".png"
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1800
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 1350
    render(src, dst, w, h)
