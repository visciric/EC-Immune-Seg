#!/bin/bash
#SBATCH --job-name=wsi_heatmap
#SBATCH --array=1-33%10
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=128GB

# Configuration
MODE="csv"  #both, heatmap, csv
TILE_SIZE=896
WSI_ALPHA=0.9
COLORMAP="colorblind_safe" #"green_yellow_red" ,"colorblind_safe", "red_intensity"

WSI_BASE_DIR="/cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec"
RESULTS_BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/hovernet/tmb_h"
OUTPUT_DIR="$RESULTS_BASE_DIR/processed/heatmaps_colorblind"
CSV_OUTPUT_DIR="$RESULTS_BASE_DIR/processed/tile_data"
SCRIPT_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/src/image_processing"

mkdir -p "$OUTPUT_DIR" "$CSV_OUTPUT_DIR"

if [ -d "$RESULTS_BASE_DIR/json" ]; then
    CASE_LIST=($(ls -1 "$RESULTS_BASE_DIR/json"/TCGA-*.json 2>/dev/null | xargs -n1 basename | sed 's/\.json$//' | sort))
    INPUT_TYPE="hovernet"
else
    CASE_LIST=($(ls -1d "$RESULTS_BASE_DIR"/TCGA-* 2>/dev/null | xargs -n1 basename | sort))
    INPUT_TYPE="hovernext"
fi

CASE_NAME="${CASE_LIST[$((SLURM_ARRAY_TASK_ID-1))]}"

[ -z "$CASE_NAME" ] && echo "ERROR: No case for task $SLURM_ARRAY_TASK_ID" && exit 1

if [ "$INPUT_TYPE" = "hovernet" ]; then
    INPUT_PATH="$RESULTS_BASE_DIR/json/${CASE_NAME}.json"
else
    INPUT_PATH="$RESULTS_BASE_DIR/$CASE_NAME"
fi

[ ! -e "$INPUT_PATH" ] && echo "ERROR: Input not found: $INPUT_PATH" && exit 1

# Find WSI file
WSI_FILE=$(find "$WSI_BASE_DIR" -name "${CASE_NAME}.svs" -type f 2>/dev/null | head -n1)
[ -z "$WSI_FILE" ] && echo "ERROR: WSI not found for $CASE_NAME" && exit 1

# Set output files
OUTPUT_FILE="$OUTPUT_DIR/${CASE_NAME}_heatmap.png"
CSV_FILE="$CSV_OUTPUT_DIR/${CASE_NAME}_tiles.csv"

# Check if already processed
if [ "$MODE" = "both" ] && [ -f "$OUTPUT_FILE" ] && [ -f "$CSV_FILE" ]; then
    exit 0
elif [ "$MODE" = "heatmap" ] && [ -f "$OUTPUT_FILE" ]; then
    exit 0
elif [ "$MODE" = "csv" ] && [ -f "$CSV_FILE" ]; then
    exit 0
fi

cd "$SCRIPT_DIR"

# Run processing
case "$MODE" in
    both)
        python -B main.py --input "$INPUT_PATH" --wsi "$WSI_FILE" --output "$OUTPUT_FILE" \
            --csv "$CSV_FILE" --tile_size $TILE_SIZE --wsi_alpha $WSI_ALPHA --colormap $COLORMAP
        ;;
    heatmap)
        python -B main.py --input "$INPUT_PATH" --wsi "$WSI_FILE" --output "$OUTPUT_FILE" \
            --tile_size $TILE_SIZE --wsi_alpha $WSI_ALPHA --colormap $COLORMAP
        ;;
    csv)
        TEMP_OUTPUT="/tmp/${CASE_NAME}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.png"
        python -B main.py --input "$INPUT_PATH" --wsi "$WSI_FILE" --output "$TEMP_OUTPUT" \
            --csv "$CSV_FILE" --tile_size $TILE_SIZE --wsi_alpha $WSI_ALPHA --colormap $COLORMAP
        rm -f "$TEMP_OUTPUT"
        ;;
esac

exit $?