#!/bin/bash
#SBATCH --job-name=merge_csv
#SBATCH --array=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:15:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=16GB
#SBATCH --output=merge_%j.out
#SBATCH --error=merge_%j.err

# Usage: sbatch split_csv.sbatch <input.csv> [output_prefix]

# Change to dataset_processing directory where csv_operations.py is located
cd '/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/notebooks/dataset_processing'

# Get input file from command line argument 
INPUT_FILE=$1
OUTPUT_PREFIX=$2

if [ -z "$INPUT_FILE" ]; then
    echo "Error: No input file specified"
    echo "Usage: sbatch split_csv.sbatch <full_path_to_input.csv> [output_prefix]"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File $INPUT_FILE not found"
    exit 1
fi

echo "Starting CSV split job"
echo "Input file: $INPUT_FILE"
echo "Output prefix: ${OUTPUT_PREFIX:-auto}"
echo "Working directory: $(pwd)"
echo "=========================================="

# Run the split operation
if [ -z "$OUTPUT_PREFIX" ]; then
    python csv_operations.py split "$INPUT_FILE"
else
    python csv_operations.py split "$INPUT_FILE" "$OUTPUT_PREFIX"
fi

echo "=========================================="
echo "Job completed"
echo "Output files created in: $(dirname $INPUT_FILE)"
