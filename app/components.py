"""Các thành phần trình bày nhỏ dùng chung cho các màn hình."""

from html import escape
from functools import lru_cache
import streamlit as st


def number(value):
    return f"{int(value):,}".replace(",", ".")


def heading(kicker, title, description):
    st.markdown(
        f'<div class="page-heading"><div class="eyebrow">{escape(kicker)}</div>'
        f"<h1>{escape(title)}</h1><p>{escape(description)}</p></div>",
        unsafe_allow_html=True,
    )


def section(number_text, title, description=""):
    st.markdown(
        f'<div class="section-heading"><span>{escape(number_text)}</span>'
        f"<div><h3>{escape(title)}</h3><p>{escape(description)}</p></div></div>",
        unsafe_allow_html=True,
    )


def stat(label, value, detail, accent=False, icon=None):
    variant = " stat-accent" if accent else ""
    icon_html = f'<span class="stat-icon" aria-hidden="true"><span class="stat-material">{escape(icon)}</span></span>' if icon else ""
    st.markdown(
        f'<div class="stat-card{variant}">{icon_html}<div class="stat-label">{escape(label)}</div>'
        f'<div class="stat-value">{escape(str(value))}</div><div class="stat-detail">{escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )


def note(title, text, kind="plain"):
    st.markdown(
        f'<div class="note note-{kind}"><strong>{escape(title)}</strong>'
        f"<p>{escape(text)}</p></div>",
        unsafe_allow_html=True,
    )


def csv_download(label, frame, filename, key=None):
    # BOM giúp Excel trên Windows đọc đúng tên cột tiếng Việt.
    st.download_button(
        label,
        frame.to_csv(index=False).encode("utf-8-sig"),
        filename,
        "text/csv",
        key=key,
        icon=":material/download:",
    )


@lru_cache(maxsize=2)
def _encoded_logo(path, modified):
    import base64
    from pathlib import Path
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def logo_image(animated=False):
    """Embed the bundled logo so Streamlit works from any current directory."""
    from pathlib import Path
    path = Path(__file__).resolve().parent / "assets" / "vincent-d-logo-avatar.png"
    data = _encoded_logo(str(path), path.stat().st_mtime_ns)
    arcs = ""
    if animated:
        import random
        # Fixed irregular geometry; no timer, JavaScript or per-frame path generation.
        def lightning(seed):
            rng = random.Random(seed)
            points = []
            y = 6.0
            for i in range(49):
                x = 9 + i * 1.7
                y = max(2.0, min(10.0, y + rng.uniform(-2.3, 2.3)))
                points.append((x, y))
            main = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in points)
            branches = []
            for idx in (5, 11, 18, 25, 32, 39, 44):
                x, y = points[idx]
                coords = [(x, y)]
                direction = -1 if idx % 2 else 1
                for step in range(rng.randint(4, 7)):
                    x += rng.uniform(-2.0, 2.4)
                    y += direction * rng.uniform(.8, 1.8)
                    coords.append((x, y))
                branch = "M" + " L".join(f"{px:.2f} {py:.2f}" for px, py in coords)
                tip_x, tip_y = coords[-2]
                branch += f" M{tip_x:.2f} {tip_y:.2f} l{rng.uniform(2,5):.2f} {direction*3:.2f} l2 {direction*2}"
                branches.append(branch)
            return main, " ".join(branches)
        layers = []
        for index, side in enumerate(("top", "right", "bottom", "left")):
            main, branches = lightning(381 + index * 19)
            layers.append(f'<g transform="rotate({index * 90} 50 50)">'
                          f'<g class="electric-bolt bolt-{side}">'
                          f'<path class="bolt-aura" d="{main}" />'
                          f'<path class="bolt-halo" d="{main}" />'
                          f'<path class="bolt-color" d="{main}" />'
                          f'<path class="bolt-core" d="{main}" />'
                          f'<path class="bolt-branches" d="{branches}" />'
                          f'<path class="bolt-branch-core" d="{branches}" />'
                          '</g></g>')
        arcs = ('<svg class="avatar-electricity" viewBox="-10 -10 120 120" '
                'aria-hidden="true" focusable="false" fill="none">'
                + ''.join(layers) + '</svg>')
    return (f'<img class="identity-logo" src="data:image/png;base64,{data}" '
            f'alt="Logo Vincent D" width="76" height="76">' + (arcs if animated else ''))


def brand_wordmark():
    """Static, selectable brand name; electricity belongs to the logo only."""
    return '<span class="brand-wordmark"><span class="brand-wordmark-text">Vincent D</span></span>'
