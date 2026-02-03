#!/bin/bash
#SBATCH --job-name=train_ml
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:30:00
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

# Check if PCA data exists
echo "Checking for PCA processed data..."

if [ ! -f data/processed/train/features.npy ]; then
    echo "ERROR: Training features not found. Run PCA job first!"
    exit 1
fi

if [ ! -f data/processed/train/labels.npy ]; then
    echo "ERROR: Training labels not found. Run PCA job first!"
    exit 1
fi

echo "All PCA data files found"
echo ""

# Display data info
echo "Data shapes:"
python -c "
import numpy as np
X_train = np.load('data/processed/train/features.npy')
y_train = np.load('data/processed/train/labels.npy')
X_val = np.load('data/processed/val/features.npy')
y_val = np.load('data/processed/val/labels.npy')
print(f'  Train: X{X_train.shape}, y{y_train.shape}')
print(f'  Validation: X{X_val.shape}, y{y_val.shape}')
print(f'  Label distribution (train): {np.bincount(y_train)}')
print(f'  Label distribution (validation): {np.bincount(y_val)}')
"
echo ""

# Run model training
echo "Starting model training..."
echo "=========================================="

python scripts/02_train_models.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Completed: $(date)"
echo "Exit code: $EXIT_CODE"
echo "=========================================="

# Print summary if training succeeded
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Training Complete!"
    
    if [ -f ml_results/training_summary.csv ]; then
        echo ""
        echo "Training Summary:"
        echo "-------------------------------------------"
        
        # Count total models
        TOTAL_MODELS=$(tail -n +2 ml_results/training_summary.csv | wc -l)
        echo "Total models trained: $TOTAL_MODELS"
        
        # Count successful models
        SUCCESSFUL=$(tail -n +2 ml_results/training_summary.csv | grep -c "success" || echo "0")
        echo "Successful: $SUCCESSFUL"
        
        # Count failed models
        FAILED=$(tail -n +2 ml_results/training_summary.csv | grep -c "failed" || echo "0")
        if [ $FAILED -gt 0 ]; then
            echo "Failed: $FAILED"
        fi
        
        echo ""
        echo "Models trained:"
        tail -n +2 ml_results/training_summary.csv | awk -F',' '{print "  - " $1 "_" $2}' | sort
        
        echo ""
        echo "Total training time:"
        tail -n +2 ml_results/training_summary.csv | awk -F',' 'BEGIN{sum=0} {sum+=$3} END{printf "  %.2f seconds (%.2f minutes)\n", sum, sum/60}'
        
    else
        echo "Warning: training_summary.csv not found"
    fi
    
    # List trained models
    echo ""
    echo "Trained model files:"
    ls -lh ml_results/models/*_*.pkl 2>/dev/null | grep -v "scaler\|pca\|label_map\|feature_columns" | awk '{print "  " $9 " (" $5 ")"}'
    
else
    echo ""
    echo "Training FAILED with exit code $EXIT_CODE"
    echo "Check logs/train_${SLURM_JOB_ID}.err for details"
    
    echo ""
    echo "Last 20 lines of error log:"
    tail -20 logs/train_${SLURM_JOB_ID}.err
fi

# Resource usage
echo ""
echo "Resource Usage:"
echo "-------------------------------------------"
sacct -j $SLURM_JOB_ID --format=JobID,JobName,MaxRSS,Elapsed,State

exit $EXIT_CODE