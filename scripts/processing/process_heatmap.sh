#!/bin/bash
#SBATCH --job-name=wsi_heatmap
#SBATCH --array=1-31
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:30:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=128GB

# Configuration
TILE_SIZE=896
WSI_ALPHA=0.7
COLORMAP="red_intensity"  # Options: "green_yellow_red", "colorblind_safe", "red_intensity", "blue_intensity"

WSI_BASE_DIR="/cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec"
RESULTS_BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/hovernet/tmb_h"
OUTPUT_DIR="$RESULTS_BASE_DIR/processed/heatmaps_red_intensity"
CSV_OUTPUT_DIR="$RESULTS_BASE_DIR/processed/tile_data"
SCRIPT_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/src/image_processing"

mkdir -p "$OUTPUT_DIR"

# Choose one of the following options

# Option 1: Process SPECIFIC cases 
# SELECTED_CASES=(
#     "TCGA-EO-A3AZ-01Z-00-DX1.113D4EE1-7922-432D-B43B-947756060983"
#     "TCGA-B5-A3FA-01Z-00-DX1.AD6F12EA-9E77-454A-96A9-C087778BC34D"
#     "TCGA-FI-A2D2-01Z-00-DX1.D14E7B6C-DD07-4FE3-A23D-3B62B4346A00"
# )

# Option 2: Process FIRST N cases
FIRST_N=31

# Option 3: Process RANDOM N cases
# RANDOM_N=10


# Images Used in the Publication 
# MSI 
# SELECTED_CASES=("TCGA-EO-A3AZ-01Z-00-DX1.113D4EE1-7922-432D-B43B-947756060983")

# MSS/TMB-H
# SELECTED_CASES=("TCGA-B5-A3FA-01Z-00-DX1.AD6F12EA-9E77-454A-96A9-C087778BC34D")

# MSS/TMB-L
# SELECTED_CASES=("TCGA-FI-A2D2-01Z-00-DX1.D14E7B6C-DD07-4FE3-A23D-3B62B4346A00")



# Detect input type and get full case list
if [ -d "$RESULTS_BASE_DIR/json" ]; then
    ALL_CASES=($(ls -1 "$RESULTS_BASE_DIR/json"/TCGA-*.json 2>/dev/null | xargs -n1 basename | sed 's/\.json$//' | sort))
    INPUT_TYPE="hovernet"
else
    ALL_CASES=($(ls -1d "$RESULTS_BASE_DIR"/TCGA-* 2>/dev/null | xargs -n1 basename | sort))
    INPUT_TYPE="hovernext"
fi

# Apply selection logic
if [ ! -z "${SELECTED_CASES+x}" ]; then
    # Option 1: Use manually specified cases
    CASE_LIST=("${SELECTED_CASES[@]}")
    echo "Mode: Processing ${#CASE_LIST[@]} manually selected cases"
elif [ ! -z "$FIRST_N" ]; then
    # Option 2: Use first N cases
    CASE_LIST=("${ALL_CASES[@]:0:$FIRST_N}")
    echo "Mode: Processing first $FIRST_N cases"
elif [ ! -z "$RANDOM_N" ]; then
    # Option 3: Use random N cases
    CASE_LIST=($(printf '%s\n' "${ALL_CASES[@]}" | shuf | head -n $RANDOM_N))
    echo "Mode: Processing $RANDOM_N random cases"
else
    echo "ERROR: No selection mode configured. Edit the script to choose SELECTED_CASES, FIRST_N, or RANDOM_N"
    exit 1
fi

# Get case for this array task
CASE_NAME="${CASE_LIST[$((SLURM_ARRAY_TASK_ID-1))]}"
[ -z "$CASE_NAME" ] && echo "ERROR: No case for task $SLURM_ARRAY_TASK_ID" && exit 1

# Set input path
if [ "$INPUT_TYPE" = "hovernet" ]; then
    INPUT_PATH="$RESULTS_BASE_DIR/json/${CASE_NAME}.json"
else
    INPUT_PATH="$RESULTS_BASE_DIR/$CASE_NAME"
fi
[ ! -e "$INPUT_PATH" ] && echo "ERROR: Input not found: $INPUT_PATH" && exit 1

# Find WSI file
WSI_FILE=$(find "$WSI_BASE_DIR" -name "${CASE_NAME}.svs" -type f 2>/dev/null | head -n1)
[ -z "$WSI_FILE" ] && echo "ERROR: WSI not found for $CASE_NAME" && exit 1

OUTPUT_FILE="$OUTPUT_DIR/${CASE_NAME}_heatmap.png"
CSV_FILE="$CSV_OUTPUT_DIR/${CASE_NAME}_tiles.csv"

# Skip if already processed
[ -f "$OUTPUT_FILE" ] && echo "Already processed: $CASE_NAME" && exit 0

echo "Processing heatmap for: $CASE_NAME"
cd "$SCRIPT_DIR"

# Generate heatmap (reuse CSV if it exists)
python -B main.py --input "$INPUT_PATH" --wsi "$WSI_FILE" --output "$OUTPUT_FILE" \
    --csv "$CSV_FILE" --tile_size $TILE_SIZE --wsi_alpha $WSI_ALPHA --colormap $COLORMAP

EXIT_CODE=$?
echo "Completed: $CASE_NAME (Heatmap: $OUTPUT_FILE)"
exit $EXIT_CODE