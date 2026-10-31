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
    ap.add_argument("--top-n", type=int, default=15)
    ap.add_argument("--min-epitope-recovery", type=float, default=MIN_EPITOPE_RECOVERY)
    args = ap.parse_args()
    out = args.outdir
    hc.assert_parent_integrity()

    queue = read_csv(out / "priority_cofold_queue.csv")
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
        r["ipsae_interpretation"] = (
            "NO_PARENT_BASELINE" if not isinstance(d, float)
            else "WITHIN_SEED_NOISE" if abs(d) <= max(seed_noise, 1e-9)
            else ("ABOVE_PARENT" if d > 0 else "BELOW_PARENT"))

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
    quota = {b: max(1, round(args.top_n * s / sum(BRANCH_SLOTS.values())))
             for b, s in BRANCH_SLOTS.items()}
    for b, q in quota.items():
        pool = [r for r in rows if r["branch"] == b]
        chosen += greedy_diverse(pool, min(q, len(pool)))
    have = {r["candidate_id"] for r in chosen}
    for r in rows:
        if len(chosen) >= args.top_n:
            break
        if r["candidate_id"] not in have:
            chosen.append(r)
            have.add(r["candidate_id"])
    chosen = sorted(chosen, key=lambda r: -r["rank_score"])[: args.top_n]
    chosen_ids = {r["candidate_id"] for r in chosen}
    for r in rows:
        r["selected_top15"] = r["candidate_id"] in chosen_ids
    print(f"[select] top {len(chosen)} nominees, branch mix="
          f"{ {b: sum(1 for r in chosen if r['branch']==b) for b in BRANCH_SLOTS} }")

    # ---- write submission artifacts --------------------------------------- #
    fields = ["rank", "candidate_id", "branch", "priority_tier", "selected_top15",
              "mutation_count", "mutations_1based", "mutated_domains", "mutated_CDRs",
              "new_cysteine_count", "new_liability_flags",
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
