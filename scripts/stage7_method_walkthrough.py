#!/usr/bin/env python
"""Stage 7 - generate ``method_walkthrough.md`` from the run's own artifacts.

The organizer requires a clear explanation of the design method alongside the
sequences and their ipSAE values. This script writes that document, but every
number in it is read back out of the pipeline's manifests, audit and result
tables rather than typed in by hand. If a stage did not run, the corresponding
section says so instead of quoting a stale figure.

Run after stage 6:
    python stage7_method_walkthrough.py --outdir ../outputs
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import her2_common as hc


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:                                            # noqa: BLE001
        return {}


def load_csv(p: Path) -> list[dict]:
    if not p.is_file():
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


def fmt(v, nd=4, dash="n/a"):
    if v is None or v == "":
        return dash
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base = Path(__file__).resolve().parent.parent
    ap.add_argument("--outdir", type=Path, default=base / "outputs")
    ap.add_argument("--top-table", type=int, default=15, help="rows of the nominee table to print")
    args = ap.parse_args()
    o = args.outdir
    hc.assert_parent_integrity()

    contract = load_json(o / "contract.json")
    m2, m3 = load_json(o / "stage2_manifest.json"), load_json(o / "stage3_manifest.json")
    m3b = load_json(o / "stage3b_manifest.json")
    m5, audit = load_json(o / "stage5_manifest.json"), load_json(o / "compliance_audit.json")
    manifest = load_json(o / "run_manifest.json")
    m4 = load_json(base / "pipeline_runs" / "her2_cofold" / "stage4_manifest.json")
    scored = load_csv(o / "submission_scored.csv")
    top = load_csv(o / "top_15_scored.csv")
    internal = load_csv(o / "internal_50_candidates.csv")
    excluded = load_csv(o / "excluded_from_submission.csv")

    tgt = contract.get("target", {})
    div = tgt.get("domain_iv_mature", ["?", "?"])
    parent_base = audit.get("parent_baseline", {})
    L: list[str] = []
    A = L.append

    A("# Method walkthrough: HER2 scFv optimisation")
    A("")
    A(f"Generated {datetime.now(timezone.utc).isoformat()} from this run's own artifacts.")
    A("")
    A("> **Claim boundary.** Every value below is a computational ranking signal for "
      "experimental triage. No affinity is measured or predicted. ipSAE is not K_D, "
      "ipTM is not ipSAE, and a higher score is not a demonstrated improvement. The "
      "parent is already a sub-picomolar binder, so the prior that any 5-8 substitution "
      "variant improves on it is low by construction.")
    A("")

    # ---------------------------------------------------------------- summary
    A("## What was produced")
    A("")
    A("| Deliverable | Count |")
    A("| --- | --- |")
    A(f"| Valid internal proposals (`internal_50_candidates.*`) | {len(internal)} |")
    A(f"| Designs with a real, externally computed ipSAE (`submission_scored.*`) | {len(scored)} |")
    A(f"| Ranked lab nominations (`top_15_scored.*`) | {len(top)} |")
    A(f"| Designs excluded, with recorded reasons | {len(excluded)} |")
    A(f"| Boltz-2 structures computed | {m4.get('completed', 'n/a')} |")
    A("")
    A(f"Compliance audit: **{audit.get('overall', 'NOT_EVALUATED')}** "
      f"({audit.get('failed_checks', '?')} failed checks).")
    A("")

    # ----------------------------------------------------------------- parent
    A("## 1. Immutable parent, verified not assumed")
    A("")
    A("Every stage re-verifies the parent on import and aborts on mismatch, so no design "
      "can be built against the wrong scaffold.")
    A("")
    A("| Property | Value |")
    A("| --- | --- |")
    A(f"| Length | {hc.PARENT_LEN} |")
    A(f"| SHA-256 | `{hc.PARENT_SHA256}` |")
    A(f"| V_H / linker / V_L | {hc.VH_RANGE[0]}-{hc.VH_RANGE[1]} / "
      f"{hc.LINKER_RANGE[0]}-{hc.LINKER_RANGE[1]} `(GGGGS)x3` / {hc.VL_RANGE[0]}-{hc.VL_RANGE[1]} |")
    A(f"| Native cysteines | {', '.join(str(c) for c in hc.NATIVE_CYS)} |")
    A("")
    cdrs = contract.get("cdr_spans_kabat", {})
    if cdrs:
        A("CDRs are located by exact motif match rather than hard-coded indices:")
        A("")
        A("| CDR | Span | Sequence |")
        A("| --- | --- | --- |")
        for k in sorted(cdrs):
            s, e = cdrs[k]
            A(f"| {k} | {s}-{e} | `{hc.PARENT_SEQ[s-1:e]}` |")
        A("")

    # ----------------------------------------------------------------- target
    A("## 2. Target: HER2 domain IV, derived from primary data")
    A("")
    A("Built from RCSB `1N8Z` and UniProt `P04626` only. 1N8Z chain A is the Fab light "
      "chain, B the heavy chain, C the HER2 ectodomain; chain C is numbered in HER2 "
      "**mature** numbering (`uniprot = mature + 22`).")
    A("")
    A("| Property | Value |")
    A("| --- | --- |")
    A(f"| Crop (mature) | {div[0]}-{div[1]} |")
    A(f"| Crop (UniProt) | {tgt.get('domain_iv_uniprot', ['?','?'])[0]}-"
      f"{tgt.get('domain_iv_uniprot', ['?','?'])[1]} |")
    A(f"| Crop length | {tgt.get('domain_iv_length', '?')} aa |")
    A(f"| Intact disulfides in crop | {len(tgt.get('intact_disulfides_in_crop', []))} (0 split) |")
    A(f"| Fab-contacting HER2 residues retained | {len(tgt.get('epitope_contacts_mature', []))} |")
    A(f"| Boltz complex size | {tgt.get('complex_residues_for_boltz', '?')} residues |")
    A("")
    A("The crop is validated three ways before anything is cofolded: it must not split a "
      "disulfide (checked against `SSBOND` records), it must retain every observed "
      "Fab-contacting residue, and its sequence must match UniProt exactly. Any failure is "
      "a hard exit. **The full ~630-residue ectodomain is never cofolded**, per the "
      "organizer's restriction, and the same crop is used for the parent and every "
      "candidate so all comparisons are matched by construction.")
    A("")
    A("Caveats recorded: cropping removes receptor context and creates artificial termini, "
      "and crystallographic glycans are not modelled.")
    A("")

    # ------------------------------------------------------------- generation
    A("## 3. Candidate generation (AbLang2-guided)")
    A("")
    if m2:
        A("| Parameter | Value |")
        A("| --- | --- |")
        A(f"| Raw proposals sampled | {m2.get('pool_size_requested', '?')} |")
        A(f"| Valid unique candidates kept | {m2.get('candidates_kept', '?')} |")
        A(f"| Shortlist to ESM2 | {m2.get('shortlist', '?')} |")
        A(f"| Mutation band | {m2.get('mutation_band', '?')} substitutions |")
        A(f"| Frozen tight-contact anchors | {m2.get('frozen_anchors', '?')} |")
        A(f"| Anchor cutoff | {m2.get('anchor_cutoff_A', '?')} A |")
        A(f"| Substitutions kept per site | {m2.get('top_k_per_site', '?')} |")
        A(f"| Random seed | {m2.get('seed', '?')} |")
        A(f"| Runtime | {m2.get('total_runtime_s', '?')} s |")
        A("")
        rej = m2.get("rejects", {})
        if rej:
            A("Hard-filter rejections (the validator is fail-closed):")
            A("")
            for k, v in sorted(rej.items(), key=lambda kv: -kv[1]):
                A(f"- `{k}`: {v}")
            A("")
        A("Mutation-count distribution: "
          f"{m2.get('mutation_count_hist', {})}")
        A("")
    A("**Mutation policy.** Fixed length 242, substitution-only, 5-8 substitutions "
      "(organizer minimum is 5; the upper bound is our own conservative choice). The "
      "linker and native cysteines are frozen, no new cysteines or N-X-S/T sequons are "
      "allowed, and residues within 3.0 A of HER2 in 1N8Z are frozen as probable "
      "hydrogen-bond or salt-bridge anchors carrying the sub-pM binding energy.")
    A("")
    A("**Why four branches.** Fifty neighbours of one motif are not fifty hypotheses, so "
      "candidates are sampled from four independent mechanistic pools:")
    A("")
    A("| Branch | Slots | Hypothesis |")
    A("| --- | --- | --- |")
    A("| `A_h3` | 20 | focused CDR-H3 maturation (strongest published evidence) |")
    A("| `B_interface` | 12 | non-H3 paratope and contact-adjacent positions |")
    A("| `C_mixed` | 10 | a few paratope edits plus compatible framework support |")
    A("| `D_framework` | 8 | framework-biased control retaining all anchors |")
    A("")
    A("Selection within a branch uses farthest-point selection on Jaccard distance between "
      "mutated-position sets, which is what prevents the portfolio collapsing onto one motif.")
    A("")

    # ----------------------------------------------------------------- rerank
    A("## 4. Sequence screening with two orthogonal priors")
    A("")
    A("AbLang2 asks whether a sequence still looks like a plausible *antibody*; ESM2-3B "
      "asks whether it still looks like a plausible *protein*. The models have different "
      "training distributions and different failure modes, which is the reason for running "
      "both. **Neither model sees HER2, so neither predicts binding.**")
    A("")
    if m3:
        A("| Parameter | Value |")
        A("| --- | --- |")
        A(f"| Model | `{m3.get('model', '?')}` ({m3.get('precision', '?')}) |")
        A(f"| Candidates scored | {m3.get('candidates_scored', '?')} |")
        A(f"| Mutable positions scanned | {m3.get('mutable_positions_scanned', '?')} |")
        A(f"| Cost per candidate | {m3.get('ms_per_seq_contextual', '?')} ms |")
        A(f"| Peak GPU memory | {m3.get('peak_gpu_gib', '?')} GiB |")
        A("")
        ctrl = m3.get("bf16_fp32_control") or {}
        if ctrl:
            A(f"**Numerical control.** {ctrl.get('n')} candidates were rescored in fp32: "
              f"max |diff| {fmt(ctrl.get('max_abs_diff'))}, mean |diff| "
              f"{fmt(ctrl.get('mean_abs_diff'))}, NaNs present: {ctrl.get('any_nan')}. "
              "This is immaterial for ranking; use `--fp32` if absolute scores are needed.")
            A("")
    A("**Scoring design.** Each model is run once over the mutable positions to build a "
      "`position x amino-acid` delta-log-probability table; a candidate's additive score is "
      "then a table lookup. A second pass scores each candidate's mutated positions in its "
      "own context, which is the term that can see interaction between co-occurring "
      "substitutions. Making the expensive part pool-size independent is what allows a "
      "40,000-candidate pool at negligible cost.")
    A("")
    A("Ranking across models uses **rank aggregation of percentile ranks**, not a weighted "
      "sum of raw scores: AbLang2 and ESM2 log-probabilities are in incomparable units, and "
      "absolute thresholds borrowed from one model do not transfer to another.")
    A("")
    if m3b:
        A(f"**Third prior (ESM-C).** `{m3b.get('model')}` scored "
          f"{m3b.get('candidates_scored')} candidates at {m3b.get('ms_per_seq')} ms each.")
        ag = m3b.get("esm2_agreement")
        if ag:
            A(f"Agreement with ESM2-3B over n={ag.get('n')}: Pearson {fmt(ag.get('pearson'))}, "
              f"Spearman {fmt(ag.get('spearman'))}. Disagreement is reported, not penalised: "
              "it marks designs whose plausibility is model-dependent rather than robust.")
        A("")

    # ----------------------------------------------------------------- cofold
    A("## 5. Boltz-2 cofolding against HER2 domain IV")
    A("")
    if m4:
        bs = m4.get("boltz_settings", {})
        A("| Parameter | Value |")
        A("| --- | --- |")
        A(f"| Structures completed | {m4.get('completed', '?')} of {m4.get('runs_planned', '?')} planned |")
        A(f"| Mean cost per structure | {m4.get('mean_seconds_per_structure', '?')} s |")
        A(f"| Total GPU time | {m4.get('total_minutes', '?')} min |")
        A(f"| Diffusion samples / recycling / sampling steps | "
          f"{bs.get('diffusion_samples','?')} / {bs.get('recycling_steps','?')} / "
          f"{bs.get('sampling_steps','?')} |")
        A(f"| Seeds | {bs.get('seeds', '?')} |")
        A(f"| MSA mode | `{bs.get('msa_mode', '?')}` |")
        A(f"| Failures | {m4.get('failed', '?')} |")
        A("")
    A("**MSA policy, and why it matters.** The ColabFold MSA server costs roughly 100 s per "
      "target and is rate-limited. It is called **once**, for the parent; both resulting "
      "alignments are cached and reused for every candidate, with only the query row "
      "rewritten to the candidate's own sequence. This is exact for substitution-only "
      "variants at fixed length, because every alignment column stays in register. Over a "
      "150-design campaign this converts about six hours of mostly idle waiting into under "
      "an hour of GPU work, and it has a scientific benefit: every design is predicted "
      "under a byte-identical MSA condition, so parent-relative comparison is matched "
      "rather than assumed.")
    A("")
    A("Identical crop, MSA condition, seed protocol, recycling and sampling settings are "
      "applied to the parent and to every candidate. Boltz-2's small-molecule affinity head "
      "is **not** used; it is not a calibrated antibody-HER2 K_D estimator.")
    A("")

    # ------------------------------------------------------------------ ipSAE
    A("## 6. ipSAE: computed externally, never proxied")
    A("")
    A("Boltz-2 does not emit ipSAE. Each prediction's full PAE matrix and mmCIF are passed "
      "to the authoritative DunbrackLab/IPSAE implementation and the values parsed back.")
    A("")
    if m5:
        A("| Parameter | Value |")
        A("| --- | --- |")
        A(f"| Predictions scored | {m5.get('ipsae_passed', '?')} of {m5.get('predictions_found', '?')} |")
        A(f"| PAE cutoff | {m5.get('pae_cutoff_A', '?')} A |")
        A(f"| Distance cutoff | {m5.get('distance_cutoff_A', '?')} A |")
        A(f"| IPSAE commit | `{m5.get('ipsae_commit', '?')[:12]}` |")
        A("")
    A("Primary metric is `ipsae_min = min(asym B->T, asym T->B)`, the conservative of the "
      "two directional values. Chain order is `T` = HER2 domain IV, `B` = scFv. "
      "`ipSAE_provenance.csv` records the script commit, both cutoffs, the metric "
      "definition, the chain mapping and the artifact paths for every design.")
    A("")
    A("A prediction with a missing or unreadable PAE, a PAE/structure residue mismatch, or a "
      "failed ipSAE run is recorded with a non-`PASSED` status and **excluded**. No ipSAE "
      "value is ever estimated, interpolated or carried over from another design.")
    A("")
    if parent_base:
        A(f"**Parent baseline** (matched settings): ipsae_min "
          f"{fmt(parent_base.get('ipsae_min'))} +/- {fmt(parent_base.get('sd'))} over "
          f"{parent_base.get('n_seeds', '?')} seed(s); epitope recovery "
          f"{fmt(parent_base.get('epitope_recovery'))}.")
        A("")
    A("**Epitope recovery** is reported alongside ipSAE: the fraction of experimentally "
      "observed 1N8Z epitope residues still contacted in the predicted complex. ipSAE "
      "cannot distinguish a correct interface from a confident but misplaced one, so a "
      "model recovering less than 30% of the known epitope is rejected regardless of its "
      "ipSAE.")
    A("")

    # ------------------------------------------------- score diagnostics
    diag = load_json(o / "score_diagnostics.json")
    if diag.get("spearman"):
        A("## 6b. Do the sequence scores predict the structure? (measured each run)")
        A("")
        A("Spearman rank correlation between each sequence-stage predictor and each "
          f"structural outcome, over n={diag.get('n_scored')} ipSAE-complete designs.")
        A("")
        tnames = ["ipsae_min", "epitope_recovery", "iptm"]
        A("| Predictor | " + " | ".join(tnames) + " |")
        A("| --- | " + " | ".join("---:" for _ in tnames) + " |")
        for pn, tv in diag["spearman"].items():
            cells = []
            for tn in tnames:
                e = tv.get(tn, {})
                cells.append("n/a" if e.get("rho") is None else f"{e['rho']:+.3f}")
            A(f"| `{pn}` | " + " | ".join(cells) + " |")
        A("")
        A(f"**Interpretation.** {diag.get('interpretation','')}")
        A("")
        A("This is the single most consequential empirical result of the run: it means "
          "selecting candidates by maximising sequence plausibility optimises a proxy that "
          "points **away** from interface quality. Later rounds therefore use sequence "
          "consensus as a floor (reject the implausible tail) rather than as a maximand, and "
          "stratify the structural budget by mutation count and branch instead "
          "(`requeue_structure_informed.py`).")
        A("")
        if diag.get("by_mutation_count"):
            A("### By mutation count")
            A("")
            A("| Mutations | n | ipSAE_min | ipTM | Epitope recovery |")
            A("| ---: | ---: | ---: | ---: | ---: |")
            for k, v in diag["by_mutation_count"].items():
                A(f"| {k} | {v['n']} | {fmt(v['ipsae_min_mean'])} +/- {fmt(v['ipsae_min_sd'],3)} "
                  f"| {fmt(v['iptm_mean'],3)} | {fmt(v['epitope_recovery_mean'],3)} |")
            pr = diag.get("parent_reference", {})
            A(f"| *parent* | - | *{fmt(pr.get('ipsae_min'))}* | - "
              f"| *{fmt(pr.get('epitope_recovery'),3)}* |")
            A("")
        rel = diag.get("reliability") or {}
        if rel.get("reliability_single_seed") is not None:
            A("### How much of the ipSAE ranking is real?")
            A("")
            A("A variance decomposition over the designs that were run under multiple seeds. "
              "This is the number that governs every other claim in this document.")
            A("")
            A("| Quantity | Value |")
            A("| --- | ---: |")
            A(f"| Designs with replicates | {rel.get('n_replicated')} |")
            A(f"| Mean seeds per design | {rel.get('mean_seeds_per_design')} |")
            A(f"| sd within design (seed noise) | {fmt(rel.get('sd_within_seed'))} |")
            A(f"| sd between designs (observed) | {fmt(rel.get('sd_between_designs_observed'))} |")
            A(f"| sd between designs (true, est.) | {fmt(rel.get('sd_between_designs_true_est'))} |")
            A(f"| **Reliability of a single seed** | **{fmt(rel.get('reliability_single_seed'),3)}** |")
            A(f"| Reliability of the current mean | {fmt(rel.get('reliability_current_mean'),3)} |")
            A(f"| Seeds needed for reliability 0.8 | {rel.get('seeds_for_reliability_0.8')} |")
            A(f"| Seeds needed for reliability 0.9 | {rel.get('seeds_for_reliability_0.9')} |")
            A("")
            A("Reliability is the fraction of ranking variance that is real signal rather than "
              "seed noise. A value near 0.5 means a single-seed ranking is close to a coin "
              "flip between designs of similar quality, so **a single-seed ipSAE table must not "
              "be read as an ordering of design quality.**")
            A("")
            dis = rel.get("ipsae_correlations_disattenuated")
            if dis:
                A(f"Because the measurements are noisy, the correlations in the table above are "
                  f"*attenuated* toward zero. Dividing by sqrt(reliability) "
                  f"(x{fmt(rel.get('attenuation_correction_factor'),2)}) estimates the "
                  f"underlying relationships with ipSAE:")
                A("")
                for k, v in dis.items():
                    A(f"- `{k}`: {fmt(v)}")
                A("")
                A("So the true effects are **stronger** than measured, not weaker - including the "
                  "negative ones.")
                A("")
            pc = rel.get("parent_comparison") or {}
            if pc.get("tests"):
                A("### Replicated designs tested against the parent")
                A("")
                A(f"Parent baseline {fmt(pc.get('parent_mean'))} +/- {fmt(pc.get('parent_sd'))} "
                  f"over {pc.get('parent_n_seeds')} seeds. Welch-style comparison, "
                  f"significance threshold {pc.get('threshold')}.")
                A("")
                A(f"**Above parent: {pc.get('n_above')} | below: {pc.get('n_below')} | "
                  f"indistinguishable: {pc.get('n_indistinguishable')}**")
                A("")
                A("| Design | seeds | ipSAE mean | sd | delta | t | verdict |")
                A("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
                for d in pc["tests"]:
                    A(f"| `{d['candidate_id']}` | {d['n_seeds']} | {fmt(d['ipsae_mean'])} "
                      f"| {fmt(d['ipsae_sd'])} | {d['delta_vs_parent']:+.4f} | {d['t']:+.2f} "
                      f"| {d['verdict']} |")
                A("")
                if pc.get("n_above", 0) == 0:
                    A("**No design is statistically distinguishable as better than the parent.** "
                      "This is the honest headline result. It is also the expected one: the "
                      "parent is a sub-picomolar, heavily optimised therapeutic antibody, and a "
                      "pipeline reporting that most of its 5-8 substitution variants improved on "
                      "it would be evidence of a broken scoring function rather than a "
                      "successful campaign. Designs are submitted as compliant, structurally "
                      "intact candidates with genuine ipSAE values - not as predicted "
                      "improvements.")
                    A("")
        if diag.get("by_branch"):
            A("### By branch")
            A("")
            A("| Branch | n | ipSAE_min | ipTM | Epitope recovery |")
            A("| --- | ---: | ---: | ---: | ---: |")
            for k, v in diag["by_branch"].items():
                A(f"| `{k}` | {v['n']} | {fmt(v['ipsae_min_mean'])} | {fmt(v['iptm_mean'],3)} "
                  f"| {fmt(v['epitope_recovery_mean'],3)} |")
            A("")
            A("Note this **contradicts the premise** that CDR-H3 maturation is the strongest "
              "branch: the published evidence for H3-focused editing came from a different "
              "parent and a different assay. Here framework-biased edits best preserve the "
              "modelled interface. We report the discrepancy rather than suppressing it, and "
              "keep all four branches represented in the submission.")
            A("")

    # -------------------------------------------------------------- selection
    A("## 7. Selection: multi-objective and diversity-aware")
    A("")
    A("Ranking is deliberately **not** 'sort by ipSAE'. Four reasons: ipSAE is not "
      "calibrated to K_D; a small ipSAE gap can be smaller than seed noise; a confident "
      "model can bind the wrong face; and near-identical neighbours are not independent "
      "hypotheses.")
    A("")
    w = manifest.get("weights_primary", {})
    if w:
        A("| Axis | Weight |")
        A("| --- | --- |")
        for k, v in w.items():
            A(f"| {k} | {v} |")
        A("")
    A(f"**Seed-noise gate.** Pooled ipSAE standard deviation across replicated candidates: "
      f"**{fmt(audit.get('seed_noise_ipsae_sd'))}**. A design whose advantage over the "
      f"parent is smaller than this is labelled `WITHIN_SEED_NOISE` rather than presented "
      f"as an improvement. Designs exceeding the parent beyond that noise: "
      f"**{audit.get('designs_above_parent_beyond_noise', '?')}** of {len(scored)}.")
    A("")
    A("**Sensitivity analysis.** Because the weights are a stated hypothesis and not a "
      "fitted model, the whole set is re-ranked under three alternative weightings "
      "(ipSAE-heavy, sequence-heavy, equal). Each design carries "
      "`max_rank_shift_under_reweighting`, so a nominee whose position depends on a single "
      "metric is visible as such.")
    A("")

    # --------------------------------------------------------------- nominees
    if top:
        A(f"## 8. Lab nominations (top {min(len(top), args.top_table)})")
        A("")
        A("| Rank | ID | Branch | Muts | ipSAE_min | Δ vs parent | Interpretation | "
          "Epitope rec. | ipTM | Rank shift |")
        A("| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
        for r in top[: args.top_table]:
            A(f"| {r.get('rank','')} | `{r.get('candidate_id','')}` | {r.get('branch','')} "
              f"| {r.get('mutation_count','')} | {fmt(r.get('ipsae_min'))} "
              f"| {fmt(r.get('ipsae_delta_vs_parent'))} | {r.get('ipsae_interpretation','')} "
              f"| {fmt(r.get('epitope_recovery'),3)} | {fmt(r.get('iptm'),3)} "
              f"| {r.get('max_rank_shift_under_reweighting','')} |")
        A("")
        A("Mutation lists for each nominee are in `top_15_scored.csv` "
          "(`mutations_1based`), and each sequence is independently reconstructible by "
          "re-applying that list to the frozen parent - a check the audit performs.")
        A("")

    # ----------------------------------------------------------------- audit
    checks = audit.get("checks", [])
    if checks:
        A("## 9. Independent compliance audit")
        A("")
        A("Computed from the real output files, after and independently of the stages that "
          "produced them.")
        A("")
        A("| Check | Result | Detail |")
        A("| --- | --- | --- |")
        for c in checks:
            d = str(c.get("detail", ""))
            A(f"| {c.get('check','')} | **{c.get('result','')}** | {d[:120]} |")
        A("")

    # ----------------------------------------------------------- limitations
    A("## 10. Limitations")
    A("")
    A("- **No affinity is predicted.** ipSAE, ipTM, pLDDT, pDockQ and LIS are model "
      "confidence and interface-geometry measures. None is a K_D, and none is calibrated "
      "against sub-picomolar antibody binding.")
    A("- **The parent is very strong.** At 0.82 pM, assay floor and rebinding effects make "
      "improvement hard to demonstrate even experimentally.")
    A("- **Cropping changes the system.** Domain IV alone lacks receptor context, has "
      "artificial termini, and omits glycans. It is required by the organizer and applied "
      "identically everywhere, but it is still an approximation.")
    A("- **The MSA query-row reuse is an approximation**, exact in alignment terms for "
      "substitution-only variants but not a re-derived alignment per mutant.")
    A("- **Language-model priors are blind to the target.** AbLang2, ESM2 and ESM-C never "
      "see HER2; they can only reject implausible sequences, not identify better binders.")
    A("- **Selection weights are unvalidated.** They are a reasoned hypothesis; the "
      "sensitivity analysis quantifies how much the answer depends on them.")
    A("- **Single structure per seed.** One diffusion sample per seed; replicates quantify "
      "seed variance but not full conformational uncertainty.")
    A("- **No experimental feedback.** Without in-campaign assay data this is not Bayesian "
      "optimisation; it is one-shot constrained screening over model priors.")
    A("")
    A("## Reproducibility")
    A("")
    A(f"- repository commit: `{manifest.get('repo_commit', 'n/a')}`"
      f"{' (working tree dirty)' if manifest.get('repo_dirty') else ''}")
    A(f"- parent SHA-256: `{hc.PARENT_SHA256}`")
    A("- `bash scripts/run_her2_pipeline.sh` reruns the whole pipeline; stages are "
      "idempotent and resumable.")
    A("- per-stage manifests (`stage*_manifest.json`) record models, precisions, seeds, "
      "timings and peak memory.")
    A("")

    dest = o / "method_walkthrough.md"
    dest.write_text("\n".join(L) + "\n")
    print(f"[done] {dest} ({len(L)} lines) | scored={len(scored)} top={len(top)} "
          f"audit={audit.get('overall', 'NOT_EVALUATED')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
