#!/bin/bash
#SBATCH --job-name=visualize_hovernet_json
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=24GB

# Usage: sbatch visualize_tiles_hovernet_json.sh CASE_NAME inflammatory 5
# This version uses contours from JSON file directly (no mask PNG needed!)

CASE_NAME="${1:?Error: Provide case name}"
CELL_TYPE="${2:-inflammatory}"
NUM_TILES="${3:-5}"
TILE_SIZE=896
CENTROID_SIZE=3

RESULTS_BASE="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/hovernet/tmb_h"
WSI_BASE="/cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec"
SCRIPT_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/src/image_processing"

JSON_FILE="$RESULTS_BASE/json/${CASE_NAME}.json"
CSV_FILE="$RESULTS_BASE/processed/tile_data/${CASE_NAME}_tiles.csv"
OUTPUT_DIR="$RESULTS_BASE/processed/tile_visualizations/$CASE_NAME"

[ ! -f "$JSON_FILE" ] && echo "ERROR: JSON not found: $JSON_FILE" && exit 1
[ ! -f "$CSV_FILE" ] && echo "ERROR: CSV not found: $CSV_FILE" && exit 1

WSI_FILE=$(find "$WSI_BASE" -name "${CASE_NAME}.svs" -type f 2>/dev/null | head -n1)
[ -z "$WSI_FILE" ] && echo "ERROR: WSI not found for $CASE_NAME" && exit 1

mkdir -p "$OUTPUT_DIR"
cd "$SCRIPT_DIR"

echo "===================================================================="
echo "Processing $NUM_TILES tiles for case: $CASE_NAME"
echo "Cell type: $CELL_TYPE"
echo "Mode: JSON-only (boundaries from contours)"
echo "===================================================================="

# Build tile coordinates string for batch processing
TILE_COORDS=$(python -c "
import pandas as pd
df = pd.read_csv('$CSV_FILE')
top = df.nlargest($NUM_TILES, '${CELL_TYPE}')[['tile_x', 'tile_y', '${CELL_TYPE}']]
coords = []
for _, row in top.iterrows():
    coords.append(f'{int(row.tile_x)},{int(row.tile_y)}')
print(';'.join(coords))
")

echo "Tile coordinates: $TILE_COORDS"
echo ""
echo "Processing all tiles in one batch (JSON loaded once)..."
echo ""

# Process all tiles in one call - JSON is loaded only once!
python visualize_tile_hovernet.py \
    --json "$JSON_FILE" \
    --wsi "$WSI_FILE" \
    --tile_coords "$TILE_COORDS" \
    --tile_size $TILE_SIZE \
    --output "$OUTPUT_DIR" \
    --centroid_size $CENTROID_SIZE \
    --boundary_alpha 0.8 \
    --fill_alpha 0.0 \
    --wsi_alpha 0.2 \
    --no_centroids

echo ""
echo " All visualizations saved to: $OUTPUT_DIR"