#!/bin/bash
#SBATCH --job-name=clustering
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=128GB

BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
WORK_DIR="${BASE_DIR}/notebooks/cluster"
SCRIPT_PATH="${WORK_DIR}/clustering.py"
INPUT_CSV="${BASE_DIR}/data/processed_csv/combined_wsi_data.csv"

cd "$WORK_DIR" || { echo "ERROR: Cannot navigate to $WORK_DIR"; exit 1; }

echo "Job ID: $SLURM_JOB_ID | Started: $(date)"

# Set threading
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export NUMEXPR_NUM_THREADS=$SLURM_CPUS_PER_TASK
export VECLIB_MAXIMUM_THREADS=$SLURM_CPUS_PER_TASK

mkdir -p clustering_results logs

# Check prerequisites
[ ! -f "$INPUT_CSV" ] && { echo "ERROR: Input CSV not found: $INPUT_CSV"; exit 1; }
[ ! -f "$SCRIPT_PATH" ] && { echo "ERROR: Script not found: $SCRIPT_PATH"; exit 1; }

python -c "import pandas, numpy, matplotlib, seaborn, sklearn, umap, hdbscan" || \
    { echo "ERROR: Missing Python packages"; exit 1; }

echo "Prerequisites OK | Starting clustering..."

START_TIME=$(date +%s)
python "$SCRIPT_PATH" --input "$INPUT_CSV"
EXIT_CODE=$?
END_TIME=$(date +%s)

ELAPSED=$(($((END_TIME - START_TIME)) / 60))m
echo "Completed: $(date) | Time: $ELAPSED | Exit: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    ls -lh clustering_results/*.{csv,png} 2>/dev/null || echo "No output files found"
else
    echo "FAILED - Check logs/clustering_${SLURM_JOB_ID}.err"
fi

exit $EXIT_CODE