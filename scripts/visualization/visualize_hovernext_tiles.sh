#!/bin/bash
#SBATCH --job-name=visualize_tiles
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=16GB

# Usage: sbatch visualize_hovernext_tiles.sh CASE_NAME inflammatory 5

CASE_NAME="${1:?Error: Provide case name}"
CELL_TYPE="${2:-inflammatory}"
NUM_TILES="${3:-5}"
TILE_SIZE=896
CENTROID_SIZE=3

RESULTS_BASE="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/hovernext/msi-h"
WSI_BASE="/cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec"
SCRIPT_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/src/image_processing"

CASE_DIR="$RESULTS_BASE/$CASE_NAME"
CSV_FILE="$RESULTS_BASE/processed/tile_data/${CASE_NAME}_tiles.csv"
OUTPUT_DIR="$RESULTS_BASE/processed/tile_visualizations/$CASE_NAME"

[ ! -d "$CASE_DIR" ] && echo "ERROR: Case directory not found: $CASE_DIR" && exit 1
[ ! -f "$CSV_FILE" ] && echo "ERROR: CSV not found: $CSV_FILE" && exit 1

WSI_FILE=$(find "$WSI_BASE" -name "${CASE_NAME}.svs" -type f 2>/dev/null | head -n1)
[ -z "$WSI_FILE" ] && echo "ERROR: WSI not found for $CASE_NAME" && exit 1

mkdir -p "$OUTPUT_DIR"
cd "$SCRIPT_DIR"

python -c "
import pandas as pd
df = pd.read_csv('$CSV_FILE')
top = df.nlargest($NUM_TILES, '${CELL_TYPE}')[['tile_x', 'tile_y', '${CELL_TYPE}']]
for _, row in top.iterrows():
    print(f'{int(row.tile_x)} {int(row.tile_y)} {int(row[\"${CELL_TYPE}\"])}')
" | while read TILE_X TILE_Y COUNT; do
    OUTPUT_FILE="$OUTPUT_DIR/tile_${TILE_X}_${TILE_Y}_${COUNT}${CELL_TYPE}.png"
    
    python visualize_tile_hovernext.py \
        --input "$CASE_DIR" \
        --wsi "$WSI_FILE" \
        --tile_x $TILE_X \
        --tile_y $TILE_Y \
        --tile_size $TILE_SIZE \
        --output "$OUTPUT_FILE" \
        --centroid_size $CENTROID_SIZE \
        --boundary_alpha 1.0 \
        --fill_alpha 0.0 \
        --wsi_alpha 0.7\
        --no_centroids
done

echo "Visualizations saved to: $OUTPUT_DIR"