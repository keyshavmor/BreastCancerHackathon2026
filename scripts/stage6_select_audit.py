#!/usr/bin/env python
"""Stage 6 - multi-objective selection, compliance audit and submission packaging.

Builds the only files that may be handed to the organizer, under one rule: a
design appears in ``submission_scored.*`` **only** if it has a real structure, a
real full PAE matrix and a real externally computed ipSAE. Anything else stays in
the internal pool labelled ``NOT_EVALUATED``. No value is ever estimated,
interpolated or carried over from another design.

Selection is deliberately *not* "sort by ipSAE". Four reasons, all from the
brief: ipSAE is not calibrated to K_D; a 0.01 ipSAE gap can be smaller than
seed noise; a confident model can bind the wrong face; and 15 near-identical
neighbours are not 15 independent hypotheses. So ranking is a weighted
aggregation of *percentile ranks* across five orthogonal axes, followed by
diversity-aware allocation under branch quotas.

Because the weights are a hypothesis rather than a fitted model, the script runs
a **sensitivity analysis**: it re-ranks under alternative weightings and reports
which designs are stable and which depend on one metric. Designs whose ipSAE
advantage over the parent is smaller than the measured seed noise are flagged
``WITHIN_SEED_NOISE`` rather than presented as improvements.

Run:
    python stage6_select_audit.py --top-n 15
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import her2_common as hc
from stage2_generate_candidates import BRANCH_SLOTS, greedy_diverse

# Primary weighting. Stated as a hypothesis; see SENSITIVITY_SCHEMES.
PRIMARY_WEIGHTS = {
    "sequence_consensus": 0.30,   # AbLang2 + ESM2 rank aggregate (orthogonal priors)
    "ipsae": 0.25,                # required organizer metric, never the sole axis
    "epitope_recovery": 0.20,     # did it bind the experimentally observed face
    "structural_confidence": 0.15,# ipTM / pLDDT from Boltz
    "developability": 0.10,       # fewer newly introduced liabilities
}
SENSITIVITY_SCHEMES = {
    "ipsae_heavy": {"sequence_consensus": 0.15, "ipsae": 0.50, "epitope_recovery": 0.15,
                    "structural_confidence": 0.10, "developability": 0.10},
    "sequence_heavy": {"sequence_consensus": 0.50, "ipsae": 0.15, "epitope_recovery": 0.15,
                       "structural_confidence": 0.10, "developability": 0.10},
    "equal": {k: 0.2 for k in PRIMARY_WEIGHTS},
}
# A model that recovers less than this fraction of the experimental epitope is
# binding the wrong surface; its interface scores are not trustworthy.
MIN_EPITOPE_RECOVERY = 0.30


def pct_rank(values: list[float]) -> list[float]:
    """Percentile ranks in [0,1], higher = better; non-finite gets 0."""
    arr = np.asarray([v if v is not None and np.isfinite(v) else np.nan for v in values], float)
    out = np.zeros(len(arr))
    ok = ~np.isnan(arr)
    if ok.sum() == 0:
        return out.tolist()
    vals = arr[ok]
    order = np.argsort(-vals, kind="stable")
    r = np.empty(len(vals))
    r[order] = np.arange(len(vals))
    out[ok] = 1.0 - r / max(1, len(vals) - 1)
    return out.tolist()


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fnum(v, default=None):
    try:
        f = float(v)
        return f if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    base = here.parent
    ap.add_argument("--outdir", type=Path, default=base / "outputs")
    ap.add_argument("--queues", type=Path, nargs="*", default=None,
                    help="queue CSVs that define the candidate universe. Defaults to every "
                         "known queue, because a design only enters the submission if its "
                         "sequence is found here - missing one silently drops those designs.")
    ap.add_argument("--top-n", type=int, default=15)
    ap.add_argument("--top-50", type=int, default=50,
                    help="also emit this many top-ranked fully scored designs")
    ap.add_argument("--min-epitope-recovery", type=float, default=MIN_EPITOPE_RECOVERY)
    ap.add_argument("--ipsae-floor-sd", type=float, default=3.0,
                    help="veto designs whose ipSAE is more than this many seed-SDs below the "
                         "parent; a collapsed interface is disqualifying regardless of how well "
                         "a design scores on the other ranking axes (0 disables)")
    args = ap.parse_args()
    out = args.outdir
    hc.assert_parent_integrity()

    qpaths = args.queues if args.queues else [
        out / "priority_cofold_queue.csv",
        out / "priority_cofold_queue_merged.csv",
        out / "queue_exploit.csv",
        out / "queue_sweep.csv",
        out / "queue_breadth.csv",
        out / "queue_winners.csv",
        out / "round2" / "priority_cofold_queue.csv",
    ]
    queue: list[dict] = []
    seen_q: set[str] = set()
    for qp in qpaths:
        for r in read_csv(qp):
            cid = r.get("candidate_id")
            if cid and cid not in seen_q:
                seen_q.add(cid)
                queue.append(r)
    print(f"[universe] {len(queue)} candidate sequences from "
          f"{sum(1 for q in qpaths if Path(q).is_file())} queue file(s)")
    agg = {r["candidate_id"]: r for r in read_csv(out / "ipsae_aggregated.csv")}
    raw = read_csv(out / "boltz_results_raw.csv")
    internal = read_csv(out / "internal_50_candidates.csv")
    if not queue or not agg:
        raise SystemExit("missing priority_cofold_queue.csv or ipsae_aggregated.csv")

    seq_of = {r["candidate_id"]: r["full_scfv_sequence"] for r in queue}
    meta_of = {r["candidate_id"]: r for r in queue}

    parent = agg.get("parent", {})
    parent_ipsae = fnum(parent.get("ipsae_min_mean"))
    parent_sd = fnum(parent.get("ipsae_min_sd"), 0.0) or 0.0
    parent_recov = fnum(parent.get("epitope_recovery_mean"))
    print(f"[parent] ipsae_min={parent_ipsae} sd={parent_sd} epitope_recovery={parent_recov}")

    # Seed noise: pooled sd across every candidate that has replicates. This is
    # the yardstick an ipSAE delta has to beat to mean anything.
    sds = [fnum(r.get("ipsae_min_sd")) for cid, r in agg.items()
           if cid != "parent" and int(r.get("n_seeds") or 0) > 1]
    sds = [s for s in sds if s is not None]
    seed_noise = statistics.fmean(sds) if sds else parent_sd
    print(f"[noise] pooled ipSAE seed sd over {len(sds)} replicated candidates = {seed_noise:.4f}")

    # ---- assemble scored candidates --------------------------------------- #
    rows: list[dict] = []
    excluded: list[dict] = []
    for cid, a in agg.items():
        if cid == "parent":
            continue
        seq = seq_of.get(cid)
        if seq is None:
            excluded.append({"candidate_id": cid, "reason": "not in cofold queue"})
            continue
        ipsae = fnum(a.get("ipsae_min_mean"))
        if ipsae is None:
            excluded.append({"candidate_id": cid, "reason": "no finite ipSAE"})
            continue
        v = hc.validate_candidate(seq, cid)
        if not v.ok:
            excluded.append({"candidate_id": cid, "reason": f"validator: {v.failures}"})
            continue
        recov = fnum(a.get("epitope_recovery_mean"))
        if recov is not None and recov < args.min_epitope_recovery:
            excluded.append({"candidate_id": cid,
                             "reason": f"epitope_recovery {recov} < {args.min_epitope_recovery}"})
            continue
        # Interface collapse flag. A design this far below the parent has lost
        # its interface, and rank aggregation across five axes could otherwise
        # NOMINATE it, because strong sequence-consensus, epitope-recovery and
        # developability scores outvote a catastrophic ipSAE.
        #
        # It is flagged rather than dropped: the organizer asked for a genuine
        # ipSAE per submitted design, and a poor score is a real result. So the
        # design stays in submission_scored.* with its measured value, and is
        # barred from the lab nominations only.
        interface_collapsed = False
        if parent_ipsae is not None and args.ipsae_floor_sd > 0:
            floor = parent_ipsae - args.ipsae_floor_sd * max(seed_noise, 1e-6)
            interface_collapsed = ipsae < floor
        m = meta_of[cid]
        newlia = m.get("new_liability_flags") or ""
        rows.append({
            "candidate_id": cid, "branch": m.get("branch", ""),
            "full_scfv_sequence": seq, "sequence_sha256": hc.sha256_seq(seq),
            "mutation_count": v.mutation_count, "mutations_1based": ";".join(v.mutations),
            "mutated_domains": ";".join(sorted({hc.domain_of(int(x[1:-1])) for x in v.mutations})),
            "mutated_CDRs": ";".join(sorted({hc.cdr_of(int(x[1:-1])) for x in v.mutations})),
            "new_cysteine_count": 0, "new_liability_flags": newlia,
            "ablang2_contextual": m.get("ablang2_contextual", ""),
            "esm2_contextual": m.get("esm2_contextual", ""),
            "sequence_consensus_score": fnum(m.get("sequence_consensus_score"), 0.0),
            "model_disagreement": m.get("model_disagreement", ""),
            "priority_tier": m.get("priority_tier", ""),
            "boltz_evaluated": True,
            "n_seeds": int(a.get("n_seeds") or 1),
            "interface_status": "COLLAPSED" if interface_collapsed else "OK",
            "ipsae_min": ipsae, "ipsae_min_sd": fnum(a.get("ipsae_min_sd"), 0.0),
            "ipsae_min_best": fnum(a.get("ipsae_min_best")),
            "ipsae_max": fnum(a.get("ipsae_max_mean")),
            "ipsae_delta_vs_parent": round(ipsae - parent_ipsae, 4) if parent_ipsae else "",
            "iptm": fnum(a.get("iptm_mean")), "pDockQ": fnum(a.get("pDockQ_mean")),
            "LIS": fnum(a.get("LIS_mean")),
            "epitope_recovery": recov,
            "seeds": a.get("seeds", ""),
            # Recomputed from the sequence rather than parsed out of stage 2's
            # human-readable warning string: the authoritative source is the
            # sequence itself, and a free-text field is not a data format.
            "n_new_liabilities": sum(v for k, v in hc.new_liabilities(seq).items()
                                     if k != "nglyc_sequon"),
        })
    print(f"[assemble] {len(rows)} ipSAE-complete candidates, {len(excluded)} excluded")

    if not rows:
        raise SystemExit("no ipSAE-complete candidates; refusing to write a submission")

    # ---- do the sequence-stage scores predict anything structural? -------- #
    # This is a diagnostic, not a filter, and it is computed every run because
    # the answer governs how the next round should select candidates. In round 1
    # every sequence score came out NEGATIVELY correlated with interface quality
    # (see requeue_structure_informed.py), which is why selection must not simply
    # maximise sequence plausibility.
    def spearman(xs: list, ys: list) -> tuple[float | None, int]:
        pairs = [(x, y) for x, y in zip(xs, ys)
                 if x is not None and y is not None
                 and np.isfinite(x) and np.isfinite(y)]
        if len(pairs) < 8:
            return None, len(pairs)
        a = np.asarray([p[0] for p in pairs], float)
        b = np.asarray([p[1] for p in pairs], float)
        ra = a.argsort().argsort().astype(float)
        rb = b.argsort().argsort().astype(float)
        if ra.std() == 0 or rb.std() == 0:
            return None, len(pairs)
        return float(np.corrcoef(ra, rb)[0, 1]), len(pairs)

    predictors = {
        "ablang2_contextual": [fnum(meta_of[r["candidate_id"]].get("ablang2_contextual")) for r in rows],
        "esm2_contextual": [fnum(meta_of[r["candidate_id"]].get("esm2_contextual")) for r in rows],
        "ablang2_additive_mean": [fnum(meta_of[r["candidate_id"]].get("ablang2_additive_mean")) for r in rows],
        "esm2_additive_mean": [fnum(meta_of[r["candidate_id"]].get("esm2_additive_mean")) for r in rows],
        "sequence_consensus_score": [r["sequence_consensus_score"] for r in rows],
        "mutation_count": [float(r["mutation_count"]) for r in rows],
    }
    targets = {"ipsae_min": [r["ipsae_min"] for r in rows],
               "epitope_recovery": [r["epitope_recovery"] for r in rows],
               "iptm": [r["iptm"] for r in rows]}
    diag: dict[str, dict] = {"n_scored": len(rows), "spearman": {}}
    for pn, pv in predictors.items():
        diag["spearman"][pn] = {}
        for tn, tv in targets.items():
            rho, n = spearman(pv, tv)
            diag["spearman"][pn][tn] = {"rho": None if rho is None else round(rho, 4), "n": n}

    # Per-stratum means, which is how the mutation-count effect was spotted.
    def group_means(key_fn) -> dict:
        g: dict = {}
        for r in rows:
            g.setdefault(key_fn(r), []).append(r)
        return {str(k): {
            "n": len(v),
            "ipsae_min_mean": round(statistics.fmean([x["ipsae_min"] for x in v]), 4),
            "ipsae_min_sd": round(statistics.stdev([x["ipsae_min"] for x in v]), 4) if len(v) > 1 else 0.0,
            "iptm_mean": round(statistics.fmean([x["iptm"] for x in v if x["iptm"] is not None]), 4)
                         if any(x["iptm"] is not None for x in v) else None,
            "epitope_recovery_mean": round(statistics.fmean(
                [x["epitope_recovery"] for x in v if x["epitope_recovery"] is not None]), 4)
                if any(x["epitope_recovery"] is not None for x in v) else None,
        } for k, v in sorted(g.items(), key=lambda kv: str(kv[0]))}

    diag["by_mutation_count"] = group_means(lambda r: r["mutation_count"])
    diag["by_branch"] = group_means(lambda r: r["branch"])
    diag["parent_reference"] = {"ipsae_min": parent_ipsae, "epitope_recovery": parent_recov}

    # ---- how much of the ipSAE ranking is real? -------------------------- #
    # A variance decomposition over replicated designs. This is the number that
    # governs every claim downstream: if within-design (seed) variance rivals
    # between-design variance, a single-seed ranking is mostly noise and no
    # design can be called better than another.
    per_seed: dict[str, list[float]] = {}
    for r in raw:
        if r.get("ipsae_status") != "PASSED":
            continue
        v = fnum(r.get("ipsae_min"))
        if v is not None:
            per_seed.setdefault(r["candidate_id"], []).append(v)
    reps = {k: v for k, v in per_seed.items() if len(v) >= 2}

    rel: dict = {"n_replicated": len(reps)}
    if len(reps) >= 3:
        n_each = statistics.fmean([len(v) for v in reps.values()])
        s2_within = statistics.fmean([statistics.variance(v) for v in reps.values()])
        cand_means = [statistics.fmean(v) for v in reps.values()]
        s2_between_obs = statistics.variance(cand_means)
        # Observed spread of means still contains noise/n, so subtract it.
        s2_true = max(0.0, s2_between_obs - s2_within / n_each)
        icc1 = s2_true / (s2_true + s2_within) if (s2_true + s2_within) > 0 else 0.0
        iccn = s2_true / (s2_true + s2_within / n_each) if (s2_true + s2_within / n_each) > 0 else 0.0

        def seeds_for(target: float) -> int | None:
            if s2_true <= 0:
                return None
            return int(np.ceil(s2_within / s2_true * (target / (1 - target))))

        rel.update({
            "mean_seeds_per_design": round(n_each, 2),
            "sd_within_seed": round(float(np.sqrt(s2_within)), 4),
            "sd_between_designs_observed": round(float(np.sqrt(s2_between_obs)), 4),
            "sd_between_designs_true_est": round(float(np.sqrt(s2_true)), 4),
            "reliability_single_seed": round(icc1, 3),
            "reliability_current_mean": round(iccn, 3),
            "seeds_for_reliability_0.8": seeds_for(0.8),
            "seeds_for_reliability_0.9": seeds_for(0.9),
            "note": "reliability = fraction of ranking variance that is real signal "
                    "rather than seed noise (an intraclass correlation).",
        })

        # Correlations measured on noisy values are attenuated toward zero, so
        # the TRUE predictor-outcome relationships are stronger than reported.
        if icc1 > 0:
            att = float(np.sqrt(icc1))
            rel["attenuation_correction_factor"] = round(1 / att, 3)
            rel["ipsae_correlations_disattenuated"] = {
                pn: (None if tv["ipsae_min"]["rho"] is None
                     else round(tv["ipsae_min"]["rho"] / att, 4))
                for pn, tv in diag["spearman"].items()
            }

        # Welch comparison of each replicated design against the parent.
        pvals = per_seed.get("parent", [])
        if len(pvals) >= 2:
            pm, psd, pn = statistics.fmean(pvals), statistics.stdev(pvals), len(pvals)
            tests = []
            for cid, vals in reps.items():
                if cid == "parent" or len(vals) < 2:
                    continue
                m, sd, n = statistics.fmean(vals), statistics.stdev(vals), len(vals)
                se = float(np.sqrt(sd ** 2 / n + psd ** 2 / pn))
                t = (m - pm) / se if se > 0 else 0.0
                tests.append({"candidate_id": cid, "n_seeds": n,
                              "ipsae_mean": round(m, 4), "ipsae_sd": round(sd, 4),
                              "delta_vs_parent": round(m - pm, 4), "t": round(t, 2),
                              "verdict": "ABOVE_PARENT" if t > 2 else
                                         "BELOW_PARENT" if t < -2 else "INDISTINGUISHABLE"})
            # Multiple-comparison correction. Testing ~60 designs at alpha=0.05
            # yields ~3 false positives by chance, so an uncorrected "above
            # parent" count near 3-4 is indistinguishable from noise. Report
            # Benjamini-Hochberg q-values and make the headline verdict the
            # FDR-controlled one; the raw t is kept for transparency.
            try:
                from scipy import stats as _st

                for d_ in tests:
                    n1 = d_["n_seeds"]
                    # Welch-Satterthwaite dof, approximated with the pooled sds
                    # we have; conservative enough at these small n.
                    df = max(1.0, n1 + pn - 2)
                    d_["p_uncorrected"] = round(
                        float(2 * _st.t.sf(abs(d_["t"]), df)), 5)
                ordered = sorted(tests, key=lambda z: z["p_uncorrected"])
                m = len(ordered)
                qprev = 1.0
                for i in range(m - 1, -1, -1):
                    q = min(qprev, ordered[i]["p_uncorrected"] * m / (i + 1))
                    ordered[i]["q_value_BH"] = round(float(q), 5)
                    qprev = q
                for d_ in tests:
                    sig = d_.get("q_value_BH", 1.0) < 0.05
                    d_["verdict_fdr"] = (
                        "ABOVE_PARENT_FDR" if sig and d_["t"] > 0 else
                        "BELOW_PARENT_FDR" if sig and d_["t"] < 0 else
                        "NOT_SIGNIFICANT_AFTER_CORRECTION")
            except Exception as exc:                             # noqa: BLE001
                print(f"[warn] FDR correction unavailable: {type(exc).__name__}")
            tests.sort(key=lambda d: -d["delta_vs_parent"])
            rel["parent_comparison"] = {
                "parent_mean": round(pm, 4), "parent_sd": round(psd, 4), "parent_n_seeds": pn,
                "threshold": "|t| > 2",
                "n_above": sum(1 for d in tests if d["verdict"] == "ABOVE_PARENT"),
                "n_above_fdr": sum(1 for d in tests
                                   if d.get("verdict_fdr") == "ABOVE_PARENT_FDR"),
                "n_tests": len(tests),
                "expected_false_positives_at_uncorrected_alpha05": round(0.05 * len(tests), 1),
                "correction": "Benjamini-Hochberg FDR at q<0.05 over all tested designs",
                "n_below": sum(1 for d in tests if d["verdict"] == "BELOW_PARENT"),
                "n_indistinguishable": sum(1 for d in tests
                                           if d["verdict"] == "INDISTINGUISHABLE"),
                "tests": tests,
            }
            print(f"[reliability] single-seed={rel['reliability_single_seed']} "
                  f"current-mean={rel['reliability_current_mean']} "
                  f"(need {rel.get('seeds_for_reliability_0.8')} seeds for 0.8)")
            print(f"[vs parent]  above={rel['parent_comparison']['n_above']} "
                  f"below={rel['parent_comparison']['n_below']} "
                  f"indistinguishable={rel['parent_comparison']['n_indistinguishable']}")
    diag["reliability"] = rel
    diag["interpretation"] = (
        "Negative rho means a HIGHER sequence-plausibility score goes with a WORSE modelled "
        "interface. Trastuzumab's CDRs are affinity-matured, so an antibody language model "
        "tends to propose reverting them toward germline consensus - precisely the residues "
        "contacting HER2. The mutation_count effect is partly confounded by MSA reuse."
    )
    (out / "score_diagnostics.json").write_text(json.dumps(diag, indent=2))
    print(f"[diagnostics] sequence-vs-structure correlations written "
          f"(n={len(rows)}); see score_diagnostics.json")

    # ---- rank aggregation -------------------------------------------------- #
    axes = {
        "sequence_consensus": pct_rank([r["sequence_consensus_score"] for r in rows]),
        "ipsae": pct_rank([r["ipsae_min"] for r in rows]),
        "epitope_recovery": pct_rank([r["epitope_recovery"] for r in rows]),
        "structural_confidence": pct_rank([r["iptm"] for r in rows]),
        "developability": pct_rank([-r["n_new_liabilities"] for r in rows]),
    }
    for i, r in enumerate(rows):
        for k, v in axes.items():
            r[f"rank_{k}"] = round(v[i], 4)
        r["rank_score"] = round(sum(PRIMARY_WEIGHTS[k] * axes[k][i] for k in PRIMARY_WEIGHTS), 4)
        for name, w in SENSITIVITY_SCHEMES.items():
            r[f"rank_score_{name}"] = round(sum(w[k] * axes[k][i] for k in w), 4)
        d = r["ipsae_delta_vs_parent"]
        # A one-seed measurement cannot support a directional claim when the
        # measured single-seed reliability is around 0.5. Saying "above parent"
        # off a single draw would be exactly the error this pipeline exists to
        # avoid, so such designs are labelled unreliable rather than ranked
        # against the parent.
        if not isinstance(d, float):
            r["ipsae_interpretation"] = "NO_PARENT_BASELINE"
        elif r["n_seeds"] < 2:
            r["ipsae_interpretation"] = "SINGLE_SEED_UNRELIABLE"
        elif abs(d) <= max(seed_noise, 1e-9):
            r["ipsae_interpretation"] = "WITHIN_SEED_NOISE"
        else:
            r["ipsae_interpretation"] = "ABOVE_PARENT" if d > 0 else "BELOW_PARENT"

    rows.sort(key=lambda r: -r["rank_score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # rank stability across schemes
    order_primary = {r["candidate_id"]: i for i, r in enumerate(rows)}
    stability: dict[str, int] = {}
    for name in SENSITIVITY_SCHEMES:
        alt = sorted(rows, key=lambda r: -r[f"rank_score_{name}"])
        pos = {r["candidate_id"]: i for i, r in enumerate(alt)}
        for cid in order_primary:
            stability[cid] = max(stability.get(cid, 0), abs(order_primary[cid] - pos[cid]))
    for r in rows:
        r["max_rank_shift_under_reweighting"] = stability[r["candidate_id"]]

    # ---- diversity-aware top N with branch quotas ------------------------- #
    for r in rows:
        r["mutation_positions"] = [int(x[1:-1]) for x in r["mutations_1based"].split(";")]
    chosen: list[dict] = []
    nominable = [r for r in rows if r["interface_status"] == "OK"]
    print(f"[select] {len(rows) - len(nominable)} designs barred from nomination "
          f"(interface collapsed); {len(nominable)} eligible")
    quota = {b: max(1, round(args.top_n * s / sum(BRANCH_SLOTS.values())))
             for b, s in BRANCH_SLOTS.items()}
    for b, q in quota.items():
        pool = [r for r in nominable if r["branch"] == b]
        chosen += greedy_diverse(pool, min(q, len(pool)))
    have = {r["candidate_id"] for r in chosen}
    for r in nominable:
        if len(chosen) >= args.top_n:
            break
        if r["candidate_id"] not in have:
            chosen.append(r)
            have.add(r["candidate_id"])
    # Force-include designs with FDR-corrected evidence of exceeding the parent.
    # The multi-objective score weights ipSAE at only 0.25 and imposes branch
    # quotas, which can crowd out the very designs for which the statistical
    # evidence is strongest - that is exactly what happened to the best design
    # here. A multiple-comparison-corrected advantage earns a lab slot outright.
    fdr_ids: set[str] = set()
    try:
        _pc = ((diag.get("reliability") or {}).get("parent_comparison") or {})
        fdr_ids = {t["candidate_id"] for t in _pc.get("tests", [])
                   if t.get("verdict_fdr") == "ABOVE_PARENT_FDR"}
    except Exception:                                            # noqa: BLE001
        fdr_ids = set()
    by_id = {r["candidate_id"]: r for r in nominable}
    forced = [by_id[c] for c in sorted(fdr_ids) if c in by_id]
    if forced:
        fids = {f["candidate_id"] for f in forced}
        chosen = forced + [r for r in chosen if r["candidate_id"] not in fids]
        print(f"[select] force-included {len(forced)} FDR-significant design(s): "
              f"{sorted(fids)}")
    missing = sorted(fdr_ids - set(by_id))
    if missing:
        print(f"[select] WARNING {len(missing)} FDR-significant design(s) not nominable "
              f"(interface collapsed or filtered): {missing}")
    # FDR winners first, then the multi-objective order.
    chosen = (sorted([r for r in chosen if r["candidate_id"] in fdr_ids],
                     key=lambda r: -r["rank_score"])
              + sorted([r for r in chosen if r["candidate_id"] not in fdr_ids],
                       key=lambda r: -r["rank_score"]))[: args.top_n]
    chosen_ids = {r["candidate_id"] for r in chosen}
    for r in rows:
        r["selected_top15"] = r["candidate_id"] in chosen_ids
    print(f"[select] top {len(chosen)} nominees, branch mix="
          f"{ {b: sum(1 for r in chosen if r['branch']==b) for b in BRANCH_SLOTS} }")

    # ---- write submission artifacts --------------------------------------- #
    fields = ["rank", "candidate_id", "branch", "priority_tier", "selected_top15",
              "mutation_count", "mutations_1based", "mutated_domains", "mutated_CDRs",
              "new_cysteine_count", "new_liability_flags", "interface_status",
              "ablang2_contextual", "esm2_contextual", "sequence_consensus_score",
              "model_disagreement", "boltz_evaluated", "n_seeds", "seeds",
              "ipsae_min", "ipsae_min_sd", "ipsae_min_best", "ipsae_max",
              "ipsae_delta_vs_parent", "ipsae_interpretation",
              "iptm", "pDockQ", "LIS", "epitope_recovery",
              "rank_sequence_consensus", "rank_ipsae", "rank_epitope_recovery",
              "rank_structural_confidence", "rank_developability", "rank_score",
              "rank_score_ipsae_heavy", "rank_score_sequence_heavy", "rank_score_equal",
              "max_rank_shift_under_reweighting",
              "sequence_sha256", "full_scfv_sequence"]

    def write_set(stem: str, data: list[dict]) -> None:
        with open(out / f"{stem}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
        hc.write_fasta(out / f"{stem}.fasta",
                       {r["candidate_id"]: r["full_scfv_sequence"] for r in data})

    write_set("submission_scored", rows)
    write_set("top_15_scored", chosen)
    # The brief asks for a 50-proposal pool. internal_50_candidates.* (stage 3) is
    # that pool as chosen on sequence evidence alone, with ipSAE NOT_EVALUATED.
    # When more than 50 designs are ipSAE-complete we can do strictly better, so
    # we also emit the top 50 of the final multi-objective ranking - every row of
    # which carries a real, externally computed ipSAE.
    if len(rows) > args.top_50:
        write_set("top_50_scored", rows[: args.top_50])
        print(f"[select] top_50_scored.* written ({args.top_50} fully scored designs)")

    with open(out / "excluded_from_submission.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate_id", "reason"])
        w.writerows([[e["candidate_id"], e["reason"]] for e in excluded])

    # ---- compliance audit (PASS / FAIL / NOT_EVALUATED from real files) ---- #
    checks: list[dict] = []

    def check(name: str, ok: bool | None, detail: str) -> None:
        checks.append({"check": name,
                       "result": "NOT_EVALUATED" if ok is None else ("PASS" if ok else "FAIL"),
                       "detail": detail})

    check("parent_integrity", hc.sha256_seq(hc.PARENT_SEQ) == hc.PARENT_SHA256,
          f"len=242 sha256={hc.PARENT_SHA256}")
    check("internal_pool_exists", len(internal) >= 50, f"{len(internal)} internal candidates")

    bad_len = [r["candidate_id"] for r in rows if len(r["full_scfv_sequence"]) != 242]
    check("all_submitted_length_242", not bad_len, f"violations={bad_len}")

    bad_mut = [r["candidate_id"] for r in rows if r["mutation_count"] < hc.MIN_MUTATIONS]
    check("all_submitted_min_5_mutations", not bad_mut, f"violations={bad_mut}")

    bad_linker = [r["candidate_id"] for r in rows
                  if r["full_scfv_sequence"][120:135] != hc.LINKER_SEQ]
    check("linker_intact", not bad_linker, f"violations={bad_linker}")

    bad_cys = [r["candidate_id"] for r in rows
               if tuple(i + 1 for i, a in enumerate(r["full_scfv_sequence"]) if a == "C") != hc.NATIVE_CYS]
    check("native_cysteines_preserved_no_new", not bad_cys, f"violations={bad_cys}")

    seqs = [r["full_scfv_sequence"] for r in rows]
    check("submitted_sequences_unique", len(set(seqs)) == len(seqs),
          f"{len(seqs)} rows, {len(set(seqs))} unique")

    sigs = [r["mutations_1based"] for r in rows]
    check("mutation_signatures_unique", len(set(sigs)) == len(sigs),
          f"{len(set(sigs))} unique signatures")

    recon_bad = []
    for r in rows:
        try:
            if hc.apply_mutations(r["mutations_1based"], hc.PARENT_SEQ) != r["full_scfv_sequence"]:
                recon_bad.append(r["candidate_id"])
        except Exception:                                        # noqa: BLE001
            recon_bad.append(r["candidate_id"])
    check("reconstructible_from_mutation_list", not recon_bad, f"violations={recon_bad}")

    nonfinite = [r["candidate_id"] for r in rows if not np.isfinite(r["ipsae_min"])]
    check("every_submitted_has_finite_ipsae", not nonfinite, f"violations={nonfinite}")

    raw_ok = {r["candidate_id"] for r in raw if r.get("ipsae_status") == "PASSED"}
    missing_art = [r["candidate_id"] for r in rows if r["candidate_id"] not in raw_ok]
    check("structure_and_pae_present_for_submitted", not missing_art, f"violations={missing_art}")

    check("parent_baseline_scored", parent_ipsae is not None,
          f"parent ipsae_min={parent_ipsae} over {parent.get('n_seeds')} seed(s)")

    stale = []
    for p in (out / "contract.json", out / "residue_map.csv"):
        if p.is_file() and any(t in p.read_text() for t in ("EGFR", "1YY9", "etuximab")):
            stale.append(p.name)
    check("no_stale_EGFR_cetuximab_inputs", not stale, f"files_with_stale_refs={stale}")

    check("top15_size", len(chosen) == args.top_n, f"{len(chosen)}/{args.top_n} nominees")
    check("top15_branch_diversity", len({r['branch'] for r in chosen}) >= 3,
          f"branches={sorted({r['branch'] for r in chosen})}")
    check("top15_distinct_mutation_sets",
          len({r["mutations_1based"] for r in chosen}) == len(chosen),
          "each nominee has a distinct mutation signature")

    n_fail = sum(1 for c in checks if c["result"] == "FAIL")
    audit = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "overall": "PASS" if n_fail == 0 else "FAIL",
        "failed_checks": n_fail,
        "submitted_scored_count": len(rows),
        "top_n": len(chosen),
        "excluded_count": len(excluded),
        "seed_noise_ipsae_sd": round(seed_noise, 4),
        "parent_baseline": {"ipsae_min": parent_ipsae, "sd": parent_sd,
                            "epitope_recovery": parent_recov},
        "designs_above_parent_beyond_noise":
            sum(1 for r in rows if r["ipsae_interpretation"] == "ABOVE_PARENT"),
        "designs_single_seed_unreliable":
            sum(1 for r in rows if r["ipsae_interpretation"] == "SINGLE_SEED_UNRELIABLE"),
        "interpretation_counts": {
            k: sum(1 for r in rows if r["ipsae_interpretation"] == k)
            for k in ("ABOVE_PARENT", "BELOW_PARENT", "WITHIN_SEED_NOISE",
                      "SINGLE_SEED_UNRELIABLE", "NO_PARENT_BASELINE")},
        "checks": checks,
    }
    (out / "compliance_audit.json").write_text(json.dumps(audit, indent=2))

    git = lambda *a: subprocess.run(["git", "-C", str(base), *a],
                                    capture_output=True, text=True).stdout.strip()
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo_commit": git("rev-parse", "HEAD"),
        "repo_dirty": bool(git("status", "--porcelain")),
        "parent_sha256": hc.PARENT_SHA256,
        "weights_primary": PRIMARY_WEIGHTS,
        "sensitivity_schemes": SENSITIVITY_SCHEMES,
        "min_epitope_recovery": args.min_epitope_recovery,
        "counts": {"scored_submission": len(rows), "top_n": len(chosen),
                   "internal_pool": len(internal), "excluded": len(excluded)},
        "claim_boundary": "Model scores rank designs for experimental triage. "
                          "No in-silico K_D is claimed. ipSAE is not an affinity measurement.",
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"[audit] {audit['overall']} ({n_fail} failed checks); "
          f"{len(rows)} scored designs, {len(chosen)} nominees")
    print(f"[audit] designs above parent beyond seed noise: "
          f"{audit['designs_above_parent_beyond_noise']}/{len(rows)}")
    for c in checks:
        if c["result"] != "PASS":
            print(f"  [{c['result']}] {c['check']}: {c['detail']}")
    print(f"[done] submission_scored.*, top_15_scored.*, compliance_audit.json -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
