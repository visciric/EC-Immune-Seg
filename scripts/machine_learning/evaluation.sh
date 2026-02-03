#!/bin/bash
#SBATCH --job-name=evaluate
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

# Create necessary directories
mkdir -p ml_results/figures logs

# Check prerequisites
echo "Checking prerequisites"
echo ""

MISSING=0

if [ ! -f data/processed/val/features.npy ]; then
    echo "Validation features not found"
    MISSING=1
else
    echo "Validation features found"
fi

if [ ! -f data/processed/val/labels.npy ]; then
    echo "Validation labels not found"
    MISSING=1
else
    echo "Validation labels found"
fi

if [ ! -f ml_results/models/label_map.pkl ]; then
    echo "Label map not found"
    MISSING=1
else
    echo "Label map found"
fi

# Count trained models
MODEL_COUNT=$(ls ml_results/models/*_*.pkl 2>/dev/null | grep -v "scaler\|pca\|label_map\|feature_columns" | wc -l)

if [ $MODEL_COUNT -eq 0 ]; then
    echo "No trained models found"
    MISSING=1
else
    echo "Found $MODEL_COUNT trained models"
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "ERROR: Missing prerequisites. Run PCA and training jobs first!"
    exit 1
fi

echo ""

# Display validation data info
echo "Validation data:"
python -c "
import numpy as np
X_val = np.load('data/processed/val/features.npy')
y_val = np.load('data/processed/val/labels.npy')
print(f'  Shape: X{X_val.shape}, y{y_val.shape}')
print(f'  Label distribution: {np.bincount(y_val)}')
"
echo ""

# Run evaluation
echo "Starting model evaluation"
echo ""

python scripts/03_evaluate.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "Completed: $(date)"
echo "Exit code: $EXIT_CODE"
echo ""

# Check outputs if successful
if [ $EXIT_CODE -eq 0 ]; then
    echo "Evaluation Complete!"
    echo ""
    echo "Output files created:"
    echo ""
    
    # Check results CSV
    echo "Results:"
    if [ -f ml_results/evaluation_results.csv ]; then
        LINES=$(wc -l < ml_results/evaluation_results.csv)
        echo "  Evaluation results: $(du -h ml_results/evaluation_results.csv | cut -f1) ($((LINES-1)) models)"
    else
        echo "  Evaluation results: NOT FOUND"
    fi
    
    if [ -f ml_results/evaluation_report.md ]; then
        echo "  Evaluation report: $(du -h ml_results/evaluation_report.md | cut -f1)"
    else
        echo "  Evaluation report: NOT FOUND"
    fi
    
    echo ""
    echo "Figures:"
    
    # Check key figures
    if [ -f ml_results/figures/model_comparison.png ]; then
        echo "  Model comparison: $(du -h ml_results/figures/model_comparison.png | cut -f1)"
    else
        echo "  Model comparison: NOT FOUND"
    fi
    
    if [ -f ml_results/figures/strategy_comparison.png ]; then
        echo "  Strategy comparison: $(du -h ml_results/figures/strategy_comparison.png | cut -f1)"
    else
        echo "  Strategy comparison: NOT FOUND"
    fi
    
    if [ -f ml_results/figures/per_class_performance.png ]; then
        echo "  Per-class performance: $(du -h ml_results/figures/per_class_performance.png | cut -f1)"
    else
        echo "  Per-class performance: NOT FOUND"
    fi
    
    if [ -f ml_results/figures/roc_curves.png ]; then
        echo "  ROC curves: $(du -h ml_results/figures/roc_curves.png | cut -f1)"
    else
        echo "  ROC curves: NOT FOUND"
    fi
    
    # Count confusion matrices
    CM_COUNT=$(ls ml_results/figures/cm_*.png 2>/dev/null | wc -l)
    echo "  Confusion matrices: $CM_COUNT files"
    
    echo ""
    
    # Show best model
    if [ -f ml_results/evaluation_results.csv ]; then
        echo "Best Model (by Macro F1):"
        echo "-------------------------------------------"
        head -2 ml_results/evaluation_results.csv
        
        echo ""
        echo "Top 5 Models:"
        echo "-------------------------------------------"
        head -6 ml_results/evaluation_results.csv | tail -5
    fi
    
    echo ""
    echo "Summary statistics:"
    grep -E "(Best Model|Macro F1|Balanced Acc)" logs/evaluate_${SLURM_JOB_ID}.out 2>/dev/null | tail -5 || echo "  (Check log file for details)"
    
else
    echo "Evaluation FAILED with exit code $EXIT_CODE"
    echo "Check logs/evaluate_${SLURM_JOB_ID}.err for details"
    echo ""
    echo "Last 20 lines of error log:"
    tail -20 logs/evaluate_${SLURM_JOB_ID}.err 2>/dev/null || echo "  (Log file not found)"
fi

# Resource usage
echo ""
echo "Resource Usage:"
sacct -j $SLURM_JOB_ID --format=JobID,JobName,MaxRSS,Elapsed,State

exit $EXIT_CODE