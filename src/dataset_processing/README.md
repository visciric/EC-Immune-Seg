Here is the `README.md` for the `src/dataset_processing` folder.

I have also included a specific answer to your question about renaming `filter_tmb_h.py` at the end of the response.

-----

# Dataset Processing Scripts

This directory contains Python scripts for managing datasets, including creating image lists from clinical data, manipulating large CSV files, and aggregating inference results.

## ⚠️ Prerequisites

**Environment Activation**
Ensure your Python environment is active before running these scripts.

```bash
conda activate ec_env
```

## Files & Usage

### 1\. `filter_tmb_h.py` (Image List Generator)

**Purpose:** Scans the clinical data CSV and the file system to create a list of image paths (`.svs`) corresponding to a specific biomarker category (e.g., MSI-H, MSS/TMB-H).

  * **Input:** `ucec_clinical.csv` and a root directory of images.
  * **Output:** A CSV file containing file paths and metadata for the selected cases.

**Usage:**
Currently, you must edit the `CATEGORY` variable inside the script (bottom of the file) to choose which group to process:

```python
if __name__ == "__main__":
    CATEGORY = "MSI-H"  # Change to "MSS/TMB-H" or "MSS/TMB-L" as needed
```

Then run:

```bash
python filter_tmb_h.py
```

### 2\. `combine_tiles_csv.py`

**Purpose:** Aggregates individual tile-level CSVs from multiple inference result directories into a single master dataset. It adds a `label` column to distinguish between classes (e.g., MSI-H vs MSS).

**Arguments:**

  * `--results_dirs`: List of directories containing the processed tile data.
  * `--labels`: List of labels corresponding to each directory (must match order).
  * `--output`: Path for the final combined CSV.

**Usage:**

```bash
python combine_tiles_csv.py \
  --results_dirs /path/to/results/msi_h /path/to/results/mss_tmb \
  --labels 1 0 \
  --output /path/to/data/combined_training_data.csv
```

### 3\. `csv_operations.py`

**Purpose:** A utility to split large CSV files into smaller chunks (useful for upload limits or backup) and merge them back together.

**Usage (Split):**
Splits a file into two parts (`_part1.csv` and `_part2.csv`).

```bash
python csv_operations.py split large_file.csv [optional_prefix]
```

**Usage (Merge):**
Combines two parts back into one file.

```bash
python csv_operations.py merge part1.csv part2.csv restored_file.csv
```

-----

### Answer to your question: "filter\_tmb\_h.py do you mean I can rename this?"

**Yes, absolutely.**

The filename `filter_tmb_h.py` is actually misleading because the code inside is generic—it can filter for **any** category (MSI-H, MSS/TMB-L, etc.) just by changing one line of code.

I highly recommend renaming it to something more descriptive like:

  * `create_image_list.py`
  * `filter_clinical_data.py`

If you rename it, just remember to update any references to it in your main `scripts/` folder (though based on your previous files, this script seems to be run manually to generate the input CSVs for the pipeline).