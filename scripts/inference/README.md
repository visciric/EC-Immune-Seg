# Inference Scripts

This folder contains SLURM batch scripts for running tumor segmentation inference using **HoverNet** and **HoverNeXT** models.

## Important Prerequisites

**Before running any script, you must ensure the environment is installed and activated.**

You must activate your conda environment in the command line **before** submitting the job.

```bash
# Example
conda activate ec_env
```

## File Contents

The scripts are divided into two categories based on the model used and the GPU hardware configuration (A100 vs L40s).

### 1\. HoverNet Inference

  * **`hovernet_a100.sh`**

      * **Task:** Runs HoverNet inference on MSI-H data.
      * **Hardware:** Configured for **2x A100 GPUs** (Earth-5 partition).
      * **Details:** Processes images defined in the MSI-H CSV, using `run_infer.py`.

  * **`hovernet_l40s.sh`**

      * **Task:** Runs HoverNet inference on TMB-H data.
      * **Hardware:** Configured for **3x L40s GPUs** (Earth-4 partition).
      * **Details:** Processes images defined in the TMB-H CSV, using `run_infer.py`.

### 2\. HoverNeXT Inference

  * **`hovernext_a100.sh`**

      * **Task:** Runs HoverNeXT inference for MSS/TMB cases (or reprocessing).
      * **Hardware:** Configured for **2x A100 GPUs** (Earth-5 partition).
      * **Details:** Scans for unprocessed images and runs `main.py` from the HoverNeXT directory.

  * **`hovernext_l40s.sh`**

      * **Task:** Runs HoverNeXT inference for MSS/TMB-H cases.
      * **Hardware:** Configured for **3x L40s GPUs** (Earth-4 partition).
      * **Details:** Similar logic to the script above but optimized for the L40s partition.

## How to Run

To submit a job to the cluster, ensure your environment is active and use the `sbatch` command with the appropriate script:

```bash
# For HoverNet on A100
sbatch hovernet_a100.sh

# For HoverNet on L40s
sbatch hovernet_l40s.sh

# For HoverNeXT on A100
sbatch hovernext_a100.sh

# For HoverNeXT on L40s
sbatch hovernext_l40s.sh
```

### Outputs

  * **HoverNet:** Results are saved to `results/msi-h_output_BATCHID` or `tmb_h_output_BATCHID`.
  * **HoverNeXT:** Results are saved to `results/hovernext_output_mss_tmb...`.
  * Logs for resource usage and job status are generated automatically upon job completion.
