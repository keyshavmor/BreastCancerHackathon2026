"""Modal deployment of the HER2 scFv cofolding stage, fanned out across many GPUs.

Why only this stage: generation and ESM reranking are cheap locally (1M AbLang2
candidates in ~200 s; 50k ESM candidates in ~52 min on one 3090). Boltz-2
cofolding is the only stage that is both expensive and **embarrassingly
parallel** - every design is independent - so it is the one worth renting GPUs
for. 150 designs take ~40 min locally; 20 Modal containers do 1,000 in ~15 min.

Design notes that matter for cost
---------------------------------
* **Weights live in a Volume, not the image.** Boltz-2 weights plus the CCD cache
  are ~3 GB. Downloading them per container would dominate the bill, so
  ``populate_cache`` fetches them once into a persistent Volume that every worker
  mounts read-only.
* **Batch per container.** Cold start (container boot + model load) is ~1-2 min
  and is paid per container, not per structure. Each worker therefore processes a
  batch of designs so that overhead is amortised; at batch 1 you would pay more
  for startup than for inference.
* **MSAs are baked into the image.** The pipeline calls the ColabFold MSA server
  exactly once locally (``bootstrap_msa_cache.py``) and reuses the alignments.
  Those CSVs are a few MB, so they ship in the image and no worker ever touches
  the MSA server - which also avoids 1,000 containers rate-limiting it.
* **cuEquivariance is installed explicitly.** ``pip install boltz`` does not pull
  ``cuequivariance_torch``, but Boltz-2 imports it at prediction time. This bit
  us locally; the image pins the cu12 wheels matching the Torch build.

Usage
-----
    pip install modal && modal token new          # one-time

    # one-time, ~3 GB into the Volume (cheap CPU container)
    modal run modal/her2_modal_app.py::populate_cache

    # fan out a queue produced by stage 3 / requeue_structure_informed.py
    modal run modal/her2_modal_app.py \
        --queue outputs/priority_cofold_queue_merged.csv \
        --limit 1000 --batch-size 50 --gpu A10G --seeds 42

    # pull results back for local stage 5/6
    modal volume get her2-boltz-out / ./pipeline_runs/modal_cofold

Then score exactly as for a local run:
    python scripts/stage5_score_ipsae.py --run-dir pipeline_runs/modal_cofold
    python scripts/stage6_select_audit.py --top-n 15

Cost sanity check (verify against current Modal pricing before a big run):
    A10G 24 GB ~ $1.10/GPU-hour. At ~15 s/structure a GPU-hour is ~240
    structures, so ~$0.005 per design and ~$5 per 1,000. A $30 budget is
    therefore thousands of designs, and wall-clock is set by how many containers
    you run in parallel, not by the total.
"""

from __future__ import annotations

import csv
import os
import pathlib
import subprocess
import time

import modal

APP_NAME = "her2-scfv-cofold"
BOLTZ_VERSION = "2.2.1"

# Repo root, so local files can be added to the image at build time.
_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent

app = modal.App(APP_NAME)

# Persistent storage: weights (written once, read by every worker) and outputs.
cache_vol = modal.Volume.from_name("her2-boltz-cache", create_if_missing=True)
out_vol = modal.Volume.from_name("her2-boltz-out", create_if_missing=True)

CACHE_DIR = "/cache"
OUT_DIR = "/out"
ASSET_DIR = "/assets"

# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------
# Torch comes from the boltz wheel's own pin; we add the cuEquivariance kernels
# that boltz needs but does not declare. If a future boltz pins a cu13 torch,
# swap the ops wheel to -cu13 (see envs/README.md for the same gotcha locally).
boltz_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install(
        f"boltz=={BOLTZ_VERSION}",
        "cuequivariance==0.13.0",
        "cuequivariance-torch==0.13.0",
        "cuequivariance-ops-torch-cu12==0.13.0",
        "numpy",
    )
    # Cached MSAs + the domain IV target. Small, and keeps every worker off the
    # MSA server.
    .add_local_dir(_ROOT / "outputs" / "msa_cache", f"{ASSET_DIR}/msa_cache", copy=True)
    .add_local_file(_ROOT / "outputs" / "her2_domain_iv.fasta",
                    f"{ASSET_DIR}/her2_domain_iv.fasta", copy=True)
)

# ipSAE is pure numpy on CPU, so it runs in a cheap container with no GPU.
ipsae_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("numpy")
    .run_commands(
        "git clone --depth 1 https://github.com/DunbrackLab/IPSAE.git /opt/IPSAE"
    )
)


# ---------------------------------------------------------------------------
# One-time cache population
# ---------------------------------------------------------------------------
@app.function(image=boltz_image, volumes={CACHE_DIR: cache_vol}, timeout=3600,
              cpu=4.0, memory=8192)
def populate_cache(force: bool = False) -> dict:
    """Download Boltz-2 weights and the CCD cache into the persistent Volume.

    Run once per Modal workspace. Every cofold worker then mounts this Volume
    instead of re-downloading ~3 GB, which is what keeps the bill proportional to
    GPU time rather than to container count.
    """
    cache = pathlib.Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    conf = cache / "boltz2_conf.ckpt"
    if conf.exists() and not force:
        have = sorted(p.name for p in cache.iterdir())
        return {"status": "already_populated", "entries": have}

    # Use boltz's own downloader rather than triggering it via a dummy
    # prediction: it is the supported entry point, needs no GPU, and cannot fail
    # for an unrelated inference reason.
    t0 = time.time()
    err = ""
    try:
        from boltz.main import download_boltz2

        download_boltz2(cache)
    except Exception as exc:                                     # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"

    # Fallback: a tiny CPU prediction also pulls whatever is still missing.
    if not conf.exists():
        work = pathlib.Path("/tmp/warm")
        work.mkdir(parents=True, exist_ok=True)
        (work / "warm.yaml").write_text(
            "version: 1\nsequences:\n  - protein:\n      id: A\n"
            "      sequence: GGGGSGGGGS\n      msa: empty\n"
        )
        proc = subprocess.run(
            ["boltz", "predict", str(work / "warm.yaml"), "--out_dir", "/tmp/warm_out",
             "--cache", CACHE_DIR, "--accelerator", "cpu", "--diffusion_samples", "1",
             "--recycling_steps", "1", "--sampling_steps", "10"],
            capture_output=True, text=True,
        )
        err = (err + " | fallback_rc=" + str(proc.returncode)
               + " " + proc.stderr[-800:]).strip()

    cache_vol.commit()
    entries = sorted(p.name for p in cache.iterdir())
    mols = cache / "mols"
    return {
        "status": "populated" if conf.exists() else "FAILED",
        "seconds": round(time.time() - t0, 1),
        "conf_ckpt_present": conf.exists(),
        "conf_ckpt_mb": round(conf.stat().st_size / 2**20, 1) if conf.exists() else 0,
        "mols_present": mols.exists(),
        "entries": entries,
        "error": err,
    }


# ---------------------------------------------------------------------------
# Cofold worker
# ---------------------------------------------------------------------------
def _write_retargeted_msa(src: pathlib.Path, query: str, dest: pathlib.Path) -> None:
    """Copy a Boltz MSA csv, replacing only the query row with ``query``.

    Valid because the pipeline is substitution-only at fixed length 242, so every
    alignment column stays in register. Identical to the local stage 4 logic.
    """
    with open(src) as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    if len(body[0][1]) != len(query):
        raise ValueError(f"query length {len(query)} != MSA row0 {len(body[0][1])}")
    with open(dest, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerow([body[0][0], query])
        w.writerows(body[1:])


@app.function(
    image=boltz_image,
    volumes={CACHE_DIR: cache_vol, OUT_DIR: out_vol},
    gpu=os.environ.get("HER2_MODAL_GPU", "A10G"),
    timeout=7200,
    cpu=4.0,
    memory=32768,
    retries=modal.Retries(max_retries=1),
)
def cofold_batch(job: dict) -> dict:
    """Cofold one batch of designs against HER2 domain IV.

    ``job`` = {"batch_id": str, "seed": int, "designs": [{"name","sequence"}, ...],
               "sampling_steps": int, "recycling_steps": int}

    Writes ``<OUT_DIR>/boltz_results_<batch_id>/predictions/<name>/`` containing
    the mmCIF, the full PAE npz and the confidence JSON - the same layout the
    local stage 5 expects, so results drop straight into the existing scorer.
    """
    batch_id = job["batch_id"]
    seed = int(job.get("seed", 42))
    designs = job["designs"]

    assets = pathlib.Path(ASSET_DIR)
    target_seq = "".join(
        l.strip() for l in (assets / "her2_domain_iv.fasta").read_text().splitlines()
        if not l.startswith(">")
    )
    tgt_msa = assets / "msa_cache" / "her2_domain_iv.csv"
    bnd_msa = assets / "msa_cache" / "scfv_parent.csv"

    work = pathlib.Path(f"/tmp/{batch_id}")
    ydir = work / "yamls"
    mdir = work / "msa"
    ydir.mkdir(parents=True, exist_ok=True)
    mdir.mkdir(parents=True, exist_ok=True)

    for d in designs:
        name, seq = d["name"], d["sequence"]
        per = mdir / f"{name}.csv"
        _write_retargeted_msa(bnd_msa, seq, per)
        (ydir / f"{name}.yaml").write_text(
            "version: 1\n"
            "sequences:\n"
            "  - protein:\n      id: T\n"
            f"      sequence: {target_seq}\n      msa: {tgt_msa}\n"
            "  - protein:\n      id: B\n"
            f"      sequence: {seq}\n      msa: {per}\n"
        )

    out_root = pathlib.Path(OUT_DIR)
    out_root.mkdir(parents=True, exist_ok=True)
    cmd = [
        "boltz", "predict", str(ydir),
        "--out_dir", str(out_root),
        "--cache", CACHE_DIR,
        "--diffusion_samples", "1",
        "--recycling_steps", str(job.get("recycling_steps", 3)),
        "--sampling_steps", str(job.get("sampling_steps", 200)),
        "--output_format", "mmcif",
        "--write_full_pae",
        "--seed", str(seed),
        "--num_workers", "2",
        "--preprocessing-threads", "4",
        "--accelerator", "gpu",
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    # Count what actually landed; a batch is only as good as its artifacts.
    done = []
    for d in designs:
        name = d["name"]
        hits = list(out_root.glob(f"boltz_results_*/predictions/{name}/{name}_model_0.cif"))
        paes = list(out_root.glob(f"boltz_results_*/predictions/{name}/pae_{name}_model_0.npz"))
        if hits and paes:
            done.append(name)
    out_vol.commit()

    return {
        "batch_id": batch_id, "seed": seed,
        "requested": len(designs), "completed": len(done),
        "missing": [d["name"] for d in designs if d["name"] not in done],
        "seconds": round(elapsed, 1),
        "seconds_per_structure": round(elapsed / max(1, len(done)), 1) if done else None,
        "returncode": proc.returncode,
        "stderr_tail": "" if proc.returncode == 0 else proc.stderr[-2000:],
    }


# ---------------------------------------------------------------------------
# ipSAE scoring (CPU, parallel, cheap)
# ---------------------------------------------------------------------------
@app.function(image=ipsae_image, volumes={OUT_DIR: out_vol}, timeout=3600,
              cpu=2.0, memory=8192)
def score_ipsae_batch(names: list[str], pae_cutoff: float = 10.0,
                      dist_cutoff: float = 15.0) -> list[dict]:
    """Run DunbrackLab/IPSAE over completed predictions. No GPU needed."""
    out_root = pathlib.Path(OUT_DIR)
    results = []
    for name in names:
        cifs = list(out_root.glob(f"boltz_results_*/predictions/{name}/{name}_model_0.cif"))
        paes = list(out_root.glob(f"boltz_results_*/predictions/{name}/pae_{name}_model_0.npz"))
        if not cifs or not paes:
            results.append({"name": name, "status": "MISSING_ARTIFACTS"})
            continue
        cif, pae = cifs[0], paes[0]
        proc = subprocess.run(
            ["python", "/opt/IPSAE/ipsae.py", str(pae), str(cif),
             str(int(pae_cutoff)), str(int(dist_cutoff))],
            capture_output=True, text=True,
        )
        summary = cif.parent / f"{cif.stem}_{int(pae_cutoff)}_{int(dist_cutoff)}.txt"
        rec: dict = {"name": name, "status": "PASSED" if summary.is_file() else "FAILED",
                     "returncode": proc.returncode}
        if summary.is_file():
            asym = {}
            for line in summary.read_text().splitlines():
                f = line.split()
                if len(f) > 13 and f[4] in ("asym", "max"):
                    try:
                        v = float(f[5])
                    except ValueError:
                        continue
                    if f[4] == "asym":
                        asym[f"{f[0]}{f[1]}"] = v
                    else:
                        rec["ipsae_max"] = v
            rec.update(asym)
            if asym:
                rec["ipsae_min"] = min(asym.values())
        results.append(rec)
    out_vol.commit()
    return results


# ---------------------------------------------------------------------------
# Local entrypoint
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main(queue: str = "outputs/priority_cofold_queue_merged.csv",
         limit: int = 200,
         batch_size: int = 50,
         seeds: str = "42",
         sampling_steps: int = 200,
         recycling_steps: int = 3,
         include_parent: bool = True,
         score: bool = True):
    """Fan a cofold queue out over Modal GPUs, then optionally score with ipSAE.

    Keep ``batch_size`` at a few tens: container cold start is ~1-2 min and is
    paid per container, so tiny batches spend more on startup than on inference.
    """
    parent_seq = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNS"
        "LRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAW"
        "YQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
    )
    qpath = pathlib.Path(queue)
    if not qpath.is_absolute():
        qpath = _ROOT / queue
    with open(qpath) as fh:
        rows = list(csv.DictReader(fh))[:limit]
    print(f"[modal] {len(rows)} designs from {qpath.name}")

    seed_list = [int(s) for s in str(seeds).split(",") if s.strip()]
    jobs: list[dict] = []
    for seed in seed_list:
        designs = [{"name": f"{r['candidate_id']}_seed{seed}",
                    "sequence": r["full_scfv_sequence"]} for r in rows]
        if include_parent:
            designs.insert(0, {"name": f"parent_seed{seed}", "sequence": parent_seq})
        for i in range(0, len(designs), batch_size):
            chunk = designs[i : i + batch_size]
            jobs.append({
                "batch_id": f"seed{seed}_b{i // batch_size:04d}",
                "seed": seed, "designs": chunk,
                "sampling_steps": sampling_steps, "recycling_steps": recycling_steps,
            })

    total = sum(len(j["designs"]) for j in jobs)
    print(f"[modal] {len(jobs)} batches, {total} structures, "
          f"batch_size={batch_size}, seeds={seed_list}")
    print("[modal] run populate_cache first if you have not: "
          "modal run modal/her2_modal_app.py::populate_cache")

    t0 = time.time()
    results = list(cofold_batch.map(jobs, order_outputs=False))
    wall = time.time() - t0

    completed = sum(r["completed"] for r in results)
    failed = [r for r in results if r["returncode"] != 0 or r["missing"]]
    rates = [r["seconds_per_structure"] for r in results if r.get("seconds_per_structure")]
    print(f"\n[modal] {completed}/{total} structures in {wall/60:.1f} min wall-clock")
    if rates:
        print(f"[modal] mean {sum(rates)/len(rates):.1f} s/structure per container; "
              f"effective {wall/max(1,completed):.2f} s/structure with "
              f"{len(jobs)} parallel containers")
    for r in failed:
        print(f"  [FAIL] {r['batch_id']} rc={r['returncode']} missing={len(r['missing'])}")
        if r.get("stderr_tail"):
            print(f"         {r['stderr_tail'][-400:]}")

    if score and completed:
        names = [d["name"] for j in jobs for d in j["designs"]]
        shards = [names[i : i + 50] for i in range(0, len(names), 50)]
        scored = [rec for sh in score_ipsae_batch.map(shards) for rec in sh]
        ok = [s for s in scored if s.get("status") == "PASSED"]
        print(f"\n[modal] ipSAE: {len(ok)}/{len(scored)} scored")
        top = sorted((s for s in ok if "ipsae_min" in s),
                     key=lambda s: -s["ipsae_min"])[:10]
        for s in top:
            print(f"  {s['name']:28s} ipsae_min={s['ipsae_min']:.4f}")

    print("\n[modal] fetch artifacts for local stage 5/6:")
    print("  modal volume get her2-boltz-out / ./pipeline_runs/modal_cofold")
