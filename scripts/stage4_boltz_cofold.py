#!/usr/bin/env python
"""Stage 4 - Boltz-2 cofolding of scFv candidates against HER2 domain IV.

Throughput design
-----------------
Three decisions make 100+ structures affordable on one 24 GB GPU:

1. **Domain IV only.** 242 + 119 = 361 residues instead of ~849 for the full
   ectodomain. The organizer forbids full-ECD cofolding anyway, and the measured
   parent run is ~51 s wall-clock including cold model load.
2. **Cached MSAs.** The MSA server costs ~103 s per *target* and is the single
   largest avoidable cost - over 100 designs that alone would be ~3 hours. We
   call the server once for the parent, then reuse those alignments. Because our
   policy is substitution-only at fixed length 242, the alignment columns stay
   valid; we rewrite only row 0 (the query) to the candidate's sequence so the
   profile is exact. Every candidate therefore gets an *identical* MSA
   condition, which also makes parent-relative comparisons matched by
   construction.
3. **Batched invocation.** One ``boltz predict`` call over a directory of YAMLs
   pays model load once instead of once per structure.

Every run writes a full PAE matrix (``--write_full_pae``) and an mmCIF, which
stage 5 feeds to the external DunbrackLab ipSAE implementation. A design with no
structure or no PAE is never scored and never submitted.

Resume is safe: an existing ``<name>_model_0.cif`` plus its PAE file is treated
as complete and skipped, so an interrupted run continues where it stopped.

Run:
    python stage4_boltz_cofold.py --limit 50 --batch-size 10
    python stage4_boltz_cofold.py --replicate-top 20 --seeds 1,2,3
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import her2_common as hc

BOLTZ_BIN = Path.home() / "anaconda3" / "envs" / "her2_boltz2" / "bin" / "boltz"


def read_msa_csv(path: Path) -> list[tuple[str, str]]:
    """Read a Boltz MSA csv (``key,sequence``) into a list of rows."""
    with open(path) as fh:
        r = csv.reader(fh)
        header = next(r)
        if header[:2] != ["key", "sequence"]:
            raise ValueError(f"unexpected MSA header {header} in {path}")
        return [(row[0], row[1]) for row in r if row]


def write_retargeted_msa(rows: list[tuple[str, str]], query: str, dest: Path) -> None:
    """Write an MSA whose query row is ``query`` and whose homologs are unchanged.

    Only valid for equal-length substitution-only variants, which the validator
    has already guaranteed; the gapless query row keeps every alignment column
    in register.
    """
    if len(rows[0][1]) != len(query):
        raise ValueError(f"query length {len(query)} != MSA row0 length {len(rows[0][1])}")
    with open(dest, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "sequence"])
        w.writerow([rows[0][0], query])
        w.writerows(rows[1:])


def write_yaml(dest: Path, target_seq: str, binder_seq: str,
               target_msa: Path | str | None, binder_msa: Path | str | None) -> None:
    """Emit a two-chain Boltz YAML: chain T = HER2 domain IV, chain B = scFv.

    A ``None`` msa omits the key entirely, which is what ``--msa-mode fresh``
    needs so that Boltz computes the alignment itself via the MSA server.
    """
    def msa_line(v) -> str:
        return "" if v is None else f"      msa: {v}\n"
    dest.write_text(
        "version: 1\n"
        "sequences:\n"
        "  - protein:\n"
        "      id: T\n"
        f"      sequence: {target_seq}\n" + msa_line(target_msa) +
        "  - protein:\n"
        "      id: B\n"
        f"      sequence: {binder_seq}\n" + msa_line(binder_msa)
    )


def is_complete(out_dir: Path, name: str) -> bool:
    """True if this prediction already has both a structure and a PAE matrix.

    Boltz names its result directory after the *input* it was given, so a
    batched run over ``yamls/seed42_batch000/`` writes to
    ``boltz_results_seed42_batch000/predictions/<name>/``. We therefore search
    across all result directories rather than assuming one per structure.
    """
    for pred in out_dir.glob(f"boltz_results_*/predictions/{name}"):
        if (pred / f"{name}_model_0.cif").is_file() and (pred / f"pae_{name}_model_0.npz").is_file():
            return True
    return False


def run_batch(yaml_dir: Path, out_dir: Path, seed: int, args) -> tuple[int, float]:
    """Invoke boltz once over a directory of YAMLs. Returns (returncode, seconds)."""
    cmd = [
        str(BOLTZ_BIN), "predict", str(yaml_dir),
        "--out_dir", str(out_dir),
        "--cache", str(Path(args.cache).expanduser()),
        "--diffusion_samples", str(args.diffusion_samples),
        "--recycling_steps", str(args.recycling_steps),
        "--sampling_steps", str(args.sampling_steps),
        "--output_format", "mmcif",
        "--write_full_pae",
        "--seed", str(seed),
        "--num_workers", str(args.num_workers),
        "--preprocessing-threads", str(args.preprocessing_threads),
        "--accelerator", "gpu",
    ]
    if args.no_kernels:
        cmd.append("--no_kernels")
    if args.msa_mode == "fresh":
        # Let Boltz derive a genuine alignment for each candidate's own sequence.
        cmd.append("--use_msa_server")
    log = out_dir / f"boltz_batch_seed{seed}.log"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log, "a") as fh:
        fh.write(f"\n=== {datetime.now(timezone.utc).isoformat()} :: {' '.join(cmd)} ===\n")
        fh.flush()
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    return rc, time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    base = here.parent
    ap.add_argument("--queue", type=Path, default=base / "outputs" / "priority_cofold_queue.csv")
    ap.add_argument("--target-fasta", type=Path, default=base / "outputs" / "her2_domain_iv.fasta")
    ap.add_argument("--msa-dir", type=Path, default=base / "outputs" / "msa_cache")
    ap.add_argument("--run-dir", type=Path, default=base / "pipeline_runs" / "her2_cofold")
    ap.add_argument("--limit", type=int, default=50, help="candidates to cofold (queue order)")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--seeds", default="42", help="comma-separated seeds for the main pass")
    ap.add_argument("--replicate-top", type=int, default=0,
                    help="additionally re-run the top N queue entries under every seed")
    ap.add_argument("--skip-parent", action="store_true")
    ap.add_argument("--msa-mode", choices=["retarget", "share", "empty", "fresh"],
                    default="retarget",
                    help="retarget: per-candidate query row (default); share: reuse parent MSA "
                         "verbatim; empty: single-sequence mode (documented lower-confidence); "
                         "fresh: one MSA-server call PER candidate. 'fresh' is the control for "
                         "the MSA-reuse confound - under reuse, a design further from the parent "
                         "has weaker homolog support at more columns, which can masquerade as a "
                         "mutation-count effect on confidence. ~100 s/design, so use it on a "
                         "small matched subset, not a campaign.")
    ap.add_argument("--cache", default="~/.boltz")
    ap.add_argument("--diffusion-samples", type=int, default=1)
    ap.add_argument("--recycling-steps", type=int, default=3)
    ap.add_argument("--sampling-steps", type=int, default=200)
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument("--preprocessing-threads", type=int, default=4)
    ap.add_argument("--no-kernels", action="store_true")
    ap.add_argument("--time-budget-min", type=float, default=0.0,
                    help="stop launching new batches after this many minutes (0 = unlimited)")
    args = ap.parse_args()

    hc.assert_parent_integrity()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in str(args.seeds).split(",") if str(s).strip()]

    target_seq = next(iter(hc.read_fasta(args.target_fasta).values()))
    target_msa_src = args.msa_dir / "her2_domain_iv.csv"
    binder_msa_src = args.msa_dir / "scfv_parent.csv"
    use_msa = args.msa_mode not in ("empty", "fresh")
    if use_msa:
        for p in (target_msa_src, binder_msa_src):
            if not p.is_file():
                raise SystemExit(f"missing cached MSA {p}; run the parent with --use_msa_server first")
        binder_rows = read_msa_csv(binder_msa_src)
        print(f"[msa] cached target MSA and {len(binder_rows)} binder rows, mode={args.msa_mode}")

    with open(args.queue) as fh:
        queue = list(csv.DictReader(fh))
    jobs = queue[: args.limit] if args.limit else queue
    print(f"[queue] {len(jobs)} candidates selected from {len(queue)} (order preserved)")

    msa_dir = args.run_dir / "msa_per_candidate"
    msa_dir.mkdir(parents=True, exist_ok=True)

    # ---- parent baseline, same settings, one per seed ---------------------- #
    plan: list[tuple[str, str, int]] = []   # (name, sequence, seed)
    if not args.skip_parent:
        for s in seeds:
            plan.append((f"parent_seed{s}", hc.PARENT_SEQ, s))

    main_seed = seeds[0]
    for j in jobs:
        plan.append((f"{j['candidate_id']}_seed{main_seed}", j["full_scfv_sequence"], main_seed))
    if args.replicate_top > 0 and len(seeds) > 1:
        for j in jobs[: args.replicate_top]:
            for s in seeds[1:]:
                plan.append((f"{j['candidate_id']}_seed{s}", j["full_scfv_sequence"], s))

    print(f"[plan] {len(plan)} boltz runs "
          f"({len(seeds)} seed(s), replicate_top={args.replicate_top})")

    # ---- group by seed, batch, execute ------------------------------------ #
    out_root = args.run_dir / "out"
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict] = []
    t_start = time.time()
    done = skipped = failed = 0

    by_seed: dict[int, list[tuple[str, str]]] = {}
    for name, seq, seed in plan:
        by_seed.setdefault(seed, []).append((name, seq))

    for seed, items in by_seed.items():
        pending = [(n, s) for n, s in items if not is_complete(out_root, n)]
        skipped += len(items) - len(pending)
        for i in range(0, len(pending), args.batch_size):
            if args.time_budget_min and (time.time() - t_start) / 60 > args.time_budget_min:
                print(f"[budget] {args.time_budget_min} min exhausted; stopping before batch {i//args.batch_size+1}")
                break
            chunk = pending[i : i + args.batch_size]
            bdir = args.run_dir / "yamls" / f"seed{seed}_batch{i//args.batch_size:03d}"
            if bdir.exists():
                shutil.rmtree(bdir)
            bdir.mkdir(parents=True, exist_ok=True)

            for name, seq in chunk:
                if use_msa:
                    if args.msa_mode == "retarget":
                        bm = msa_dir / f"{name}.csv"
                        if not bm.is_file():
                            write_retargeted_msa(binder_rows, seq, bm)
                    else:
                        bm = binder_msa_src
                    tm = target_msa_src
                elif args.msa_mode == "fresh":
                    bm = tm = None          # omitted entirely; boltz queries the server
                else:
                    bm = tm = "empty"
                write_yaml(bdir / f"{name}.yaml", target_seq, seq, tm, bm)

            rc, secs = run_batch(bdir, out_root, seed, args)
            ok = sum(1 for n, _ in chunk if is_complete(out_root, n))
            done += ok
            failed += len(chunk) - ok
            per = secs / max(1, len(chunk))
            print(f"[batch] seed={seed} n={len(chunk)} rc={rc} {secs:.0f}s "
                  f"({per:.1f}s/structure) complete={ok}/{len(chunk)} "
                  f"| cumulative done={done} failed={failed}")
            for name, seq in chunk:
                manifest_rows.append({
                    "name": name, "seed": seed, "complete": is_complete(out_root, name),
                    "batch_seconds": round(secs, 1), "seconds_per_structure": round(per, 1),
                    "sequence_sha256": hc.sha256_seq(seq),
                })

    total_min = (time.time() - t_start) / 60
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runs_planned": len(plan), "completed": done, "skipped_existing": skipped, "failed": failed,
        "total_minutes": round(total_min, 1),
        "mean_seconds_per_structure": round(total_min * 60 / max(1, done), 1) if done else None,
        "boltz_settings": {
            "diffusion_samples": args.diffusion_samples, "recycling_steps": args.recycling_steps,
            "sampling_steps": args.sampling_steps, "seeds": seeds, "no_kernels": args.no_kernels,
            "msa_mode": args.msa_mode, "output_format": "mmcif", "write_full_pae": True,
        },
        "target": {"source": str(args.target_fasta), "length": len(target_seq),
                   "description": "HER2 domain IV crop, mature 489-607"},
        "note": "Identical settings, crop and MSA condition for parent and every candidate.",
    }
    (args.run_dir / "stage4_manifest.json").write_text(json.dumps(manifest, indent=2))
    with open(args.run_dir / "stage4_runs.csv", "w", newline="") as fh:
        if manifest_rows:
            w = csv.DictWriter(fh, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)
    print(f"[done] {done} complete, {skipped} skipped, {failed} failed in {total_min:.1f} min "
          f"-> {args.run_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
