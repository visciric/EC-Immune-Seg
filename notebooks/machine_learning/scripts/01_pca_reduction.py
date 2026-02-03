"""
PCA Dimensionality Reduction for DataFrame-based Tile Features

This script:
1. Loads tile-level features from CSV
2. Performs PCA on ALL tiles (no splitting)
3. Aggregates PCA components per patient using statistics (mean, std, median)
4. Splits data at patient level (train/val)
5. Saves aggregated patient-level data
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import matplotlib.pyplot as plt
import sys
import logging 

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from utils import (
    setup_logging, load_config, identify_feature_columns,
    encode_labels
)

def load_dataframe(relative_path):
    """
    Load dataframe resolving the path relative to the project root.
    """
    script_dir = Path(__file__).resolve().parent
    
    project_root = script_dir.parents[2] 
    
    #  Construct the full absolute path
    full_path = project_root / relative_path
    
    return pd.read_csv(full_path)


def fit_pca(X, config):
    """
    Fit PCA on training data.
    
    Uses incremental PCA for large datasets to manage memory.
    Returns fitted PCA and scaler objects.
    """
    logger = logging.getLogger(__name__)
    
    n_samples, n_features = X.shape
    use_incremental = config['pca']['use_incremental']
    batch_size = config['pca']['batch_size']
    
    # Fit StandardScaler
    scaler = StandardScaler()
    
    if use_incremental and n_samples > batch_size:
        # Fit scaler incrementally
        for i in range(0, n_samples, batch_size):
            batch = X[i:i+batch_size]
            scaler.partial_fit(batch)
            if i % (batch_size * 10) == 0:
                logger.info(f"  Scaler: {i:,}/{n_samples:,} samples")
    else:
        scaler.fit(X)
    
    joblib.dump(scaler, 'ml_results/models/scaler.pkl')

    
    # Transform data for PCA
    if use_incremental and n_samples > batch_size:
        X_scaled = np.zeros_like(X)
        for i in range(0, n_samples, batch_size):
            batch = X[i:i+batch_size]
            X_scaled[i:i+batch_size] = scaler.transform(batch)
            
    else:
        X_scaled = scaler.transform(X)
    
    # Determine number of components
    variance_threshold = config['pca']['variance_threshold']
    n_components_config = config['pca']['n_components']
    
    if n_components_config is None:
        
        # Fit PCA with all components first
        max_components = min(n_features, n_samples)
        
        if use_incremental and n_samples > batch_size:
            pca_analysis = IncrementalPCA(n_components=max_components)
            for i in range(0, n_samples, batch_size):
                batch = X_scaled[i:i+batch_size]
                pca_analysis.partial_fit(batch)

        else:
            pca_analysis = PCA(n_components=max_components)
            pca_analysis.fit(X_scaled)
        
        # Determine components from variance
        cumsum_variance = np.cumsum(pca_analysis.explained_variance_ratio_)
        n_components = np.argmax(cumsum_variance >= variance_threshold) + 1
              
        # Plot variance
        plot_variance_explained(cumsum_variance, n_components, variance_threshold)
        
    else:
        n_components = n_components_config
    
    # Fit final PCA   
    if use_incremental and n_samples > batch_size:
        pca = IncrementalPCA(n_components=n_components)
        for i in range(0, n_samples, batch_size):
            batch = X_scaled[i:i+batch_size]
            pca.partial_fit(batch)

    else:
        pca = PCA(n_components=n_components)
        pca.fit(X_scaled)
    
    logger.info("PCA fitted")
    
    return pca, scaler


def transform_tiles(X, pca, scaler, config):
    """
    Transform all tiles using fitted PCA.
    
    Returns: numpy array of transformed features
    """
   
    n_samples = len(X)
    batch_size = config['pca']['batch_size']
    use_incremental = config['pca']['use_incremental']
    
    if use_incremental and n_samples > batch_size:
        X_transformed = np.zeros((n_samples, pca.n_components_))
        
        for i in range(0, n_samples, batch_size):
            batch = X[i:i+batch_size]
            batch_scaled = scaler.transform(batch)
            X_transformed[i:i+batch_size] = pca.transform(batch_scaled)
            
    else:
        X_scaled = scaler.transform(X)
        X_transformed = pca.transform(X_scaled)
    
    return X_transformed


def aggregate_patient_features(df_pca, config):
    """
    Aggregate tile-level PCA features to patient-level features.
    
    For each patient, compute statistics (mean, std, median, etc.) across all tiles.
    
    Args:
        df_pca: DataFrame with columns [case_id, label, PC1, PC2, ..., PCn]
        config: Configuration dictionary
    
    Returns:
        DataFrame with aggregated patient-level features
    """  
    case_id_col = config['data']['case_id_column']
    label_col = config['data']['label_column']
    
    # Get PC column names (all except case_id and label)
    pc_cols = [col for col in df_pca.columns if col not in [case_id_col, label_col]]
       
    # Get aggregation functions from config
    agg_funcs = config['aggregation']['functions']
    
   
    # Group by patient and aggregate
    df_agg = (
        df_pca
        .groupby([case_id_col, label_col])[pc_cols]
        .agg(agg_funcs)
    )
        
    # Flatten multi-level column index
    # From (PC1, mean), (PC1, std) to PC1_mean, PC1_std
    df_agg.columns = [f"{pc}_{func}" for pc, func in df_agg.columns]
    
    # Reset index to move case_id and label back to columns
    df_agg = df_agg.reset_index()
        
    return df_agg


def create_splits(df_agg, config):
    """
    Create train/val splits at patient level.
    
    Args:
        df_agg: DataFrame with aggregated patient-level features
        config: Configuration dictionary
    
    Returns:
        train_idx, val_idx, y_encoded, label_map
    """
    logger = logging.getLogger(__name__)
    
    label_col = config['data']['label_column']
    
    # Check unique labels before encoding
    unique_labels = df_agg[label_col].unique()

    # Encode labels
    try:
        y_encoded, label_map = encode_labels(df_agg[label_col].values)        
        
    except ValueError as e:
        logger.error(f"Label encoding failed: {e}")
        raise
        
    # Split patients into train/val    
    train_idx, val_idx = train_test_split(
        np.arange(len(df_agg)),
        test_size=config['train']['val_size'],
        stratify=y_encoded if config['train']['stratify'] else None,
        random_state=config['train']['random_state']
    )
    
    logger.info(f"Train patients: {len(train_idx)} ({100*len(train_idx)/len(df_agg):.1f}%)")
    logger.info(f"Val patients: {len(val_idx)} ({100*len(val_idx)/len(df_agg):.1f}%)")
    
    # Show class distribution in splits
    for split_name, split_idx in [('Train', train_idx), ('Val', val_idx)]:
        logger.info(f"{split_name} distribution:")
        split_labels = y_encoded[split_idx]
        for label_name, label_idx in label_map.items():
            count = np.sum(split_labels == label_idx)
            logger.info(f"  {label_name}: {count} ({100*count/len(split_labels):.1f}%)")
    
    return train_idx, val_idx, y_encoded, label_map


def save_patient_level_data(df_agg, train_idx, val_idx, y_encoded, config):
    """Save train/val data as numpy arrays."""
    logger = logging.getLogger(__name__)
    
    case_id_col = config['data']['case_id_column']
    label_col = config['data']['label_column']
    
    # Get feature columns (exclude case_id and label)
    feature_cols = [col for col in df_agg.columns if col not in [case_id_col, label_col]]
    
    # Extract features
    X = df_agg[feature_cols].values
    
    # Split data
    X_train = X[train_idx]
    X_val = X[val_idx]
    y_train = y_encoded[train_idx]
    y_val = y_encoded[val_idx]
    
    # Save train data
    train_path = Path('data/processed/train')
    train_path.mkdir(parents=True, exist_ok=True)
    np.save(train_path / 'features.npy', X_train)
    np.save(train_path / 'labels.npy', y_train)
    logger.info(f"Saved train data: {X_train.shape}") 
    
    # Save val data
    val_path = Path('data/processed/val')
    val_path.mkdir(parents=True, exist_ok=True)
    np.save(val_path / 'features.npy', X_val)
    np.save(val_path / 'labels.npy', y_val)
    logger.info(f"Saved val data: {X_val.shape}")
    
    # Save feature names
    joblib.dump(feature_cols, 'ml_results/models/aggregated_feature_columns.pkl')
    logger.info(f"Saved {len(feature_cols)} feature column names")
    
    return X_train, X_val, y_train, y_val



def plot_variance_explained(cumsum_variance, n_components, threshold):
    """Plot cumulative variance explained by PCA components."""
    
    plt.figure(figsize=(10, 6))
    
    plt.plot(cumsum_variance, linewidth=2)
    plt.axhline(y=threshold, color='r', linestyle='--', 
                label=f'{threshold:.2%} threshold', linewidth=2)
    plt.axvline(x=n_components, color='g', linestyle='--', 
                label=f'{n_components} components', linewidth=2)
    plt.xlabel('Number of Components', fontsize=12)
    plt.ylabel('Cumulative Explained Variance', fontsize=12)
    plt.title('PCA Variance Explained', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('ml_results/figures/pca_variance.png', dpi=300, bbox_inches='tight')
    plt.close()


def main():
    logger = setup_logging()
    config = load_config()
    
    # Create output directories
    for dir_path in ['ml_results/models', 'ml_results/figures', 'data/processed']:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    logger.info("PCA DIMENSIONALITY REDUCTION PIPELINE")
    
    # Load data
    df = load_dataframe(config['data']['dataframe_path'])
    
    # Identify feature columns
    if config['data']['feature_selection']['strategy'] == 'auto':
        feature_cols = identify_feature_columns(df)
        logger.info(f"Auto-detected {len(feature_cols)} feature columns")
        logger.info(f"Features: {feature_cols}")
    else:
        feature_cols = config['data']['feature_selection']['feature_columns']
        logger.info(f"Using {len(feature_cols)} manually specified features")
    
    # Exclude any additional columns
    exclude_cols = config['data']['feature_selection'].get('exclude_columns', [])
    feature_cols = [col for col in feature_cols if col not in exclude_cols]
    
    # Save feature column names
    joblib.dump(feature_cols, 'ml_results/models/feature_columns.pkl')
    
    # Extract features
    X = df[feature_cols].values

    if np.any(np.isnan(X)):
        logger.warning("Missing values detected! Filling with column means")
        col_means = np.nanmean(X, axis=0)
        nan_indices = np.where(np.isnan(X))
        X[nan_indices] = np.take(col_means, nan_indices[1])
    
    # Fit PCA on ALL tiles
    pca, scaler = fit_pca(X, config)
    
    # Save PCA and Scaler
    joblib.dump(pca, 'ml_results/models/pca.pkl')
    joblib.dump(scaler, 'ml_results/models/scaler.pkl')
    logger.info("PCA and scaler saved")
   
   # Transform all tiles
    X_pca = transform_tiles(X, pca, scaler, config)
      
    # Create DF 
    case_id_col = config['data']['case_id_column']
    label_col = config['data']['label_column']
    
   # Create PCA column names
    pc_cols = [f'PC{i+1}' for i in range(pca.n_components_)]
       
    # Create DataFrame
    df_pca = pd.DataFrame(X_pca, columns=pc_cols)
    df_pca[case_id_col] = df[case_id_col].values
    df_pca[label_col] = df[label_col].values
      
    # Aggregation to patient level 
    df_agg = aggregate_patient_features(df_pca, config)
   
   
    # Create patient-level splits
    train_idx, val_idx, y_encoded, label_map = create_splits(df_agg, config)
    
    # Save label map
    joblib.dump(label_map, 'ml_results/models/label_map.pkl')
    
    # Save train/val data
    X_train, X_val, y_train, y_val = save_patient_level_data(
        df_agg, train_idx, val_idx, y_encoded, config
    )

    
    # Summary statistics
    logger.info(f"Original tile features:     {len(feature_cols)}")
    logger.info(f"PCA components:              {pca.n_components_}")
    logger.info(f"Aggregation functions:       {config['aggregation']['functions']}")
    logger.info(f"Final patient features:      {X_train.shape[1]}")
    logger.info(f"Dimension reduction:         {100 * (1 - pca.n_components_/len(feature_cols)):.1f}%")
    logger.info(f"Variance explained:          {pca.explained_variance_ratio_.sum():.4f}")
    logger.info(f"Total patients:              {len(df_agg)}")
    logger.info(f"Train patients:              {len(train_idx)} ({100*len(train_idx)/len(df_agg):.1f}%)")
    logger.info(f"Val patients:                {len(val_idx)} ({100*len(val_idx)/len(df_agg):.1f}%)")
    logger.info("PCA reduction complete!")

    
if __name__ == "__main__":
    main()