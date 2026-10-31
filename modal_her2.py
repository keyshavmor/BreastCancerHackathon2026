import modal

app = modal.App("her2-scfv-pipeline")

image = (
    modal.Image.from_registry(
        "continuumio/miniconda3:latest",
        add_python=None,
    )
    .apt_install("git", "wget", "build-essential")
    .run_commands(
        "git clone --branch sarah-her2 https://github.com/keyshavmor/BreastCancerHackathon2026.git /pipeline",
        "cd /pipeline && conda env create -f envs/her2_seq.yml",
        "cd /pipeline && conda env create -f envs/her2_boltz2.yml",
    )
)

model_cache = modal.Volume.from_name("her2-models", create_if_missing=True)
outputs_vol = modal.Volume.from_name("her2-outputs", create_if_missing=True)

@app.function(
    image=image,
    gpu="A10G",
    timeout=4 * 60 * 60,
    memory=32768,
    cpu=8.0,
    volumes={
        "/root/.cache": model_cache,
        "/pipeline/outputs": outputs_vol,
    },
)
def run_pipeline(smoke: bool = False, from_stage: int | None = None):
    import subprocess, os
    env = os.environ.copy()
    env["PATH"] = "/opt/conda/bin:" + env.get("PATH", "")
    env["CONDA_ROOT"] = "/opt/conda"
    env["SEQ_ENV"] = "her2_seq"
    env["BOLTZ_ENV"] = "her2_boltz2"
    if smoke:
        env["SMOKE"] = "1"
    if from_stage is not None:
        env["FROM"] = str(from_stage)
    subprocess.run(
        ["bash", "scripts/run_her2_pipeline.sh"],
        cwd="/pipeline",
        env=env,
        check=True,
    )

@app.local_entrypoint()
def main(smoke: bool = False, from_stage: int = 0):
    run_pipeline.remote(smoke=smoke, from_stage=from_stage or None)