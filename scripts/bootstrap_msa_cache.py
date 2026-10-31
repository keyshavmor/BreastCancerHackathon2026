#!/usr/bin/env python
"""Bootstrap the MSA cache with a single ColabFold MSA-server call.

This is the one and only network MSA request the pipeline makes. It cofolds the
**parent** scFv against HER2 domain IV with ``--use_msa_server``, then harvests
the two resulting alignments into ``outputs/msa_cache/``:

    her2_domain_iv.csv   alignment for the target chain  (identical for all designs)
    scfv_parent.csv      alignment for the binder chain  (retargeted per design)

Why this matters: the MSA server costs ~103 s per target and is rate-limited.
Paying it once instead of once per candidate is the difference between ~6 hours
and ~50 minutes for a 150-design campaign. Stage 4 reuses these files and
rewrites only the query row of the binder alignment, which is exact for our
substitution-only fixed-length policy and gives every design a byte-identical
MSA condition.

The run also serves as the Gate B benchmark: it reports wall-clock, and leaves a
scored parent baseline that stage 5 can pick up.

Run:
    python bootstrap_msa_cache.py --outdir ../outputs
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

import her2_common as hc

BOLTZ_BIN = Path.home() / "anaconda3" / "envs" / "her2_boltz2" / "bin" / "boltz"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    base = here.parent
    ap.add_argument("--outdir", type=Path, default=base / "outputs")
    ap.add_argument("--work-dir", type=Path, default=base / "pipeline_runs" / "msa_bootstrap")
    ap.add_argument("--target-fasta", type=Path, default=None)
    ap.add_argument("--cache", default="~/.boltz")
    ap.add_argument("--boltz", type=Path, default=BOLTZ_BIN)
    ap.add_argument("--msa-server-url", default=None)
    ap.add_argument("--force", action="store_true", help="refetch even if the cache exists")
    args = ap.parse_args()

    hc.assert_parent_integrity()
    msa_dir = args.outdir / "msa_cache"
    msa_dir.mkdir(parents=True, exist_ok=True)
    tgt_dest, bnd_dest = msa_dir / "her2_domain_iv.csv", msa_dir / "scfv_parent.csv"
    if tgt_dest.is_file() and bnd_dest.is_file() and not args.force:
        print(f"[skip] MSA cache already present in {msa_dir} (use --force to refetch)")
        return 0

    target_fasta = args.target_fasta or (args.outdir / "her2_domain_iv.fasta")
    if not target_fasta.is_file():
        raise SystemExit(f"missing {target_fasta}; run stage1_target_prep.py first")
    target_seq = next(iter(hc.read_fasta(target_fasta).values()))

    args.work_dir.mkdir(parents=True, exist_ok=True)
    yaml_dir = args.work_dir / "yaml"
    yaml_dir.mkdir(exist_ok=True)
    (yaml_dir / "parent.yaml").write_text(
        "version: 1\n"
        "sequences:\n"
        "  - protein:\n      id: T\n"
        f"      sequence: {target_seq}\n"
        "  - protein:\n      id: B\n"
        f"      sequence: {hc.PARENT_SEQ}\n"
    )

    cmd = [str(args.boltz), "predict", str(yaml_dir / "parent.yaml"),
           "--out_dir", str(args.work_dir / "out"),
           "--cache", str(Path(args.cache).expanduser()),
           "--use_msa_server",
           "--diffusion_samples", "1", "--recycling_steps", "3", "--sampling_steps", "200",
           "--output_format", "mmcif", "--write_full_pae", "--seed", "42",
           "--num_workers", "2", "--preprocessing-threads", "4", "--accelerator", "gpu"]
    if args.msa_server_url:
        cmd += ["--msa_server_url", args.msa_server_url]

    print(f"[msa] one MSA-server call for target ({len(target_seq)} aa) + "
          f"parent scFv ({len(hc.PARENT_SEQ)} aa)")
    t0 = time.time()
    log = args.work_dir / "bootstrap.log"
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    secs = time.time() - t0
    print(f"[msa] boltz rc={rc} in {secs:.0f}s (log: {log})")

    # Boltz writes msa/<name>_<entity_index>.csv - entity 0 = chain T, 1 = chain B.
    found = sorted((args.work_dir / "out").glob("boltz_results_*/msa/*.csv"))
    if len(found) < 2:
        raise SystemExit(f"expected 2 MSA csv files, found {len(found)}: {found}\n"
                         f"inspect {log} (MSA server may be rate-limited or unreachable)")
    by_entity = {int(p.stem.rsplit("_", 1)[1]): p for p in found if p.stem.rsplit("_", 1)[1].isdigit()}
    shutil.copy2(by_entity[0], tgt_dest)
    shutil.copy2(by_entity[1], bnd_dest)

    def nrows(p: Path) -> int:
        with open(p) as fh:
            return sum(1 for _ in fh) - 1

    print(f"[cache] {tgt_dest.name}: {nrows(tgt_dest)} rows")
    print(f"[cache] {bnd_dest.name}: {nrows(bnd_dest)} rows")

    # Sanity: the binder alignment's query row must equal the parent, otherwise
    # stage 4's retargeting would silently misalign every candidate.
    with open(bnd_dest) as fh:
        fh.readline()
        q = fh.readline().split(",", 1)[1].strip()
    if q != hc.PARENT_SEQ:
        raise SystemExit("binder MSA query row does not equal the frozen parent; refusing to cache")
    print("[ok] binder MSA query row matches the frozen parent exactly")
    print(f"[done] MSA cache ready in {msa_dir}; stage 4 will make no further server calls")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
