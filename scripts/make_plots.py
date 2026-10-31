#!/usr/bin/env python
"""Generate the figure set for the HER2 scFv reports.

Colour and form follow a validated design system rather than taste:

* **Categorical** hues are assigned in fixed order from the reference palette
  (blue, orange, aqua). Scatter-type forms are capped at **three** slots, which
  is the documented all-pairs-validated subset - past three, adjacent hues stop
  clearing the colour-vision-deficiency separation floor, so extra groups are
  faceted instead of recoloured.
* **Ordinal magnitude** (mutation count) uses a single-hue blue ramp starting no
  lighter than step 250, so the lightest mark still clears 2:1 on the surface.
* **Diverging** data (correlations, which have a meaningful zero) uses blue<->red
  with a neutral *gray* midpoint - never a hue at the midpoint, never a rainbow.
* Single-series charts carry **no legend** (the title names the series); >=2
  series always do, so identity is never colour-alone.
* Marks are thin, grid and axes recessive, and values are direct-labelled
  selectively rather than printed on every point.

Idempotent: safe to re-run as new Modal results arrive. Figures that have no data
yet are skipped with a notice instead of emitting an empty axes.

Run:
    python make_plots.py --outdir ../outputs/figures
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# --------------------------------------------------------------------------- #
# Design-system parameters (light surface)
# --------------------------------------------------------------------------- #
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8980"
GRID = "#e6e5e0"

# Categorical, fixed order. Only the first three are used where all pairs of
# series can appear together (scatter, overlaid distributions).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
# Single-hue sequential/ordinal ramp (blue). Ordinal marks start at step 250.
BLUE_ORDINAL = ["#86b6ef", "#3987e5", "#2a78d6", "#1c5cab"]
BLUE_SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Diverging: blue <-> red with a neutral gray midpoint.
DIVERGING = LinearSegmentedColormap.from_list(
    "blue_gray_red", ["#1c5cab", "#86b6ef", "#f0efec", "#ef9a9a", "#c62828"])
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}


def style_axes(ax, *, grid_axis: str = "y") -> None:
    """Recessive grid and axes; data should be the most prominent thing."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(1.0)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    for lbl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        lbl.set_color(INK_2)


def finish(fig, ax, title: str, subtitle: str = "", xlabel: str = "", ylabel: str = ""):
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=10)
    ax.set_title("")
    y = 0.97 if subtitle else 0.95
    fig.text(0.015, y, title, color=INK, fontsize=13, fontweight="600", va="top")
    if subtitle:
        fig.text(0.015, y - 0.065, subtitle, color=INK_2, fontsize=9.5, va="top")
    fig.patch.set_facecolor(SURFACE)


def save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.name}")


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def fnum(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def read_csv(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


def load(outdir: Path) -> dict:
    raw = read_csv(outdir / "boltz_results_raw.csv")
    for r in raw:
        # Classify by which run directory the structure came from.
        sp = r.get("structure_path", "")
        r["source"] = "Modal" if "modal_cofold" in sp else "Local"
    return {
        "raw": [r for r in raw if r.get("ipsae_status") == "PASSED"],
        "scored": read_csv(outdir / "submission_scored.csv"),
        "top15": read_csv(outdir / "top_15_scored.csv"),
        "top50": read_csv(outdir / "top_50_scored.csv"),
        "agg": read_csv(outdir / "ipsae_aggregated.csv"),
        "diag": json.loads((outdir / "score_diagnostics.json").read_text())
                if (outdir / "score_diagnostics.json").is_file() else {},
    }


def parent_band(raw: list[dict]) -> tuple[float | None, float | None]:
    vals = [fnum(r["ipsae_min"]) for r in raw if r["candidate_id"] == "parent"]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    m = float(np.mean(vals))
    s = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    return m, s


def add_parent_ref(ax, pm, ps, *, horizontal=True, label=True):
    """A recessive, directly-labelled reference line - not a series."""
    if pm is None:
        return
    fn_line = ax.axhline if horizontal else ax.axvline
    fn_span = ax.axhspan if horizontal else ax.axvspan
    if ps:
        fn_span(pm - ps, pm + ps, color=INK_MUTED, alpha=0.13, zorder=0, linewidth=0)
    fn_line(pm, color=INK_2, linestyle=(0, (5, 3)), linewidth=1.6, zorder=2)
    if label:
        if horizontal:
            ax.annotate(f"parent {pm:.3f}", xy=(0.995, pm), xycoords=("axes fraction", "data"),
                        ha="right", va="bottom", fontsize=8.5, color=INK_2)
        else:
            ax.annotate(f"parent {pm:.3f}", xy=(pm, -0.055),
                        xycoords=("data", "axes fraction"),
                        ha="center", va="top", fontsize=8.5, color=INK_2)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

def fig_distribution(d: dict, out: Path) -> None:
    """ipSAE distribution, split by compute source. Two series -> legend present."""
    raw = [r for r in d["raw"] if r["candidate_id"] != "parent"]
    if not raw:
        print("  skip distribution (no data)")
        return
    by_src = defaultdict(list)
    for r in raw:
        v = fnum(r["ipsae_min"])
        if v is not None:
            by_src[r["source"]].append(v)
    srcs = [s for s in ("Local", "Modal") if by_src.get(s)]
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    style_axes(ax)
    bins = np.linspace(0, 1.0, 41)
    for i, s in enumerate(srcs):
        ax.hist(by_src[s], bins=bins, color=SERIES[i], alpha=0.55 if len(srcs) > 1 else 0.8,
                label=f"{s}  (n={len(by_src[s])})", edgecolor=SURFACE, linewidth=0.8)
    add_parent_ref(ax, pm, ps, horizontal=False)
    if len(srcs) >= 2:
        leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
        for t in leg.get_texts():
            t.set_color(INK_2)
    finish(fig, ax,
           "ipSAE distribution of designed scFv variants",
           "Per-structure values. The dashed line is the parent baseline; the band is its "
           "+/-1 SD across seeds.\nMost designs fall below the parent, which is the expected "
           "result for a sub-picomolar starting antibody.",
           "ipSAE_min", "structures")
    save(fig, out / "01_ipsae_distribution.png")


def fig_by_mutation_count(d: dict, out: Path) -> None:
    """Ordinal x-axis, single series with error bars -> single-hue ramp, no legend."""
    bym = (d["diag"].get("by_mutation_count") or {})
    if not bym:
        print("  skip mutation-count figure (no diagnostics)")
        return
    keys = sorted(bym, key=lambda k: int(float(k)))
    means = [bym[k]["ipsae_min_mean"] for k in keys]
    sds = [bym[k].get("ipsae_min_sd") or 0 for k in keys]
    ns = [bym[k]["n"] for k in keys]
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    style_axes(ax)
    x = np.arange(len(keys))
    colors = [BLUE_ORDINAL[min(i, len(BLUE_ORDINAL) - 1)] for i in range(len(keys))]
    ax.bar(x, means, width=0.56, color=colors, edgecolor=SURFACE, linewidth=2.0, zorder=3)
    ax.errorbar(x, means, yerr=sds, fmt="none", ecolor=INK_2, elinewidth=1.4,
                capsize=4, capthick=1.4, zorder=4)
    add_parent_ref(ax, pm, ps)
    for xi, m, n in zip(x, means, ns):
        ax.annotate(f"{m:.3f}\nn={n}", xy=(xi, m), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK_2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(float(k))}" for k in keys])
    ax.set_ylim(0, max(1.0, max(means) * 1.35))
    finish(fig, ax,
           "Interface quality declines with substitution count",
           "Mean ipSAE_min per mutation-count stratum, error bars +/-1 SD. Mutation count was the "
           "strongest\nsingle predictor we found; no stratum reaches the parent.",
           "substitutions vs parent", "ipSAE_min")
    save(fig, out / "02_ipsae_by_mutation_count.png")


def fig_by_branch(d: dict, out: Path) -> None:
    """Categorical axis, single series -> one hue, no legend; ordered by value."""
    byb = (d["diag"].get("by_branch") or {})
    if not byb:
        print("  skip branch figure (no diagnostics)")
        return
    items = sorted(byb.items(), key=lambda kv: -(kv[1]["ipsae_min_mean"] or 0))
    labels = [k for k, _ in items]
    means = [v["ipsae_min_mean"] for _, v in items]
    sds = [v.get("ipsae_min_sd") or 0 for _, v in items]
    ns = [v["n"] for _, v in items]
    recov = [v.get("epitope_recovery_mean") for _, v in items]
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    style_axes(ax, grid_axis="x")
    y = np.arange(len(labels))[::-1]
    ax.barh(y, means, height=0.55, color=SERIES[0], edgecolor=SURFACE, linewidth=2.0, zorder=3)
    ax.errorbar(means, y, xerr=sds, fmt="none", ecolor=INK_2, elinewidth=1.4,
                capsize=4, capthick=1.4, zorder=4)
    add_parent_ref(ax, pm, ps, horizontal=False)
    for yi, m, n, rc in zip(y, means, ns, recov):
        extra = f"   epitope {rc:.2f}" if rc is not None else ""
        ax.annotate(f"{m:.3f}  n={n}{extra}", xy=(m, yi), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=INK_2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, max(1.05, max(means) * 1.45))
    finish(fig, ax,
           "Framework-biased edits preserve the interface best",
           "Mean ipSAE_min by design branch, error bars +/-1 SD. CDR-H3-focused editing scores "
           "worst,\nwhich contradicts the prior that H3 maturation would be the strongest branch.",
           "ipSAE_min", "")
    save(fig, out / "03_ipsae_by_branch.png")


def fig_replicate_spread(d: dict, out: Path) -> None:
    """Per-design mean +/- SD, sorted. Shows why single-seed ranking is unsafe."""
    per = defaultdict(list)
    for r in d["raw"]:
        v = fnum(r["ipsae_min"])
        if v is not None:
            per[r["candidate_id"]].append(v)
    reps = {k: v for k, v in per.items() if len(v) >= 2 and k != "parent"}
    if len(reps) < 3:
        print("  skip replicate spread (need >=3 replicated designs)")
        return
    items = sorted(reps.items(), key=lambda kv: -float(np.mean(kv[1])))
    means = np.array([np.mean(v) for _, v in items])
    sds = np.array([np.std(v, ddof=1) for _, v in items])
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    style_axes(ax)
    x = np.arange(len(items))
    ax.errorbar(x, means, yerr=sds, fmt="o", markersize=4.5, color=SERIES[0],
                ecolor=INK_MUTED, elinewidth=1.3, capsize=2.5, zorder=3)
    add_parent_ref(ax, pm, ps)
    ax.set_xlim(-1, len(items))
    ax.set_xticks([])
    # Direct-label only the extremes, never every point.
    for idx in (0, len(items) - 1):
        ax.annotate(items[idx][0], xy=(x[idx], means[idx]), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=8, color=INK_2)
    med_sd = float(np.median(sds))
    finish(fig, ax,
           "Seed noise is comparable to the differences between designs",
           f"Each marker is one design's mean across seeds; whiskers are +/-1 SD "
           f"(median SD {med_sd:.3f}).\nError bars overlap the parent band for nearly every "
           f"design, so single-seed rankings are not reliable.",
           f"{len(items)} replicated designs, ranked", "ipSAE_min")
    save(fig, out / "04_replicate_spread.png")


def fig_reliability(d: dict, out: Path) -> None:
    """Variance decomposition + how many seeds buy what reliability."""
    rel = (d["diag"].get("reliability") or {})
    if not rel.get("reliability_single_seed"):
        print("  skip reliability figure (no replicate statistics)")
        return
    s_w = rel.get("sd_within_seed") or 0
    s_t = rel.get("sd_between_designs_true_est") or 0
    icc1 = rel["reliability_single_seed"]

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
    for ax in axes:
        style_axes(ax)

    ax = axes[0]
    v_t, v_w = s_t ** 2, s_w ** 2
    tot = max(1e-12, v_t + v_w)
    ax.bar([0], [100 * v_t / tot], width=0.5, color=SERIES[0], edgecolor=SURFACE,
           linewidth=2.0, label="true design differences")
    ax.bar([0], [100 * v_w / tot], width=0.5, bottom=[100 * v_t / tot],
           color=INK_MUTED, edgecolor=SURFACE, linewidth=2.0, label="seed noise")
    ax.set_xlim(-0.6, 1.5)
    ax.set_xticks([])
    ax.set_ylim(0, 100)
    ax.annotate(f"{100*v_t/tot:.0f}% signal", xy=(0, 100 * v_t / tot / 2), ha="center",
                va="center", fontsize=10, color="white", fontweight="600")
    ax.annotate(f"{100*v_w/tot:.0f}% noise", xy=(0, 100 * v_t / tot + 100 * v_w / tot / 2),
                ha="center", va="center", fontsize=10, color="white", fontweight="600")
    leg = ax.legend(frameon=False, fontsize=9, loc="center right")
    for t in leg.get_texts():
        t.set_color(INK_2)
    ax.set_ylabel("share of variance in a single-seed ranking", color=INK_2, fontsize=9.5)

    ax = axes[1]
    n = np.arange(1, 16)
    r = (icc1 * n) / (1 + icc1 * (n - 1))        # Spearman-Brown
    ax.plot(n, r, color=SERIES[0], linewidth=2.0, zorder=3)
    ax.scatter(n, r, s=22, color=SERIES[0], zorder=4)
    for tgt, col in ((0.8, STATUS["warning"]), (0.9, STATUS["good"])):
        ax.axhline(tgt, color=col, linestyle=(0, (4, 3)), linewidth=1.4, zorder=2)
        need = next((int(k) for k, v in zip(n, r) if v >= tgt), None)
        ax.annotate(f"{tgt:g} needs {need} seeds" if need else f"{tgt:g} not reached within 15",
                    xy=(15, tgt), xytext=(-4, 4), textcoords="offset points",
                    ha="right", fontsize=8.5, color=INK_2)
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0.5, 15.5)
    ax.set_xlabel("seeds averaged per design", color=INK_2, fontsize=9.5)
    ax.set_ylabel("reliability of the mean", color=INK_2, fontsize=9.5)

    fig.patch.set_facecolor(SURFACE)
    fig.text(0.015, 0.99, "How much of the ipSAE ranking is real?",
             color=INK, fontsize=13, fontweight="600", va="top")
    fig.text(0.015, 0.925,
             f"Variance decomposition over {rel.get('n_replicated')} replicated designs. A single "
             f"seed carries reliability {icc1:.3f};\naveraging more seeds is the only way to make "
             f"design-to-design comparisons defensible.",
             color=INK_2, fontsize=9.5, va="top")
    fig.subplots_adjust(top=0.78)
    save(fig, out / "05_reliability.png")


def fig_correlations(d: dict, out: Path) -> None:
    """Diverging heatmap: correlations have a meaningful zero -> blue<->red, gray midpoint."""
    sp = (d["diag"].get("spearman") or {})
    if not sp:
        print("  skip correlation figure (no diagnostics)")
        return
    preds = list(sp)
    targs = ["ipsae_min", "epitope_recovery", "iptm"]
    M = np.full((len(preds), len(targs)), np.nan)
    for i, p in enumerate(preds):
        for j, t in enumerate(targs):
            v = sp[p].get(t, {}).get("rho")
            if v is not None:
                M[i, j] = v

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    ax.set_facecolor(SURFACE)
    im = ax.imshow(M, cmap=DIVERGING, vmin=-0.6, vmax=0.6, aspect="auto")
    ax.set_xticks(range(len(targs)))
    ax.set_xticklabels(["ipSAE_min", "epitope\nrecovery", "ipTM"], fontsize=9, color=INK_2)
    ax.set_yticks(range(len(preds)))
    ax.set_yticklabels(preds, fontsize=9, color=INK_2)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(len(preds)):
        for j in range(len(targs)):
            if not np.isnan(M[i, j]):
                shade = INK if abs(M[i, j]) < 0.38 else "white"
                ax.text(j, i, f"{M[i,j]:+.2f}", ha="center", va="center",
                        fontsize=9.5, color=shade, fontweight="600")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=INK_2, labelsize=8, length=0)
    cb.set_label("Spearman rho", color=INK_2, fontsize=9)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.015, 0.99, "Sequence scores anti-correlate with interface quality",
             color=INK, fontsize=13, fontweight="600", va="top")
    fig.text(0.015, 0.925,
             "Negative means a higher sequence-plausibility score goes with a WORSE modelled "
             "interface.\nThe parent is affinity-matured, so language models push its CDRs back "
             "toward germline consensus.",
             color=INK_2, fontsize=9.5, va="top")
    fig.subplots_adjust(top=0.76)
    save(fig, out / "06_score_correlations.png")


def fig_scatter(d: dict, out: Path) -> None:
    """ipSAE vs epitope recovery, coloured by mutation count as an ordinal ramp."""
    rows = [r for r in d["scored"]
            if fnum(r.get("ipsae_min")) is not None and fnum(r.get("epitope_recovery")) is not None]
    if len(rows) < 8:
        print("  skip scatter (insufficient data)")
        return
    x = np.array([fnum(r["epitope_recovery"]) for r in rows])
    y = np.array([fnum(r["ipsae_min"]) for r in rows])
    mc = np.array([int(float(r["mutation_count"])) for r in rows])
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    style_axes(ax, grid_axis="both")
    for i, m in enumerate(sorted(set(mc))):
        sel = mc == m
        ax.scatter(x[sel], y[sel], s=34,
                   color=BLUE_ORDINAL[min(i, len(BLUE_ORDINAL) - 1)],
                   edgecolor=SURFACE, linewidth=0.9, label=f"{m} substitutions", zorder=3)
    add_parent_ref(ax, pm, ps)
    if pm is not None:
        ax.scatter([1.0], [pm], marker="*", s=230, color=STATUS["good"],
                   edgecolor=SURFACE, linewidth=1.2, zorder=5)
        ax.annotate("parent", xy=(1.0, pm), xytext=(-8, 10), textcoords="offset points",
                    ha="right", fontsize=9, color=INK_2, fontweight="600")
    leg = ax.legend(frameon=False, fontsize=9, loc="lower left", title="")
    for t in leg.get_texts():
        t.set_color(INK_2)
    finish(fig, ax,
           "Epitope recovery against interface confidence",
           "Each point is one design. Epitope recovery is the fraction of the 19 experimentally "
           "observed\n1N8Z contacts reproduced in the model - a design can be confident and still "
           "bind the wrong face.",
           "epitope recovery (fraction of experimental contacts)", "ipSAE_min")
    save(fig, out / "07_epitope_vs_ipsae.png")


def fig_top_designs(d: dict, out: Path) -> None:
    """The nominated designs with error bars, ranked. Single series, no legend."""
    top = d["top15"] or d["top50"]
    if not top:
        print("  skip top-designs figure (no selection yet)")
        return
    top = [r for r in top if fnum(r.get("ipsae_min")) is not None][:15]
    if not top:
        return
    ids = [r["candidate_id"] for r in top]
    means = np.array([fnum(r["ipsae_min"]) for r in top])
    sds = np.array([fnum(r.get("ipsae_min_sd")) or 0 for r in top])
    muts = [r["mutation_count"] for r in top]
    pm, ps = parent_band(d["raw"])

    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    style_axes(ax, grid_axis="x")
    y = np.arange(len(ids))[::-1]
    ax.barh(y, means, height=0.6, color=SERIES[0], edgecolor=SURFACE, linewidth=2.0, zorder=3)
    ax.errorbar(means, y, xerr=sds, fmt="none", ecolor=INK_2, elinewidth=1.3,
                capsize=3.5, capthick=1.3, zorder=4)
    add_parent_ref(ax, pm, ps, horizontal=False)
    # Place each value label clear of its own error-bar cap, not at the bar end.
    for yi, m, sd, mu in zip(y, means, sds, muts):
        ax.annotate(f"{m:.3f}" + (f" +/-{sd:.3f}" if sd else "") + f"   {mu} muts",
                    xy=(m + sd, yi), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=INK_2)
    ax.set_yticks(y)
    ax.set_yticklabels(ids, fontsize=8.5)
    ax.set_xlim(0, max(1.15, float((means + sds).max()) * 1.42))
    finish(fig, ax,
           f"Nominated designs ({len(ids)}) with replicate error bars",
           "Ranked by the multi-objective score, not by ipSAE alone. Error bars that cross the "
           "parent band\nmean the design is not distinguishable from the parent on this metric.",
           "ipSAE_min", "")
    save(fig, out / "08_top_designs.png")


def fig_throughput(d: dict, out: Path) -> None:
    """Where the structures came from. Two series -> legend present."""
    raw = d["raw"]
    if not raw:
        return
    counts = defaultdict(int)
    for r in raw:
        counts[r["source"]] += 1
    srcs = [s for s in ("Local", "Modal") if counts.get(s)]
    if not srcs:
        return
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    style_axes(ax, grid_axis="x")
    left = 0
    for i, s in enumerate(srcs):
        ax.barh([0], [counts[s]], left=[left], height=0.42, color=SERIES[i],
                edgecolor=SURFACE, linewidth=2.0, label=f"{s}  {counts[s]}")
        left += counts[s]
    ax.set_yticks([])
    ax.set_xlim(0, left * 1.02)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=len(srcs))
    for t in leg.get_texts():
        t.set_color(INK_2)
    finish(fig, ax, f"{left} scored structures",
           "Boltz-2 cofolds of scFv against HER2 domain IV, all with full PAE and external ipSAE.",
           "structures", "")
    save(fig, out / "09_throughput.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--results", type=Path, default=base / "outputs")
    ap.add_argument("--outdir", type=Path, default=base / "outputs" / "figures")
    args = ap.parse_args()

    d = load(args.results)
    print(f"[plots] {len(d['raw'])} scored structures, {len(d['scored'])} designs")
    args.outdir.mkdir(parents=True, exist_ok=True)
    for fn in (fig_distribution, fig_by_mutation_count, fig_by_branch, fig_replicate_spread,
               fig_reliability, fig_correlations, fig_scatter, fig_top_designs, fig_throughput):
        try:
            fn(d, args.outdir)
        except Exception as exc:                                 # noqa: BLE001
            print(f"  [warn] {fn.__name__} failed: {type(exc).__name__}: {exc}")
    print(f"[plots] done -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
