#!/usr/bin/env python
"""Render rotating 3D GIFs of the scFv-HER2 domain IV complexes for slides.

Headless by construction: a C-alpha trace drawn with matplotlib's 3D axes and
assembled into a GIF with Pillow. No PyMOL, ChimeraX or browser needed, so this
runs on a GPU box over SSH exactly as it runs on a laptop.

What each frame shows:

* **HER2 domain IV** as a muted tube - it is context, not the subject.
* **The scFv binder** in the primary series hue, so the eye lands on the design.
* **Mutated positions** as larger markers, which is the actual point of the
  figure: where this design differs from trastuzumab.
* **Modelled interface contacts** as thin connectors, so the binding face is
  visible while the model turns.

Colour follows the same validated palette as the static figures, and the two
chains are additionally separated by line weight and marker size, so the figure
does not rely on hue alone.

Run:
    python make_3d_gifs.py --set top_15_scored --limit 5
    python make_3d_gifs.py --cif outputs/binders/HER2_1238/complex.cif --out demo.gif
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import her2_common as hc
from stage5_score_ipsae import parse_cif_atoms, TARGET_CHAIN, BINDER_CHAIN

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
BINDER_COLOR = "#2a78d6"     # categorical slot 1
TARGET_COLOR = "#9a9890"     # muted: context, not subject
MUT_COLOR = "#eb6834"        # categorical slot 2
CONTACT_COLOR = "#1baf7a"    # categorical slot 3


def ca_trace(cif: Path) -> dict[str, tuple[list[int], np.ndarray]]:
    """Approximate a C-alpha trace per chain as each residue's centroid.

    parse_cif_atoms keeps all heavy atoms; the per-residue centroid tracks the
    backbone closely enough for a schematic at this scale and avoids a second
    parser just to pick out CA records.
    """
    atoms = parse_cif_atoms(cif)
    out = {}
    for ch, residues in atoms.items():
        ids = sorted(residues)
        if not ids:
            continue
        pts = np.array([residues[i].mean(axis=0) for i in ids])
        out[ch] = (ids, pts)
    return out


def contact_pairs(trace: dict, cutoff: float = 8.0, max_pairs: int = 60):
    """Residue-centroid pairs across the interface, for the connector lines."""
    if TARGET_CHAIN not in trace or BINDER_CHAIN not in trace:
        return []
    t_ids, t_pts = trace[TARGET_CHAIN]
    b_ids, b_pts = trace[BINDER_CHAIN]
    d = np.linalg.norm(t_pts[None, :, :] - b_pts[:, None, :], axis=2)
    pairs = []
    bi, ti = np.where(d <= cutoff)
    for b, t in zip(bi, ti):
        pairs.append((float(d[b, t]), b_pts[b], t_pts[t]))
    pairs.sort(key=lambda p: p[0])
    return pairs[:max_pairs]


def render_gif(cif: Path, out_gif: Path, *, title: str = "", subtitle: str = "",
               mutations: list[int] | None = None, frames: int = 36,
               size: tuple[int, int] = (720, 720), elev: float = 14.0,
               duration_ms: int = 90) -> bool:
    trace = ca_trace(cif)
    if BINDER_CHAIN not in trace:
        print(f"  [skip] {cif.name}: no binder chain {BINDER_CHAIN}")
        return False

    b_ids, b_pts = trace[BINDER_CHAIN]
    t_ids, t_pts = trace.get(TARGET_CHAIN, ([], np.empty((0, 3))))
    allpts = np.vstack([p for p in (b_pts, t_pts) if len(p)])
    center = allpts.mean(axis=0)
    radius = float(np.abs(allpts - center).max()) * 0.74

    mut_idx = []
    if mutations:
        pos_to_row = {p: i for i, p in enumerate(b_ids)}
        mut_idx = [pos_to_row[p] for p in mutations if p in pos_to_row]
    pairs = contact_pairs(trace)

    images: list[Image.Image] = []
    dpi = 100
    for k in range(frames):
        azim = 360.0 * k / frames
        fig = plt.figure(figsize=(size[0] / dpi, size[1] / dpi), dpi=dpi)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor(SURFACE)
        fig.patch.set_facecolor(SURFACE)

        if len(t_pts):
            ax.plot(t_pts[:, 0], t_pts[:, 1], t_pts[:, 2],
                    color=TARGET_COLOR, linewidth=2.2, alpha=0.85, zorder=1)
        for dist, bp, tp in pairs:
            ax.plot([bp[0], tp[0]], [bp[1], tp[1]], [bp[2], tp[2]],
                    color=CONTACT_COLOR, linewidth=0.7, alpha=0.5, zorder=2)
        ax.plot(b_pts[:, 0], b_pts[:, 1], b_pts[:, 2],
                color=BINDER_COLOR, linewidth=3.0, zorder=3)
        if mut_idx:
            mp = b_pts[mut_idx]
            ax.scatter(mp[:, 0], mp[:, 1], mp[:, 2], s=185, color=MUT_COLOR,
                       edgecolor="white", linewidth=1.6, depthshade=False, zorder=10)

        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        fig.subplots_adjust(left=-0.06, right=1.06, bottom=-0.06, top=1.02)
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:                                        # noqa: BLE001
            pass

        if title:
            fig.text(0.03, 0.965, title, color=INK, fontsize=15, fontweight="bold", va="top")
        if subtitle:
            fig.text(0.03, 0.915, subtitle, color=INK_2, fontsize=10, va="top")
        # Legend as text so identity never depends on hue alone.
        fig.text(0.03, 0.055, "scFv binder", color=BINDER_COLOR, fontsize=10, fontweight="bold")
        fig.text(0.03, 0.025, "HER2 domain IV", color=TARGET_COLOR, fontsize=10, fontweight="bold")
        if mut_idx:
            fig.text(0.62, 0.055, f"{len(mut_idx)} substitutions",
                     color=MUT_COLOR, fontsize=10, fontweight="bold")
        if pairs:
            fig.text(0.62, 0.025, "interface contacts",
                     color=CONTACT_COLOR, fontsize=10, fontweight="bold")

        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
        images.append(Image.fromarray(buf))
        plt.close(fig)

    out_gif.parent.mkdir(parents=True, exist_ok=True)
    # Quantise to a shared adaptive palette so the GIF stays small and stable.
    frames_p = [im.convert("P", palette=Image.ADAPTIVE, colors=128) for im in images]
    frames_p[0].save(out_gif, save_all=True, append_images=frames_p[1:],
                     duration=duration_ms, loop=0, optimize=True, disposal=2)
    print(f"  wrote {out_gif.name}  ({out_gif.stat().st_size/1024:.0f} KB, {frames} frames)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--set", default="top_15_scored")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--size", type=int, default=720)
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--cif", type=Path, default=None, help="render one file and exit")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--parent", action="store_true",
                    help="also render the parent complex for side-by-side comparison")
    args = ap.parse_args()
    outdir = args.outdir or (args.results / "gifs")

    if args.cif:
        ok = render_gif(args.cif, args.out or (outdir / (args.cif.stem + ".gif")),
                        title=args.cif.stem, frames=args.frames,
                        size=(args.size, args.size))
        return 0 if ok else 1

    designs = []
    p = args.results / f"{args.set}.csv"
    if p.is_file():
        with open(p) as fh:
            designs = list(csv.DictReader(fh))[: args.limit]
    if not designs:
        raise SystemExit(f"no designs in {p}")

    made = 0
    for d in designs:
        cid = d["candidate_id"]
        folder = args.results / "binders" / cid
        cif = folder / "complex.cif"
        if not cif.is_file():
            print(f"  [skip] {cid}: no complex.cif (run export_binder_info.py first)")
            continue
        info = {}
        ij = folder / "design.json"
        if ij.is_file():
            info = json.loads(ij.read_text())
        muts = [int(m[1:-1]) for m in info.get("design", {}).get("mutations", [])] or \
               [int(m[1:-1]) for m in (d.get("mutations_1based") or "").split(";") if m]
        ipsae = d.get("ipsae_min", "")
        sd = d.get("ipsae_min_sd", "")
        sub = (f"{len(muts)} substitutions   ipSAE {ipsae}"
               + (f" +/- {sd}" if sd else "")
               + f"   {d.get('branch','')}")
        if render_gif(cif, outdir / f"{cid}.gif", title=cid, subtitle=sub,
                      mutations=muts, frames=args.frames, size=(args.size, args.size)):
            made += 1

    if args.parent:
        raw_p = args.results / "boltz_results_raw.csv"
        if raw_p.is_file():
            with open(raw_p) as fh:
                rows = [r for r in csv.DictReader(fh)
                        if r.get("candidate_id") == "parent"
                        and r.get("ipsae_status") == "PASSED"]
            if rows:
                cif = Path(rows[0]["structure_path"])
                if cif.is_file():
                    render_gif(cif, outdir / "parent.gif",
                               title="Parent (trastuzumab scFv)",
                               subtitle="unmodified reference, 0 substitutions",
                               frames=args.frames, size=(args.size, args.size))
                    made += 1

    print(f"[gifs] {made} animations -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
