# Machine Learning Pipeline for Molecular Subclass Classification

This pipeline implements a comprehensive machine learning workflow for classifying endometrial cancer molecular subtypes (MSS/TMB-H, MSS/TMB-L, MSI-H) based on spatial immune features extracted from whole slide images (WSIs).

## Overview

The pipeline performs the following steps:
1. **Dimensionality Reduction**: PCA on tile-level features with patient-level aggregation
2. **Model Training**: Multiple classifiers with various class imbalance strategies
3. **Evaluation**: Comprehensive performance metrics, visualizations, and comparison
4. **Learning Curves**: Overfitting analysis and model convergence assessment

## Configuration

Edit `configs/config.yaml` to customize:

### Data Settings
- **dataframe_path**: Path to input CSV with tile-level features
- **case_id_column**: Patient identifier column (default: `case_id`)
- **label_column**: Molecular subtype column (default: `label`)
- **feature_selection**: Auto-detection or manual feature specification

### PCA Settings
- **n_components**: Number of components (null = auto-detect from variance threshold)
- **variance_threshold**: Cumulative variance to retain (default: 0.95)
- **use_incremental**: Use incremental PCA for large datasets
- **batch_size**: Batch size for incremental processing

### Aggregation Settings
- **functions**: Statistics to compute per patient (mean, std, median, min, max)

### Training Settings
- **val_size**: Validation split proportion (default: 0.2)
- **stratify**: Stratified splitting by class (recommended: true)
- **random_state**: Random seed for reproducibility

### Imbalance Strategies
- **class_weight**: Use class weights in loss function
- **smote**: Synthetic Minority Oversampling Technique
- **combined**: SMOTE + Tomek links (hybrid approach)

## Usage

### Individual Steps

#### 1. PCA Dimensionality Reduction

```bash
sbatch scripts/machine_learning/run_pca.sh
```

**Inputs:**
- Tile-level feature CSV (configured in `config.yaml`)

**Outputs:**
- `data/processed/train/features.npy` - Training features (aggregated)
- `data/processed/train/labels.npy` - Training labels
- `data/processed/val/features.npy` - Validation features
- `data/processed/val/labels.npy` - Validation labels
- `ml_results/models/pca.pkl` - Fitted PCA transformer
- `ml_results/models/scaler.pkl` - Fitted StandardScaler
- `ml_results/models/label_map.pkl` - Label encoding mapping
- `ml_results/figures/pca_variance.png` - Variance explained plot

**What it does:**
1. Loads tile-level features from all patients
2. Fits PCA on ALL tiles (no data leakage)
3. Transforms tiles to PCA space
4. Aggregates PCA features per patient (mean, std, median, etc.)
5. Splits patients into train/val sets (stratified)
6. Saves patient-level arrays for training

#### 2. Model Training

```bash
sbatch scripts/machine_learning/train.sh
```

**Inputs:**
- `data/processed/train/` - Training data from step 1

**Outputs:**
- `ml_results/models/*_*.pkl` - Trained model files (12 total: 4 models × 3 strategies)
- `ml_results/training_summary.csv` - Training metadata and timings

**What it does:**
1. Loads patient-level training data
2. For each model and strategy combination:
   - Applies imbalance handling (class weights, SMOTE, or combined)
   - Trains classifier with configured hyperparameters
   - Saves trained model to disk
3. Logs training time and sample counts

**Models trained:**
- Logistic Regression (multinomial, L2 regularization)
- Random Forest (balanced class weights)
- XGBoost (multi-class softprob)
- Multi-Layer Perceptron (with early stopping)

#### 3. Model Evaluation

```bash
sbatch scripts/machine_learning/evaluation.sh
```

**Inputs:**
- `data/processed/val/` - Validation data
- `ml_results/models/*_*.pkl` - All trained models

**Outputs:**
- `ml_results/evaluation_results.csv` - All metrics in table format
- `ml_results/evaluation_report.md` - Detailed markdown report
- `ml_results/figures/cm_*.png` - Confusion matrix for each model
- `ml_results/figures/roc_curves.png` - Combined ROC curves (3 subplots)
- `ml_results/figures/roc_curve_*.png` - Individual ROC per class
- `ml_results/figures/strategy_comparison.png` - Heatmap of F1 by strategy
- `ml_results/figures/per_class_performance.png` - Top 5 models bar chart

**What it does:**
1. Loads validation data and all trained models
2. For each model:
   - Generates predictions and probabilities
   - Computes metrics: balanced accuracy, F1, weighted F1, ROC-AUC
   - Calculates per-class precision, recall, F1, ROC-AUC
   - Creates confusion matrix visualization
3. Compares all models and identifies best performer
4. Creates comprehensive comparison visualizations
5. Generates detailed markdown report

**Key Metrics:**
- **Balanced Accuracy**: Average recall per class (handles imbalance)
- **F1**: Unweighted mean F1 across classes
- **Weighted F1**: Sample-weighted mean F1
- **ROC-AUC (OvR)**: One-vs-Rest area under ROC curve
- **Per-class F1/Precision/Recall**: Individual class performance


### Class Imbalance Handling

Three strategies are compared:

1. **Class Weight** (fastest)
   - Assigns higher loss penalties to minority classes
   - No data resampling
   - Supported by all scikit-learn models

2. **SMOTE** (moderate speed)
   - Synthetic Minority Oversampling Technique
   - Creates synthetic samples via k-NN interpolation
   - Increases minority class representation

3. **Combined (SMOTE-Tomek)** (slowest, most thorough)
   - SMOTE for oversampling minority classes
   - Tomek links for cleaning class boundaries
   - Removes ambiguous samples near decision boundaries
