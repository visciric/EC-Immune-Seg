#!/bin/bash
#SBATCH --job-name=combined_csv
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:30:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=16GB

RESULTS_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results"
OUTPUT_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/processed_csv"

mkdir -p "$OUTPUT_DIR"

cd "/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/src/dataset_processing/"

# MSI-H (combining both directories)
# python combine_tiles_csv.py \
#     --results_dirs "$RESULTS_DIR/hovernet/msi-h" "$RESULTS_DIR/hovernext/msi-h" \
#     --labels msi-h msi-h \
#     --output "$OUTPUT_DIR/msi-h.csv"

# # TMB-H (note: underscore in directory name)
# python combine_tiles_csv.py \
#     --results_dirs "$RESULTS_DIR/hovernet/tmb_h" \
#     --labels mss_tmb-h \
#     --output "$OUTPUT_DIR/mss_tmb-h.csv"

# MSS_TMB-L
# python combine_tiles_csv.py \
#     --results_dirs "$RESULTS_DIR/hovernext/mss_tmb-l" \
#     --labels mss_tmb-l \
#     --output "$OUTPUT_DIR/mss_tmb-l.csv"

echo "Created:"
echo "  $OUTPUT_DIR/msi-h.csv"
echo "  $OUTPUT_DIR/mss_tmb-h.csv"
echo "  $OUTPUT_DIR/mss_tmb-l.csv"