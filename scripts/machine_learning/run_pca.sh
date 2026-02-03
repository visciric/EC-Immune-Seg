#!/bin/bash
#SBATCH --job-name=pca_reduce
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:10:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=64GB

# Define directory structure
BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
WORK_DIR="${BASE_DIR}/notebooks/machine_learning"

# Navigate to working directory
cd "$WORK_DIR" || {
    echo "ERROR: Cannot navigate to $WORK_DIR"
    exit 1
}

echo "Working directory: $(pwd)"
echo ""


# Set threading for parallel processing
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export NUMEXPR_NUM_THREADS=$SLURM_CPUS_PER_TASK
export VECLIB_MAXIMUM_THREADS=$SLURM_CPUS_PER_TASK

# Create necessary directories
mkdir -p ml_results/models ml_results/figures data/processed/train logs

# Check if input data exists
if [ -f "configs/config.yaml" ]; then
    INPUT_FILE=$(python -c "import yaml; config=yaml.safe_load(open('configs/config.yaml')); print(config['data']['dataframe_path'])" 2>/dev/null)
    if [ -z "$INPUT_FILE" ]; then
        INPUT_FILE="data/tile_features.csv"
    fi
else
    INPUT_FILE="data/tile_features.csv"
fi

echo "Input file: $INPUT_FILE"

# Get file size
INPUT_SIZE=$(du -h "$INPUT_FILE" | cut -f1)
echo "Input file size: $INPUT_SIZE"
echo ""

# Run PCA pipeline
echo "Starting PCA pipeline"

python scripts/01_pca_reduction.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "Completed: $(date)"
echo "Exit code: $EXIT_CODE"


# Check outputs if successful
if [ $EXIT_CODE -eq 0 ]; then
    echo "PCA Pipeline Complete!"
    echo "Output files created:"
    
    
    # Check models
    echo "Models:"
    if [ -f ml_results/models/pca.pkl ]; then
        echo "PCA model: $(du -h ml_results/models/pca.pkl | cut -f1)"
    else
        echo "PCA model: NOT FOUND"
    fi
    
    if [ -f ml_results/models/scaler.pkl ]; then
        echo "Scaler: $(du -h ml_results/models/scaler.pkl | cut -f1)"
    else
        echo "Scaler: NOT FOUND"
    fi
    
    if [ -f ml_results/models/label_map.pkl ]; then
        echo "Label map: $(du -h ml_results/models/label_map.pkl | cut -f1)"
    else
        echo "Label map: NOT FOUND"
    fi
    
    if [ -f ml_results/models/feature_columns.pkl ]; then
        echo "Feature columns: $(du -h ml_results/models/feature_columns.pkl | cut -f1)"
    else
        echo "Feature columns: NOT FOUND"
    fi
    
    echo "Processed data:"
    
    # Check processed data
    if [ -f data/processed/train/features.npy ]; then
        TRAIN_SIZE=$(du -h data/processed/train/features.npy | cut -f1)
        echo "Train features: $TRAIN_SIZE"
    else
        echo "Train features: NOT FOUND"
    fi
    
    if [ -f data/processed/train/labels.npy ]; then
        echo "Train labels: $(du -h data/processed/train/labels.npy | cut -f1)"
    else
        echo "Train labels: NOT FOUND"
    fi
    
    # Check figures
    if [ -f ml_results/figures/pca_variance.png ]; then
        echo "Variance plot created"
    else
        echo "Variance plot: NOT FOUND"
    fi
    echo "Summary statistics:"
    grep -E "(Original dimensions|Reduced dimensions|Variance explained|Train samples|Test samples)" logs/pca_${SLURM_JOB_ID}.out 2>/dev/null | tail -5 || echo "  (Check log file for details)"
    
else
    echo "PCA Pipeline FAILED with exit code $EXIT_CODE"
    echo "Check logs/pca_${SLURM_JOB_ID}.err for details"
fi

# Resource usage
echo ""
echo "Resource Usage:"
sacct -j $SLURM_JOB_ID --format=JobID,JobName,MaxRSS,Elapsed,State

exit $EXIT_CODE
