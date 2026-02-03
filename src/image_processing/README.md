# Image Processing & Visualization Library

This directory contains the core Python modules used to process inference results, generate heatmaps, extract statistical CSV data, and visualize specific tiles with cell boundaries.

## Prerequisites

**Environment Activation**
Ensure your Python environment with `openslide`, `matplotlib`, `pandas`, and `numpy` is active.

```bash
conda activate ec_env
```

## 1\. Main Processing Script (`main.py`)

This is the primary entry point for batch processing. It auto-detects the input format (HoverNet JSON or HoverNeXT directory) and generates:

1.  **Heatmaps:** Visualization of immune cell density overlaid on the WSI.
2.  **Tile Data CSV:** A dataset containing cell counts per tile.

**Usage:**

```bash
# Run the bulk processing script 
sbatch process_heatmap_csv.sh

# Run the selection-based script
sbatch process_heatmap.sh
```

**Key Arguments:**

  * `--colormap`: Options defined in `constants.py` (`green_yellow_red`, `colorblind_safe`, `red_intensity`, `blue_intensity`).
  * `--magnification`: Overrides auto-detection if provided.
  * `--target_tiles`: Calculates dynamic tile size to reach a specific grid count.

-----

## 2\. Visualization Tools

These scripts are used to inspect specific tiles, drawing cell centroids and segmentation boundaries.

### For Hover-Net & HoVer-NeXt (`visualize_tile_hovernet.py`)

Used for results stored in **JSON** format.

  * **Features:** Efficient JSON caching, centroid plotting, boundary reconstruction from JSON contours.
  * **Usage:**
    ```bash
    # Syntax: sbatch script.sh CASE_NAME <cell_type> <num_tiles>
    sbatch visualization/visualize_hovernet_tiles.sh TCGA-XXXX inflammatory 5X
    sbatch visualization/visualize_hovernext_tiles.sh TCGA-XXXX inflammatory 5X
    ```


## 3\. Library Modules

The functionality is distributed across these helper modules:

| File | Description |
| :--- | :--- |
| **`constants.py`** | **Configuration Hub.** Defines `CELL_TYPES` (Neoplastic=1, Inflammatory=2, etc.), `HEATMAP_COLORMAPS` (RGBA values), and font sizes. |
| **`io_utils.py`** | Handles loading of WSI metadata (OpenSlide) and result parsing (Auto-detects JSON vs. TSV formats). |
| **`heatmap.py`** | Logic for generating the heatmap overlay. Handles WSI thumbnail generation and matplotlib plotting. |
| **`export.py`** | Logic for creating the Tile Dataset CSV. Calculates cell percentages and normalized counts per tile. |
| **`tile_analysis.py`** | Math utilities for calculating tile dimensions and iterating through nuclei data. |

## 4\. Configuration Reference (`constants.py`)

**Cell Types:**

  * 0: `nolabel` (Gray)
  * 1: `neoplastic` (Magenta)
  * 2: `inflammatory` (Green)
  * 3: `connective` (Blue)
  * 4: `necrosis` (Red)
  * 5: `non_neoplastic` (Yellow)

**Available Colormaps:**

  * `green_yellow_red`: Traditional heatmap (Green low, Red high).
  * `colorblind_safe`: Viridis-like spectrum.
  * `red_intensity`: White to Dark Red (Good for overlays).
  * `blue_intensity`: White to Dark Blue.