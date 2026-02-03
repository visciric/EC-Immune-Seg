# Source Code

This directory contains the core Python implementation for the project. While the `scripts/` folder handles orchestration (SLURM job submission), this folder contains the actual logic for data manipulation, image analysis, and visualization.

## Prerequisites

**Environment Activation**
All scripts in this directory require the project's Python environment to be active.

```bash
conda activate ec_env
```

## Directory Structure

```
src/
 ├── dataset_processing/    # Data management, list generation, and CSV aggregation
 └── image_processing/      # Visualization engine, heatmap generation, and result parsing
```

## 1\. Dataset Processing (`src/dataset_processing/`)

**Purpose:** Tools for managing input data (clinical lists) and aggregating output data (CSVs).

  * **Input Management:** Scripts like `create_image_list.py` generate the input CSVs required for the inference pipeline by filtering clinical data.
  * **Result Aggregation:** `combine_tiles_csv.py` merges thousands of individual tile CSVs into a single master dataset for machine learning.
  * **Utilities:** `csv_operations.py` handles splitting and merging large files for storage or transfer.

## 2\. Image Processing (`src/image_processing/`)

**Purpose:** The core visualization library. These modules convert raw model outputs (JSON coordinates or Masks) into visual and statistical formats.

  * **Pipeline Core:** `main.py` is the workhorse script called by the SLURM jobs to generate **Heatmaps** and **Tile Data CSVs**.
  * **Visualization:** Dedicated scripts (`visualize_tile_hovernet.py`, `visualize_hovernext.py`) allow for high-resolution inspection of specific tiles, drawing boundaries and centroids on top of the original WSI.
  * **Library:** Contains helper modules (`heatmap.py`, `io_utils.py`, `constants.py`) that handle the logic for reading OpenSlide images, parsing complex JSON/Zarr structures, and defining colormaps.


## How these interact with `scripts/`

Usually, you do not need to run files in `src/` directly. They are automatically called by the batch scripts in the main `scripts/` folder.

**Example Flow:**

1.  `scripts/inference/hovernet_a100.sh` runs the model.
2.  `scripts/processing/process_heatmap.sh` calls **`src/image_processing/main.py`** to visualize results.
3.  `scripts/preprocessing/combine_csv.sh` calls **`src/dataset_processing/combine_tiles_csv.py`** to merge the data.
