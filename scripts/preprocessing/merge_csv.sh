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

# Usage: sbatch merge_csv.sbatch <file1.csv> <file2.csv> <output.csv>

# Change to dataset_processing directory where csv_operations.py is located
cd '/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/notebooks/dataset_processing'

# Get input files from command line arguments (should be full paths)
FILE1=$1
FILE2=$2
OUTPUT_FILE=$3

if [ -z "$FILE1" ] || [ -z "$FILE2" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Error: Missing required arguments"
    echo "Usage: sbatch merge_csv.sbatch <full_path_file1.csv> <full_path_file2.csv> <full_path_output.csv>"
    exit 1
fi

if [ ! -f "$FILE1" ]; then
    echo "Error: File $FILE1 not found"
    exit 1
fi

if [ ! -f "$FILE2" ]; then
    echo "Error: File $FILE2 not found"
    exit 1
fi

echo "Starting CSV merge job"
echo "File 1: $FILE1"
echo "File 2: $FILE2"
echo "Output: $OUTPUT_FILE"
echo "Working directory: $(pwd)"
echo "=========================================="

# Run the merge operation
python csv_operations.py merge "$FILE1" "$FILE2" "$OUTPUT_FILE"

echo "=========================================="
echo "Job completed"
