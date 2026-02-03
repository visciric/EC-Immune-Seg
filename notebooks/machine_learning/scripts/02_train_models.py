"""
Model Training Script for Molecular Subclass Classification

Trains multiple models with different class imbalance strategies.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from imblearn.combine import SMOTETomek
from imblearn.under_sampling import RandomUnderSampler
import xgboost as xgb
from sklearn.model_selection import train_test_split

import joblib
from pathlib import Path
import sys
import time
import logging

sys.path.append(str(Path(__file__).parent))
from utils import setup_logging, load_config, compute_class_weights

def load_pca_data(split='train'):
    """Load PCA-transformed data."""    
    features_path = f'data/processed/{split}/features.npy'
    labels_path = f'data/processed/{split}/labels.npy'
    
    X = np.load(features_path)
    y = np.load(labels_path)
    
    return X, y

def apply_imbalance_strategy(X_train, y_train, strategy, config):
    """Apply class imbalance handling strategy."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"\nApplying strategy: {strategy}")
    
    if strategy == 'class_weight':
        # Return class weights for models that support it
        class_weights = compute_class_weights(y_train)
        return X_train, y_train, class_weights
    
    elif strategy == 'smote':
        # Apply SMOTE
        smote_params = config['imbalance']['smote']
        
        # Adjust k_neighbors if necessary
        min_class_size = min(np.bincount(y_train))
        k_neighbors = min(smote_params['k_neighbors'], min_class_size - 1)
        
        if k_neighbors < 1:
            class_weights = compute_class_weights(y_train)
            return X_train, y_train, class_weights
               
        smote = SMOTE(
            k_neighbors=k_neighbors,
            sampling_strategy=smote_params['sampling_strategy'],
            random_state=config['train']['random_state']
        )
        
        try:
            X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
            logger.info(f"After SMOTE: {dict(zip(*np.unique(y_resampled, return_counts=True)))}")
            return X_resampled, y_resampled, None
        
        except ValueError as e:
            class_weights = compute_class_weights(y_train)
            return X_train, y_train, class_weights
        
    else:
        # SMOTE + Tomek links
        min_class_size = min(np.bincount(y_train))
        k_neighbors = min(config['imbalance']['smote']['k_neighbors'], min_class_size - 1)
        
        if k_neighbors < 1:
            class_weights = compute_class_weights(y_train)
            return X_train, y_train, class_weights
        
        try:
            smote_tomek = SMOTETomek(
                smote=SMOTE(k_neighbors=k_neighbors, random_state=config['train']['random_state']),
                random_state=config['train']['random_state']
            )
            X_resampled, y_resampled = smote_tomek.fit_resample(X_train, y_train)
            return X_resampled, y_resampled, None
        except Exception as e:
            class_weights = compute_class_weights(y_train)
            return X_train, y_train, class_weights
    
    
def train_logistic_regression(X_train, y_train, class_weights, config):
    """Train Logistic Regression."""
    logger = logging.getLogger(__name__)
    logger.info("Training Logistic Regression")
    
    params = config['models']['logistic_regression'].copy()
    
    model = LogisticRegression(
        multi_class='multinomial',
        class_weight=class_weights if class_weights else 'balanced',
        **params
    )
    
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    
    logger.info(f"Trained in {train_time:.2f}s")
    return model, train_time

def train_random_forest(X_train, y_train, class_weights, config):
    """Train Random Forest."""
    logger = logging.getLogger(__name__)
    logger.info("Training Random Forest")
    
    params = config['models']['random_forest'].copy()
    
    model = RandomForestClassifier(
        class_weight=class_weights if class_weights else 'balanced',
        **params
    )
    
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    
    logger.info(f"  Trained in {train_time:.2f}s")
    return model, train_time


def train_xgboost(X_train, y_train, class_weights, config):
    """Train XGBoost (Simplified: No Early Stopping, uses 100% data)."""
    logger = logging.getLogger(__name__)
    logger.info("Training XGBoost")
    
    params = config['models']['xgboost'].copy()
    n_classes = len(np.unique(y_train))
    
    # Safety: Remove early_stopping_rounds if it was accidentally left in config
    params.pop('early_stopping_rounds', None)
    
    # Sample weights
    if class_weights:
        sample_weights = np.array([class_weights[y] for y in y_train])
    else:
        class_weights_auto = compute_class_weights(y_train)
        sample_weights = np.array([class_weights_auto[y] for y in y_train])
    
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=n_classes,
        eval_metric='mlogloss',
        **params
    )
    
    start_time = time.time()
    
    # TRAIN ON EVERYTHING (100% of X_train)
    model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)
    
    train_time = time.time() - start_time
    
    logger.info(f"  Trained in {train_time:.2f}s")
    return model, train_time

def train_mlp(X_train, y_train, class_weights, config):
    """Train MLP with early stopping."""
    logger = logging.getLogger(__name__)
    logger.info("Training MLP (Neural Network)")
    
    params = config['models']['mlp'].copy()
    hidden_layers = tuple(params.pop('hidden_layers'))
    
    # Ensure validation_fraction and n_iter_no_change are set if early_stopping is True
    if params.get('early_stopping', False):
        if 'validation_fraction' not in params:
            params['validation_fraction'] = 0.2
        if 'n_iter_no_change' not in params:
            params['n_iter_no_change'] = 20
    
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layers,
        **params  # This includes early_stopping from config
    )
    
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    
    logger.info(f"  Trained in {train_time:.2f}s")
    logger.info(f"  Converged: {model.n_iter_} iterations")
    
    # Only log best_loss_ if it exists and is not None
    if hasattr(model, 'best_loss_') and model.best_loss_ is not None:
        logger.info(f"  Best loss: {model.best_loss_:.4f}")
    
    return model, train_time

def train_single_model(model_name, strategy, X_train, y_train, config):
    """Train a single model with a specific imbalance strategy."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"Model: {model_name.upper()} | Strategy: {strategy.upper()}")
   
    try:
        # Apply imbalance strategy
        X_resampled, y_resampled, class_weights = apply_imbalance_strategy(
            X_train, y_train, strategy, config
        )
        
        # Model training functions
        trainers = {
            'logistic_regression': train_logistic_regression,
            'random_forest': train_random_forest,
            'xgboost': train_xgboost,
            'mlp': train_mlp
        }
        
        # Train model
        model, train_time = trainers[model_name](
            X_resampled, y_resampled, class_weights, config
        )
        
        if model is None: 
            return None
        
        # Save model
        model_path = f'ml_results/models/{model_name}_{strategy}.pkl'
        joblib.dump(model, model_path)
        logger.info(f"Model saved to {model_path}")
        
        return {
            'model_name': model_name,
            'strategy': strategy,
            'train_time': train_time,
            'n_train_samples': len(y_resampled),
            'model_path': model_path,
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"Error training {model_name} with {strategy}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            'model_name': model_name,
            'strategy': strategy,
            'train_time': 0,
            'n_train_samples': 0,
            'model_path': None,
            'status': 'failed',
            'error': str(e)
        }

def main():
    import logging
    logger = setup_logging()
    config = load_config()
   
    logger.info("MODEL TRAINING PIPELINE")
   
    # Create output directory
    Path('ml_results/models').mkdir(parents=True, exist_ok=True)
    
    # Load data
    X_train, y_train = load_pca_data('train')
    X_val, y_val = load_pca_data('val')
        
    logger.info(f"\nTraining set: {X_train.shape[0]} cases, {X_train.shape[1]} features")
    logger.info(f"Validation set: {X_val.shape[0]} cases, {X_val.shape[1]} features")
    
   
    # Models and strategies to train
    models = ['logistic_regression', 'random_forest', 'xgboost', 'mlp']

    strategies = config['imbalance']['strategies']
    
    logger.info(f"\nWill train {len(models)} models with {len(strategies)} strategies")
    logger.info(f"Total combinations: {len(models) * len(strategies)}")
    
    # Train all combinations
    results = []
    total_combinations = len(models) * len(strategies)
    current = 0
    
    start_time_total = time.time()
    
    for model_name in models:
        for strategy in strategies:
            current += 1
            logger.info(f"Progress: {current}/{total_combinations}")

            result = train_single_model(
                model_name, strategy, X_train, y_train, config
            )
            
            if result is not None:
                results.append(result)
    
    total_time = time.time() - start_time_total
    
    # Save training summary
    df_results = pd.DataFrame(results)
    df_results.to_csv('ml_results/training_summary.csv', index=False)
    
    logger.info("TRAINING COMPLETE!")
    logger.info(f"\n{df_results[['model_name', 'strategy', 'train_time', 'status']].to_string()}")
    
    # Summary statistics
    successful = df_results[df_results['status'] == 'success']
    
    logger.info(f"\nSuccessfully trained: {len(successful)}/{len(df_results)} models")
    logger.info(f"\nTotal training time: {total_time:.2f}s ({total_time/60:.2f} min)")
    logger.info(f"Average time per model: {successful['train_time'].mean():.2f}s")
    logger.info(f"Fastest model: {successful.loc[successful['train_time'].idxmin(), 'model_name']} "
                f"({successful['train_time'].min():.2f}s)")
    logger.info(f"Slowest model: {successful.loc[successful['train_time'].idxmax(), 'model_name']} "
                f"({successful['train_time'].max():.2f}s)")

if __name__ == "__main__":
    main()
    
    