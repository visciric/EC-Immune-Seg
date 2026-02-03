"""
Model Evaluation and Comparison Script

Evaluates all trained models and creates comprehensive comparison reports.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc
import logging

sys.path.append(str(Path(__file__).parent))
from utils import (
    setup_logging, load_config, evaluate_model, 
    plot_confusion_matrix
)


def load_pca_data(split='test'):
    """Load PCA-transformed data."""
    features_path = f'data/processed/{split}/features.npy'
    labels_path = f'data/processed/{split}/labels.npy'
    
    X = np.load(features_path)
    y = np.load(labels_path)
    
    return X, y

def evaluate_all_models():
    """Evaluate all trained models on validation set."""
    logger = logging.getLogger(__name__)
    config = load_config()
    
    # Load test data
    X_val, y_val = load_pca_data('val')
    
    # Load label mapping
    label_map = joblib.load('ml_results/models/label_map.pkl')
    classes = list(label_map.keys())
    
    model_files = list(Path('ml_results/models').glob('*_*.pkl'))
    model_files = [
        f for f in model_files 
        if f.stem not in ['scaler', 'pca', 'label_map', 'feature_columns', 
                          'original_feature_columns', 'aggregated_feature_columns']
    ]
    
    all_results = []
    all_predictions = {}
    
    for i, model_file in enumerate(model_files, 1):
        model_id = model_file.stem
       
        try:
            # Load model
            model = joblib.load(model_file)
            
            # Predictions
            y_pred = model.predict(X_val)
            
            # Check if model supports predict_proba
            try:
                y_pred_proba = model.predict_proba(X_val)
            except AttributeError:
                logger.warning(f"  {model_id} doesn't support predict_proba")
                y_pred_proba = None
            
            # Evaluate
            metrics = evaluate_model(y_val, y_pred, y_pred_proba, classes)
            
            # Save confusion matrix
            cm_path = f'ml_results/figures/cm_{model_id}.png'
            plot_confusion_matrix(y_val, y_pred, classes, cm_path, model_name=model_id)
            
            # Store predictions
            all_predictions[model_id] = {
                'y_pred': y_pred,
                'y_pred_proba': y_pred_proba
            }
            
            # Compile results
            result = {
                'model': model_id,
                'balanced_accuracy': metrics['balanced_accuracy'],
                'f1': metrics['f1'],
                'weighted_f1': metrics['weighted_f1'],
                'roc_auc_ovr': metrics['roc_auc_ovr'],
            }
            
            # Add per-class F1
            for i, cls in enumerate(classes):
                result[f'f1_{cls}'] = metrics['per_class_f1'][i]
            
            # Add per-class precision and recall
            for cls in classes:
                cls_metrics = metrics['classification_report'][cls]
                result[f'precision_{cls}'] = cls_metrics['precision']
                result[f'recall_{cls}'] = cls_metrics['recall']
            
            # Add per-class ROC-AUC
            if metrics['roc_auc_per_class'] is not None:
                for i, cls in enumerate(classes):
                    result[f'roc_auc_{cls}'] = metrics['roc_auc_per_class'][i]
            
            all_results.append(result)
            
            logger.info(f"Balanced Acc: {metrics['balanced_accuracy']:.4f}")
            logger.info(f"F1: {metrics['f1']:.4f}")
            if metrics['roc_auc_ovr']:
                logger.info(f"ROC-AUC: {metrics['roc_auc_ovr']:.4f}")
            
        except Exception as e:
            logger.error(f"Error evaluating {model_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Create results DataFrame
    df_results = pd.DataFrame(all_results)
    
    if len(df_results) == 0:
        logger.error("No models were successfully evaluated!")
        return None
    
    # Sort by F1
    df_results = df_results.sort_values('f1', ascending=False)
    
    # Save results
    df_results.to_csv('ml_results/evaluation_results.csv', index=False)
        
    # Identify best model
    best_model = df_results.iloc[0]
    logger.info("BEST MODEL")
    logger.info(f"Model:            {best_model['model']}")
    logger.info(f"F1:         {best_model['f1']:.4f}")
    logger.info(f"Balanced Acc:     {best_model['balanced_accuracy']:.4f}")
    logger.info(f"Weighted F1:      {best_model['weighted_f1']:.4f}")
    if best_model['roc_auc_ovr'] is not None:
        logger.info(f"ROC-AUC (OvR):    {best_model['roc_auc_ovr']:.4f}")
    
    logger.info(f"\nPer-class F1 scores:")
    for cls in classes:
        logger.info(f"  {cls:15s}: {best_model[f'f1_{cls}']:.4f}")
    
    # Create comparison plots
    create_comparison_plots(df_results, classes)
    
    # Create ROC curves for best models
    create_roc_curves(all_predictions, y_val, df_results, classes)
    
    return df_results

def create_comparison_plots(df_results, classes):
    """Create comprehensive comparison plots."""
    
    # Extract model names and strategies
    df_results = df_results.copy()
    
    def extract_strategy(model_name):
        if 'class_weight' in model_name:
            return 'class_weight'
        elif 'smote' in model_name and 'combined' not in model_name:
            return 'smote'
        elif 'combined' in model_name:
            return 'combined'
        else:
            return model_name.rsplit('_', 1)[-1]
    
    df_results['strategy'] = df_results['model'].apply(extract_strategy)
    
    def extract_model_type(model_name):
        for suffix in ['_class_weight', '_smote', '_combined']:
            if model_name.endswith(suffix):
                return model_name.replace(suffix, '')
        return model_name
    
    df_results['model_type'] = df_results['model'].apply(extract_model_type)
    
    # Model Mapping
    model_name_map = {
        'logistic_regression': 'Logistic Regression',
        'random_forest': 'Random Forest',
        'xgboost': 'XGBoost',
        'mlp': 'MLP'
    }
    df_results['model_type'] = df_results['model_type'].map(model_name_map)
    
    # Clean readable strategy names
    strategy_map = {
        'combined': 'SMOTE-Tomek',
        'smote': 'SMOTE',
        'class_weight': 'Class Weight'
    }
    
    df_results['strategy'] = df_results['strategy'].map(strategy_map)
        
    # Strategy comparison heatmap  
    pivot_data = df_results.pivot_table(
        values='f1',
        index='model_type',
        columns='strategy',
        aggfunc='mean'
    )
    
    column_order = ['Class Weight', 'SMOTE', 'SMOTE-Tomek']
    available_columns = [col for col in column_order if col in pivot_data.columns]
    pivot_data = pivot_data[available_columns]
    
    plt.figure(figsize=(10, 8))
    ax = sns.heatmap(
        pivot_data,
        annot=True,
        fmt='.3f',
        cmap='YlGnBu',
        cbar_kws={'label': 'F1 Score'},
        linewidths=0.5,
        annot_kws={'size': 14, 'fontweight': 'bold'}
    )
    plt.title('F1 Score by Model Type and Imbalance Strategy', fontsize=16, fontweight='bold')
    plt.xlabel('Imbalance Strategy', fontsize=14, fontweight='bold')
    plt.ylabel('Model Type', fontsize=14, fontweight='bold')
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12, rotation=0)
    plt.tight_layout()
    plt.savefig('ml_results/figures/strategy_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    f1_cols = [f'f1_{cls}' for cls in classes]
    top_models = df_results.nlargest(5, 'f1')
    
    # Formatting function for labels 
    def format_model_label(model_name):
        model_type = extract_model_type(model_name)
        model_type_readable = model_name_map.get(model_type, model_type)
        strategy = extract_strategy(model_name)
        strategy_readable = strategy_map.get(strategy, strategy)
        return f'{model_type_readable}\n({strategy_readable})'
    
    top_models['model_label'] = top_models['model'].apply(format_model_label)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(top_models))
    width = 0.25
    
    colors = ['#3498db', '#e74c3c', '#2ecc71']
    
    for i, cls in enumerate(classes):
        values = top_models[f'f1_{cls}'].values
        bars = ax.bar(x + i*width, values, width, label=cls, color=colors[i])
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{height:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax.set_ylabel('F1 Score', fontsize=12, fontweight='bold')
    ax.set_title('Per-Class F1 Scores for Top 5 Models', fontsize=14, fontweight='bold')
    
    # Rotate ticks for better readability
    ax.set_xticks(x + width)
    ax.set_xticklabels(top_models['model_label'], rotation=45, ha='right', fontsize=11)
    
    ax.legend(title='Molecular Subclass', fontsize=10, loc='upper right', 
              bbox_to_anchor=(1.0, 1.0))
    
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim([0, 1.1]) 
    
    plt.tight_layout()
    plt.savefig('ml_results/figures/per_class_performance.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_roc_curves(all_predictions, y_val, df_results, classes):
    """Create both combined and individual ROC curve plots."""
    
    # Get top 5 models
    top_models = df_results.nlargest(5, 'f1')['model'].tolist()
    
    # Helper functions for consistent naming
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
    
    # Model and strategy mappings
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
    
    # COMBINED ROC PLOT (3 subplots in one figure)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colors = plt.cm.Set2(np.linspace(0, 1, len(top_models)))
    
    for class_idx, (ax, class_name) in enumerate(zip(axes, classes)):
        for model_id, color in zip(top_models, colors):
            if model_id not in all_predictions:
                continue
            
            y_pred_proba = all_predictions[model_id]['y_pred_proba']
            if y_pred_proba is None:
                continue
            
            # Compute ROC curve
            y_true_binary = (y_val == class_idx).astype(int)
            y_score = y_pred_proba[:, class_idx]
            
            fpr, tpr, _ = roc_curve(y_true_binary, y_score)
            roc_auc = auc(fpr, tpr)
            
            model_label = format_model_label(model_id)
            ax.plot(fpr, tpr, color=color, lw=2, 
                   label=f'{model_label} (AUC={roc_auc:.3f})')
        
        # Plot diagonal
        ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.3)
        
        ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
        ax.set_title(f'ROC Curve: {class_name}', fontsize=13, fontweight='bold')
        ax.legend(loc='lower right', fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.tick_params(axis='both', which='major', labelsize=10)
    
    plt.tight_layout()
    plt.savefig('ml_results/figures/roc_curves.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # INDIVIDUAL ROC PLOTS (one figure per class)
    for class_idx, class_name in enumerate(classes):
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        
        colors = plt.cm.Set2(np.linspace(0, 1, len(top_models)))
        
        for model_id, color in zip(top_models, colors):
            if model_id not in all_predictions:
                continue
            
            y_pred_proba = all_predictions[model_id]['y_pred_proba']
            if y_pred_proba is None:
                continue
            
            # Compute ROC curve
            y_true_binary = (y_val == class_idx).astype(int)
            y_score = y_pred_proba[:, class_idx]
            
            fpr, tpr, _ = roc_curve(y_true_binary, y_score)
            roc_auc = auc(fpr, tpr)
            
            model_label = format_model_label(model_id)
            ax.plot(fpr, tpr, color=color, lw=3, 
                   label=f'{model_label} (AUC={roc_auc:.3f})')
        
        # Plot diagonal
        ax.plot([0, 1], [0, 1], 'k--', lw=1.5, alpha=0.4)
        
        ax.set_xlabel('False Positive Rate', fontsize=14, fontweight='bold')
        ax.set_ylabel('True Positive Rate', fontsize=14, fontweight='bold')
        ax.set_title(f'ROC Curve: {class_name}', fontsize=16, fontweight='bold', pad=15)
        ax.legend(loc='lower right', fontsize=12, framealpha=0.95)
        ax.grid(alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.tick_params(axis='both', which='major', labelsize=12)
        
        plt.tight_layout()
        
        # Save with class name in filename
        class_name_safe = class_name.replace('/', '_')  # Replace / with _ for filename
        plt.savefig(f'ml_results/figures/roc_curve_{class_name_safe}.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
   

def create_detailed_report(df_results, classes):
    """Create detailed markdown report."""
    logger = logging.getLogger(__name__)
    
    report_path = 'ml_results/evaluation_report.md'
    
    with open(report_path, 'w') as f:
        f.write("# Model Evaluation Report\n\n")
        f.write("## Summary\n\n")
        
        f.write(f"- Total models evaluated: {len(df_results)}\n")
        f.write(f"- Number of classes: {len(classes)}\n")
        f.write(f"- Classes: {', '.join(classes)}\n\n")
        
        # Best model
        best = df_results.iloc[0]
        f.write("## Best Model\n\n")
        f.write(f"**{best['model']}**\n\n")
        f.write(f"- F1: {best['f1']:.4f}\n")
        f.write(f"- Balanced Accuracy: {best['balanced_accuracy']:.4f}\n")
        f.write(f"- Weighted F1: {best['weighted_f1']:.4f}\n")
        if best['roc_auc_ovr'] is not None:
            f.write(f"- ROC-AUC (OvR): {best['roc_auc_ovr']:.4f}\n")
        f.write("\n### Per-Class Performance\n\n")
        f.write("| Class | F1 | Precision | Recall | ROC-AUC |\n")
        f.write("|-------|----|-----------|---------|---------|\n")
        for cls in classes:
            f1 = best[f'f1_{cls}']
            prec = best[f'precision_{cls}']
            rec = best[f'recall_{cls}']
            roc_col = f'roc_auc_{cls}'
            roc = best[roc_col] if roc_col in best else 'N/A'
            roc_str = f"{roc:.4f}" if isinstance(roc, float) else roc
            f.write(f"| {cls} | {f1:.4f} | {prec:.4f} | {rec:.4f} | {roc_str} |\n")
       
               
        # Top 5 models
        f.write("\n## Top 5 Models\n\n")
        f.write("| Rank | Model | F1 | Balanced Acc | ROC-AUC |\n")
        f.write("|------|-------|----------|--------------|----------|\n")
        
        for i, row in df_results.head(5).iterrows():
            roc = row['roc_auc_ovr'] if row['roc_auc_ovr'] is not None else 'N/A'
            roc_str = f"{roc:.4f}" if isinstance(roc, float) else roc
            f.write(f"| {i+1} | {row['model']} | {row['f1']:.4f} | "
                   f"{row['balanced_accuracy']:.4f} | {roc_str} |\n")
        
        f.write("\n## Model Insights\n\n")
        
        # Strategy analysis
        df_results_copy = df_results.copy()
        df_results_copy['strategy'] = df_results_copy['model'].str.rsplit('_', n=1).str[1]
        strategy_perf = df_results_copy.groupby('strategy')['f1'].mean().sort_values(ascending=False)
        
        f.write("### Performance by Imbalance Strategy\n\n")
        for strategy, score in strategy_perf.items():
            f.write(f"- **{strategy}**: {score:.4f}\n")
        
        # Model type analysis
        df_results_copy['model_type'] = df_results_copy['model'].str.rsplit('_', n=1).str[0]
        model_perf = df_results_copy.groupby('model_type')['f1'].mean().sort_values(ascending=False)
        
        f.write("\n### Performance by Model Type\n\n")
        for model_type, score in model_perf.items():
            f.write(f"- **{model_type}**: {score:.4f}\n")
    
    logger.info(f"Saved {report_path}")

def main():
    logger = setup_logging()

    logger.info("MODEL EVALUATION PIPELINE")
    
    # Create output directories
    Path('ml_results/figures').mkdir(parents=True, exist_ok=True)
    
    # Evaluate all models
    df_results = evaluate_all_models()
    
    if df_results is not None:
        # Load classes for report
        label_map = joblib.load('ml_results/models/label_map.pkl')
        classes = list(label_map.keys())
        
        # Create detailed report
        create_detailed_report(df_results, classes)
        

        logger.info("EVALUATION COMPLETE!")
        logger.info("\nResults saved to:")
        logger.info("  - ml_results/evaluation_results.csv")
        logger.info("  - ml_results/evaluation_report.md")
        logger.info("  - ml_results/figures/*.png")
    else:
        logger.error("Evaluation failed!")

if __name__ == "__main__":
    main()