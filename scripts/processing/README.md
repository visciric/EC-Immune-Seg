# Image Processing & Heatmap Generation

This folder contains SLURM batch scripts used to generate heatmaps and extract tile data (CSV) from WSI inference results.

## Important Prerequisites

**Environment Activation Required**
Before submitting any of these jobs, you must ensure your Python environment is installed and activated in the command line.

```bash
# Example
conda activate ec_env
```

## Script Overview

### 1\. `process_heatmap_csv.sh` (Batch Processing)

This script is designed for bulk processing of cases using SLURM arrays. It offers the most flexibility regarding **what** is generated (Heatmap & CSV).

  * **Key Configuration (`MODE`):**
    You can change the `MODE` variable inside the script to one of three options:

      * `"both"`: Generates both the heatmap image and the tile data CSV.
      * `"heatmap"`: Generates only the visualization.
      * `"csv"`: Generates only the data file (useful for statistical analysis without rendering images).

  * **Visual Configuration:**

      * `COLORMAP`: Choose the color scheme (e.g., `"colorblind_safe"`, `"green_yellow_red"`).
      * `TILE_SIZE`: Adjusts the resolution of the processing.

### 2\. `process_heatmap.sh` (Selection Processing)

This script is designed for processing specific subsets of data, such as reproducing images for a publication or testing on a few random cases.

  * **Key Configuration:**
    You must uncomment/edit one of the following sections in the script to determine which images are processed:

      * **Option 1 (`SELECTED_CASES`):** A manual list of specific Case IDs (e.g., for paper figures).
      * **Option 2 (`FIRST_N`):** Processes the first $N$ images found in the directory.
      * **Option 3 (`RANDOM_N`):** Randomly selects $N$ images for testing.

  * **Visual Configuration:**

      * `COLORMAP`: Currently set to `"red_intensity"`, but can be changed to `"blue_intensity"`, `"colorblind_safe"`, etc.

## How to Run

```bash
# Run the bulk processing script 
sbatch process_heatmap_csv.sh

# Run the selection-based script
sbatch process_heatmap.sh
```

### Outputs

  * **Heatmaps:** Saved to `results/.../processed/heatmaps_[COLORMAP]/`
  * **CSVs:** Saved to `results/.../processed/tile_data/`
