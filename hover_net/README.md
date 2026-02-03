# Running Hover-Net on A100 (HPC)

This guide explains how to set up and run **Hover-Net** on the A100 GPUs available on our HPC cluster (partition: `earth-5`). I was able to run it successfully on a single A100 GPU.

## Environment setup

To create the environment with a CUDA version supported by A100 GPUs:

```bash
conda env create -f env.yml
conda activate hovernet_a100
```

If you run into issues with `env.yml`, you can try an explicit installation from the `env.txt` file:

```bash
conda create --name hovernet_a100 --file env.txt
conda activate hovernet_a100
```

Then install the Python packages with:

```bash
pip install -r requirements.txt
```

---

## Running inference on WSI

You can submit a job using the provided SLURM script:

```bash
sbatch submit_hovernet.sh
```

Make sure to review and edit the script if needed (e.g., input paths, output directory, number of workers, etc.). The `run_wsi.sh` contains the command I used to run Hover-Net on a test slide.

### Notes:
- Each slide took approximately **40–50 minutes**.
- It's likely possible to reduce this time by increasing the number of **workers**.

## Files
- `submit_hovernet.sh` – Example SLURM submission script
- `run_wsi.sh` – The command I used for inference
