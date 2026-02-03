import numpy as np
import pandas as pd
import yaml
import logging
from pathlib import Path
from datetime import datetime
import joblib
from sklearn.metrics import (
    confusion_matrix, classification_report, 
    balanced_accuracy_score, f1_score, roc_auc_score
)
import matplotlib.pyplot as plt
import seaborn as sns

def setup_logging(log_dir="logs"):
    """Configure logging for the pipeline."""
    Path(log_dir).mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = Path(log_dir) / f"pipeline_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path="configs/config.yaml"):
    """Load configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def identify_feature_columns(df):
    """
    Identify feature columns from your dataframe.
    Excludes metadata and ID columns.
    """
    # Metadata columns to exclude
    metadata_cols = [
        'case_id', 'label', 'tile_x', 'tile_y', 'tile_id', 
        'x_start', 'y_start', 'x_end', 'y_end', 'width', 'height',
        'area', 'coverage_pct', 'is_partial', 'is_edge_right', 
        'is_edge_bottom', 'group'
    ]
    
    # Get all numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Feature columns = numeric columns - metadata
    feature_cols = [col for col in numeric_cols if col not in metadata_cols]
    
    return feature_cols

def encode_labels(labels):
    """
    Encode string labels to integers.
    
    Handles multiple label formats:
    - 'MSS/TMB-H', 'MSS/TMB-L', 'MSI'
    - 'mss_tmb-h', 'mss_tmb-l', 'msi' (lowercase with underscore)
    - 'MSS_TMB-H', 'MSS_TMB-L', 'MSI' (uppercase with underscore)
    
    Returns: encoded labels and mapping dictionary
    """
    # Normalize labels to standard format
    def normalize_label(label):
        """Normalize label to standard format."""
        if pd.isna(label):
            raise ValueError("Found NaN/missing label values")
        
        label_str = str(label).strip().upper().replace('_', '/').replace(' ', '')
        
        # Map variations to standard format
        label_mapping = {
            'MSS/TMB-L': 'MSS/TMB-L',
            'MSS/TMB-H': 'MSS/TMB-H',
            'MSI-H':     'MSI-H',
        }
        
        if label_str in label_mapping:
            return label_mapping[label_str]
        else:
            raise ValueError(f"Unknown label format: '{label}' (normalized to '{label_str}')")
    
    # Normalize all labels
    normalized_labels = [normalize_label(label) for label in labels]
    
    # Create mapping
    label_map = {
        'MSS/TMB-H': 0,
        'MSS/TMB-L': 1,
        'MSI-H': 2
    }
    
    # Encode
    encoded = np.array([label_map[label] for label in normalized_labels])
    
    return encoded, label_map


def compute_class_weights(y):
    """Compute class weights for imbalanced data."""
    from sklearn.utils.class_weight import compute_class_weight
    classes = np.unique(y)
    weights = compute_class_weight('balanced', classes=classes, y=y)
    return dict(zip(classes, weights))

def save_results(results, save_path):
    """Save results to disk."""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results, save_path)


def plot_confusion_matrix(y_true, y_pred, classes, save_path, model_name=None):
    """Plot and save confusion matrix with consistent styling."""
    cm = confusion_matrix(y_true, y_pred)
    
    #  Helper Functions
    def extract_strategy(model_name):
        if 'class_weight' in model_name:
            return 'class_weight'
        elif 'smote' in model_name and 'combined' not in model_name:
            return 'smote'
        elif 'combined' in model_name:
            return 'combined'
        else:
            return model_name.rsplit('_', 1)[-1]
    
    def extract_model_type(model_name):
        for suffix in ['_class_weight', '_smote', '_combined']:
            if model_name.endswith(suffix):
                return model_name.replace(suffix, '')
        return model_name
    
    model_name_map = {
        'logistic_regression': 'Logistic Regression',
        'random_forest': 'Random Forest',
        'xgboost': 'XGBoost',
        'mlp': 'MLP'
    }
    
    strategy_map = {
        'combined': 'SMOTE-Tomek',
        'smote': 'SMOTE',
        'class_weight': 'Class Weight'
    }
    
    def format_model_label(model_name):
        model_type = extract_model_type(model_name)
        model_type_readable = model_name_map.get(model_type, model_type)
        strategy = extract_strategy(model_name)
        strategy_readable = strategy_map.get(strategy, strategy)
        return f'{model_type_readable} ({strategy_readable})'
    
    #  Plotting Code 
    plt.figure(figsize=(8, 6))

    ax = sns.heatmap(cm, annot=False, fmt='d', cmap='YlGnBu', 
                     xticklabels=classes, yticklabels=classes, 
                     cbar_kws={'label': 'Count'},
                     linewidths=0.5)
    
    # Create title with model name if provided
    if model_name:
        model_label = format_model_label(model_name)
        title = f'Confusion Matrix: {model_label}'
    else:
        title = 'Confusion Matrix'
    
    plt.title(title, fontsize=18, fontweight='bold', pad=20)
    plt.ylabel('True Label', fontsize=16, fontweight='bold')
    plt.xlabel('Predicted Label', fontsize=16, fontweight='bold')
    
    # Add count and percentages with adaptive text color
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    
    # Get the colormap and normalization for determining text color
    norm = plt.Normalize(vmin=cm.min(), vmax=cm.max())
    
    for i in range(len(classes)):
        for j in range(len(classes)):
            # Determine text color based on cell darkness
            cell_value = cm[i, j]
            normalized_value = norm(cell_value)
            
            # Use white text for darker cells 
            text_color = 'white' if normalized_value > 0.5 else 'black'
            
            text = f'{cm[i, j]}\n({cm_norm[i, j]:.1%})'
            
            # Internal Text Size 
            plt.text(j + 0.5, i + 0.5, text, 
                     ha='center', va='center', 
                     fontsize=16, fontweight='bold',
                     color=text_color)
    
    # Group Labels
    ax.set_xticklabels(classes, fontsize=14, ha='center')
    ax.set_yticklabels(classes, fontsize=14, rotation=0)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    
def evaluate_model(y_true, y_pred, y_pred_proba, classes):
    """Comprehensive model evaluation."""
    metrics = {
        'balanced_accuracy': balanced_accuracy_score(y_true, y_pred),
        'f1': f1_score(y_true, y_pred, average='macro'),
        'weighted_f1': f1_score(y_true, y_pred, average='weighted'),
        'per_class_f1': f1_score(y_true, y_pred, average=None),
    }
    
    # ROC-AUC per class (one-vs-rest)
    try:
        metrics['roc_auc_ovr'] = roc_auc_score(
            y_true, y_pred_proba, 
            multi_class='ovr', 
            average='macro'
        )
        metrics['roc_auc_per_class'] = roc_auc_score(
            y_true, y_pred_proba, 
            multi_class='ovr', 
            average=None
        )
    except Exception as e:
        metrics['roc_auc_ovr'] = None
        metrics['roc_auc_per_class'] = None
    
    # Classification report
    metrics['classification_report'] = classification_report(
        y_true, y_pred, target_names=classes, output_dict=True
    )
    
    # Confusion matrix
    metrics['confusion_matrix'] = confusion_matrix(y_true, y_pred)
    
    return metrics
