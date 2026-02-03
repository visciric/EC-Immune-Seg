# Segmenting Tumor Images to Study Immune Cells in Endometrial Cancer

**Project Work 2** | **Bsc Applied Digital Life Sciences** 

**Model:** HoVer-NeXt | **Cluster:** Earth (SLURM) | **Focus:** MSS/TMB-H

## Project Overview

This repository contains the source code and workflow for my project work 2

### The Scientific Problem

Immunotherapy has shown promise in treating Endometrial Cancer (EC), specifically in tumors with High Microsatellite Instability (MSI-H). However, a subset of **Microsatellite Stable (MSS)** tumors also exhibit **High Tumor Mutation Burden (TMB-H)** and may be responsive to treatment.

Currently, the immune microenvironment of this specific MSS/TMB-H subtype is poorly understood.

### Research Goals

1.  **Quantify** immune cell densities within the Tumor Microenvironment (TME).
2.  **Compare** the efficiency of the **HoVer-NeXt** deep learning framework on large-scale Whole Slide Images (WSIs).
3.  **Identify** spatial patterns that distinguish immunotherapy-responsive phenotypes.



## Project Structure

The project is organized to separate raw data, SLURM job scripts, and source code.

```text
.
├── data/                       # Clinical metadata and image lists
│   ├── processed_csv/          # Aggregated results (Case-level stats)
│   └── raw/                    # Input lists (e.g., msi-h_image_list.csv)
├── ec_env.yml                  # Main Conda environment for the project
├── hover_next_inference/       # HoVer-NeXt source code and inference logic
├── hover_net/                  # HoVer-Net source code and inference logic
├── notebooks/                  # Jupyter notebooks
├── results/                    # Output directories for model predictions
├── scripts/                    # SLURM submission scripts (The main entry points)
│   ├── inference/              # Scripts to run HoVer-NeXt on GPUs (A100/L40s)
│   ├── preprocessing/          # CSV splitting and merging
│   ├── processing/             # Heatmap generation logic
│   └── visualization/          # Tile visualization tools
└── src/                        # Core Python modules for image processing
```



## Setup & Requirements

### 1\. HPC Environment

This codebase is optimized for the **Earth Cluster** using the SLURM workload manager.

  * **Storage:** High-performance scratch storage is required.
  * **Compute:** NVIDIA A100 or L40s GPUs are recommended for HoVer-NeXt inference.

### 2\. Data Access

The raw Whole Slide Images (WSIs) are **not** included in this repository due to size.

  * **Raw WSIs:** Located on the cluster at:

    ```
    /cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec/
    ```

  * **Results Archive:**

    ```
    /shared/icls-14042025-cancer-genomics-image-analysis/riccardo_files/
    ```

### 3\. Installation

All dependencies are managed via Conda. Create the environment using `ec_env.yml`:

```bash
# Create the environment
conda env create -f ec_env.yml

# Activate before running any scripts
conda activate ec_env
```



## Usage Pipeline

The workflow consists of three main stages. **Note:** Before submitting any jobs, ensure the file paths in the `.sh` scripts match your user directory.

### Step 1: Inference (HoVer-NeXt)

We utilize **HoVer-NeXt** for faster segmentation. Select the script matching the available GPU partition (A100 or L40s).

**Important:** Open the script below and adjust `INPUT_DIR` and `OUTPUT_DIR` paths to your workspace before running.

```bash
# Submit inference job to A100 partition
sbatch scripts/inference/hovernext_a100.sh

# OR for L40s partition
sbatch scripts/inference/hovernext_l40s.sh
```

### Step 2: Post-Processing & Analysis

Once inference is complete, combine the cell-level data into patient-level statistics and generate spatial visualizations.

**Combine Results:**
aggregates the raw segmentation outputs into a single CSV.

```bash
sbatch scripts/preprocessing/combine_csv.sh
```

**Generate Heatmaps:**
Creates spatial maps of immune cell density.

```bash
sbatch scripts/processing/process_heatmap.sh
```

### Step 3: Exploratory & Statistical Analysis

After heatmaps are generated, the interactive analysis should be run using the Jupyter Notebooks.

  * **Exploratory:** `notebooks/exploratory/exploratory_analysis.ipynb`
  * **Statistical:** `notebooks/statistical_analysis/statistical_analysis.ipynb`

### Step 4: Machine Learning Pipeline

Finally, execute the machine learning workflow to classify tumor subtypes based on the extracted features.

```bash
# 1. Run PCA (Principal Component Analysis)
sbatch scripts/machine_learning/run_pca.sh

# 2. Training (Run this after PCA completes)
sbatch scripts/machine_learning/train.sh

# 3. Evaluation (Run this after training completes)
sbatch scripts/machine_learning/evaluation.sh
```


## Results & Visualization

  * **Inference Results:** Saved in the `results/` directory or the shared `riccardo_files` folder.
  * **Analysis Results:** The results of the exploratory analysis, statistical analysis, and machine learning are contained within their respective folders (e.g., `notebooks/statistical_analysis/images` or `notebooks/machine_learning/ml_results`).

## Troubleshooting

**HoVer-Net vs. HoVer-NeXt**

  * **Recommended:** Use `hover_next_inference` (HoVer-NeXt). It is significantly faster and optimized for this cluster's hardware.

**Path Errors**
If a job fails immediately, check the `.err` log. It is almost always a file path issue. Ensure `/cfs/earth/scratch/visciric/...` is updated to your current user path if you have forked this repo.

