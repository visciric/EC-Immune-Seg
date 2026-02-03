# Machine Learning Execution Scripts

### **Before you run any `sbatch` files activate youre envinroment**

### 1. PCA Reduction
**File:** `sbatch pca_short.sh`
- Runs: `scripts/01_pca_reduction.py`
- Time: 10 minutes
- First step in the pipeline

### 3. Model Training
**File:** `sbatch train_short.sh`
- Runs: `scripts/02_train_models.py`
- Time: 30 minutes
- Requires: PCA data from step 1

### 4. Model Evaluation
**File:** `sbatch evaluate_short.sh`
- Runs: `scripts/03_evaluate.py`
- Time: 30 minutes
- Requires: Trained models from step 2


## Pipeline Execution

```bash
# Step 1: PCA
sbatch run_pca.sh

# Step 2: Training (after PCA completes)
sbatch train.sh

# Step 3: Evaluation (after training completes)
sbatch evaluation.sh
```
