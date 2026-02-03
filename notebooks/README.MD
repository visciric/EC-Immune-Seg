# Notebooks

This directory contains the core analysis components of the project, including exploratory data analysis, statistical modeling, clustering, and machine learning for tumor segmentation in endometrial cancer histopathology data.

## Directory Structure

```
notebooks/
├── exploratory/              # Exploratory data analysis
├── statistical_analysis/     # Statistical testing and modeling
├── cluster/                  # Spatial clustering analysis
├── machine_learning/         # ML classification pipeline (see dedicated README)
└── README.md                 # This file
```

## Dataset Overview

This analysis focuses on three biologically distinct molecular subgroups from TCGA:

| Subgroup | Description |
|----------|-------------|
| **MSI-H** | Microsatellite Instability – High |
| **MSS/TMB-L** | Microsatellite Stable / Tumor Mutational Burden – Low |
| **MSS/TMB-H** | Microsatellite Stable / Tumor Mutational Burden – High |

### Cell Type Classifications

The analysis quantifies five cell types in histopathology tiles:

| Cell Type | Description |
|-----------|-------------|
| **Neoplastic** | Cancer cells with abnormal morphology |
| **Inflammatory** | Tumor-infiltrating immune cells (lymphocytes, macrophages) |
| **Connective** | Stromal cells (fibroblasts, endothelial cells) |
| **Necrosis** | Regions of cell death |
| **Non-neoplastic** | Normal epithelial or benign tissue |

---

## Analysis Components

### 1. Exploratory Analysis

**Location:** `exploratory/exploratory_analysis.ipynb`

Comprehensive exploratory data analysis to understand dataset composition, quality, and biological patterns before predictive modeling.

**Key Analyses:**

1. **Data Loading & Structure**
   - Dataset composition across molecular subgroups
   - Case and tile-level statistics
   - Missing value assessment

2. **Data Quality Assessment**
   - Percentage validation
   - Outlier detection and handling

3. **Case-Level Analysis**
   - Aggregated statistics per patient case
   - Distribution comparisons across groups
   - Sample size and variability assessment

4. **Correlation Analysis**
   - Feature relationships within groups

**Outputs:**
- Visualization suite in `exploratory/images/`

---

### 2. Statistical Analysis

**Location:** `statistical_analysis/statistical_analysis.ipynb`

Advanced statistical modeling to identify biomarkers distinguishing molecular subgroups.

**Key Analyses:**

#### 2.1 Normality Testing
- Shapiro-Wilk tests for distributional assumptions
- Justification for non-parametric methods

#### 2.2 Primary Statistical Tests
- **Kruskal-Wallis H-test:** Overall group differences
- **Mann-Whitney U test:** Pairwise comparisons
- Effect size metrics


---

### 3. Spatial Clustering Analysis

**Location:** `cluster/clustering.py`

---

### 4. Machine Learning Classification

**Location:** `machine_learning/`

**See dedicated documentation:** `machine_learning/README.md`

Comprehensive ML pipeline for classifying molecular subtypes based on spatial immune features.

**Pipeline Overview:**
1. **PCA Dimensionality Reduction** - Reduce tile features and aggregate to patient level
2. **Model Training** - 4 models × 3 imbalance strategies = 12 trained models
3. **Evaluation** - Comprehensive metrics, confusion matrices, ROC curves

**Models:**
- Logistic Regression
- Random Forest
- XGBoost
- Multi-Layer Perceptron (MLP)

**Imbalance Strategies:**
- Class Weight
- SMOTE (Synthetic Minority Oversampling)
- SMOTE-Tomek (Combined approach)

---
