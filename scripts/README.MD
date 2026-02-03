# Project Scripts Overview

This document provides a comprehensive guide to the `scripts/` directory, which contains the complete workflow for the tumor segmentation project,from data preprocessing and model inference to visualization and downstream analysis.

## Prerequisites (Read First)

**Environment Activation is Mandatory**
Before submitting **any** job in this folder or its subfolders, you must ensure your Python/Conda environment is active in the command line.

```bash
# Example
conda activate ec_env
```

## Directory Structure

```
scripts/
 ├── inference/         # Model execution (HoverNet/HoverNeXT)
 ├── processing/        # Post-inference (Heatmaps & CSV extraction)
 ├── preprocessing/     # CSV data management (Split/Merge/Combine)
 ├── visualization/     # Tile-level visualization tools
 ├── machine_learning/  # Downstream analysis & training
 ├── clustering/        # Unsupervised clustering
 ├── create_links/      # Symlink management for input data
 └── utils/             # Helper scripts (Status checks, Zipping)
```


## 1\. Inference (`inference/`)

Contains SLURM batch scripts to run tumor segmentation models. Scripts are specialized by model type and GPU architecture (A100 vs L40s).

**Key Scripts:**

  * `hovernet_a100.sh` / `hovernet_l40s.sh`
  * `hovernext_a100.sh` / `hovernext_l40s.sh`

**Configuration:**
To avoid GPU resource conflicts and process data in chunks, you can configure these variables inside the scripts:

  * `BATCH_ID`: Unique identifier for the run.
  * `MAX_NEW_IMAGES`: Limit the number of images processed per job.
  * `SKIP_IMAGES`: Skip $N$ images (useful for parallel batches).

**Usage:**

```bash
sbatch inference/hovernet_a100.sh
```


## 2\. Processing (`processing/`)

Scripts for converting raw inference outputs (JSON) into usable formats: **Heatmaps** and **Tile Data CSVs**.

### Main Scripts

  * **`process_heatmap.sh` (Batch Mode):**
      * Designed for bulk processing using SLURM arrays.
      * **Modes:** `csv` (data only), `heatmap` (image only), or `both`.
      * **Config:** Adjust `TILE_SIZE`, `WSI_ALPHA`, and `COLORMAP` (e.g., `green_yellow_red`, `colorblind_safe`).
  * **`process_heatmap_csv.sh` / `process_heatmap_list.sh`:**
      * Target specific cases (manual list, first $N$, or random $N$) for debugging or publication figures.

**Usage:**

```bash
# Edit the script to set MODE and Array range first
sbatch processing/process_heatmap.sh
```


## 3\. Preprocessing (`preprocessing/`)

Tools for managing large CSV datasets (clinical data or tile summaries).

  * **`combine_csv.sh`:**
      * Merges processed tile CSVs from multiple inference batches into a single dataset.
      * *Config:* Uncomment the specific biomarker section (MSI-H, TMB-H, etc.) before running.
  * **`split_csv.sh`:**
      * Splits large CSVs into smaller chunks (useful for GitHub storage or backup).
      * *Usage:* `sbatch split_csv.sbatch <input.csv> [output_prefix]`
  * **`merge_csv.sh`:**
      * The inverse of split; recombines chunked CSVs.
      * *Usage:* `sbatch merge_csv.sbatch <file1.csv> <file2.csv> <output.csv>`


## 4\. Visualization (`visualization/`)

Scripts to visualize specific regions or tiles based on cell counts. Useful for Quality Control (QC) or generating figures.

**Script:** `visualize_hovernet_tiles.sh`

  * **Function:** Locates top tiles based on a specific cell type count, extracts the image, and draws nuclei boundaries (from JSON, no mask needed).

**Usage:**

```bash
# Syntax: sbatch script.sh CASE_NAME <cell_type> <num_tiles>
sbatch visualization/visualize_hovernet_tiles.sh TCGA-XXXX inflammatory 5
```


## 5\. Utilities (`utils/`)

General maintenance and status check scripts.

  * **`check_unprocessed_*.sh`:**
      * Verifies if images in your list have corresponding JSON outputs.
      * Generates `complete.txt`, `incomplete.txt`, and `reprocess.txt` to help identify failed jobs.
      * *Usage:* `bash utils/check_unprocessed_hovernet.sh`
  * **`zip_folders.sh`:**
      * Compresses large result directories or CSV folders for export.


## Common Workflows

### A. Complete Processing Pipeline

1.  **Run Inference:**
    ```bash
    sbatch inference/hovernet_a100.sh
    ```
2.  **Verify Completion:**
    ```bash
    bash utils/check_unprocessed_hovernet.sh
    ```
3.  **Combine Results:**
    ```bash
    sbatch preprocessing/combine_csv.sh
    ```
4.  **Generate Visuals/Data:**
    ```bash
    sbatch processing/process_heatmap.sh
    ```

### B. Parallel Processing Strategy

To run multiple inference jobs simultaneously without processing the same image twice:

1.  **Job 1:** Set `BATCH_ID="batch1"`, `MAX_NEW_IMAGES=20`, `SKIP_IMAGES=0`
2.  **Job 2:** Set `BATCH_ID="batch2"`, `MAX_NEW_IMAGES=20`, `SKIP_IMAGES=20`
3.  Submit Job 1 to `hovernet_a100.sh` and Job 2 to `hovernet_l40s.sh`.