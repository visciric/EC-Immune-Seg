"""Histopathology UMAP Pipeline - Inflammatory & Molecular Subgroups"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from umap import UMAP
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
args = parser.parse_args()

INPUT_CSV = args.input


class Config:
    """Configuration parameters for the pipeline"""
    
    OUTPUT_DIR = Path("clustering_results")
    
    # Feature columns to use for embedding 
    FEATURE_COLUMNS = [
        'area', 'coverage_pct', 'nolabel', 'neoplastic', 'inflammatory',
        'connective', 'necrosis', 'non_neoplastic', 'total_nuclei',
        'neoplastic_pct', 'inflammatory_pct', 'connective_pct',
        'necrosis_pct', 'non_neoplastic_pct', 'neoplastic_normalized',
        'inflammatory_normalized', 'connective_normalized',
        'necrosis_normalized', 'non_neoplastic_normalized', 'total_normalized'
    ]
    
    # Columns to exclude from auto-detection
    EXCLUDE_COLUMNS = [
        'tile_x', 'tile_y', 'tile_id', 'x_start', 'y_start',
        'x_end', 'y_end', 'width', 'height', 'is_partial',
        'is_edge_right', 'is_edge_bottom'
    ]
    
    # UMAP parameters
    UMAP_N_NEIGHBORS = 15
    UMAP_MIN_DIST = 0.5
    UMAP_N_COMPONENTS = 2
    UMAP_METRIC = "euclidean"
    UMAP_RANDOM_STATE = 8340
    
    # Visualization
    FIGURE_SIZE = (10, 8)
    DPI = 300
    GROUP_COLORS = {
        'MSS/TMB-H': '#d62728',  # Red
        'MSS/TMB-L': '#1f77b4',  # Blue
        'MSI-H': '#2ca02c'       # Green
    }


def load_data(csv_path):
    """Load CSV data and perform initial checks"""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} tiles from {df['case_id'].nunique()} cases")
    
    if 'group' in df.columns:
        print(f"Molecular subgroups: {df['group'].value_counts().to_dict()}")
    
    return df


def preprocess(df, config):
    """Clean and standardize the data"""
  
    # Identify numerical columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Try to use predefined feature columns
    feature_cols = [col for col in config.FEATURE_COLUMNS if col in numeric_cols]
    
    # If none found, auto-detect
    if not feature_cols:
        feature_cols = [col for col in numeric_cols 
                       if col not in config.EXCLUDE_COLUMNS]
    
    # Extract feature matrix
    X = df[feature_cols].values
    
    # Handle missing values
    if np.isnan(X).sum() > 0:
        imputer = SimpleImputer(strategy='median')
        X = imputer.fit_transform(X)
    
    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled, feature_cols


def run_umap(X, config):
    """Run UMAP dimensionality reduction"""
    umap_model = UMAP(
        n_neighbors=config.UMAP_N_NEIGHBORS,
        min_dist=config.UMAP_MIN_DIST,
        n_components=config.UMAP_N_COMPONENTS,
        metric=config.UMAP_METRIC,
        random_state=config.UMAP_RANDOM_STATE,
        verbose=True
    )
    
    umap_embedding = umap_model.fit_transform(X)
    
    return umap_embedding, umap_model


def visualize_tile_embeddings(df, umap_embedding, config):
    """Generate tile-level UMAP visualizations"""
  
    output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set plotting style
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except:
            plt.style.use('seaborn-whitegrid')
    
    # Plot 1 UMAP colored by inflammatory cells
    inflammatory_col = None
    for col in ['inflammatory_pct', 'inflammatory_normalized', 'inflammatory']:
        if col in df.columns:
            inflammatory_col = col
            break
    
    if inflammatory_col:
        fig, ax = plt.subplots(figsize=(config.FIGURE_SIZE))
        scatter = ax.scatter(umap_embedding[:, 0], umap_embedding[:, 1],
                           c=df[inflammatory_col], cmap='OrRd', 
                           alpha=0.8, s=10, edgecolors='none')
        
        ax.set_xlabel('UMAP 1', fontsize=12)
        ax.set_ylabel('UMAP 2', fontsize=12)
        ax.set_title('Tile-Level UMAP - Colored by Inflammatory Cells', 
                     fontsize=14, fontweight='bold')
        
        plt.colorbar(scatter, ax=ax, label=f'Inflammatory [%]')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'umap_by_inflammatory.png', dpi=config.DPI, bbox_inches='tight')
        plt.close()
    else:
        print("Warning: No inflammatory column found")
    
    # Plot 2: UMAP colored by molecular subgroups
    if 'group' in df.columns:
        fig, ax = plt.subplots(figsize=config.FIGURE_SIZE)

        # Define plotting order 
        plot_order = ['MSS/TMB-L', 'MSI-H', 'MSS/TMB-H']
        
        for group in plot_order:
            if group in df['group'].values:
                mask = df['group'] == group
                ax.scatter(umap_embedding[mask, 0], umap_embedding[mask, 1],
                        c=config.GROUP_COLORS.get(group, 'gray'),
                        label=group, alpha=0.6, s=10, edgecolors='none')
        
        ax.set_xlabel('UMAP 1', fontsize=12)
        ax.set_ylabel('UMAP 2', fontsize=12)
        ax.set_title('Tile-Level UMAP - Colored by Molecular Subgroup', 
                     fontsize=14, fontweight='bold')
        
        ax.legend(markerscale=2)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'umap_by_subgroup.png', dpi=config.DPI, bbox_inches='tight')
        plt.close()
    else:
        print("Warning: No 'group' column found for molecular subgroups")


def aggregate_case_level(df, config):
    """Aggregate tile embeddings to case level"""
    print("Aggregating to case level...")
    
    # Feature columns for re-embedding
    feature_cols = [col for col in df.columns 
                   if ('_pct' in col or '_normalized' in col or col in ['area', 'coverage_pct', 'total_nuclei'])
                   and col in df.columns]
    
    # Aggregate tiles by case
    agg_dict = {
        'umap_x': 'mean',
        'umap_y': 'mean',
        **{col: 'mean' for col in feature_cols}
    }
    
    if 'group' in df.columns:
        agg_dict['group'] = 'first'
    
    case_agg = df.groupby('case_id').agg(agg_dict).reset_index()
    
    case_agg.rename(columns={
        'umap_x': 'case_umap_x', 
        'umap_y': 'case_umap_y'
    }, inplace=True)
    
    # Re-embed case features using UMAP
    if feature_cols:
        X_case = StandardScaler().fit_transform(case_agg[feature_cols].values)
        case_umap = UMAP(
            n_neighbors=min(15, len(case_agg)-1), 
            min_dist=0.1, 
            n_components=2, 
            random_state=42
        )
        case_embedding = case_umap.fit_transform(X_case)
        case_agg['case_umap_reembedded_x'] = case_embedding[:, 0]
        case_agg['case_umap_reembedded_y'] = case_embedding[:, 1]

    return case_agg


def visualize_case_level(case_df, config):
    """Generate case-level visualizations"""
    output_dir = config.OUTPUT_DIR
   
    # Plot 3: Case-level UMAP from tile means
    fig, ax = plt.subplots(figsize=config.FIGURE_SIZE)
    for group in sorted(case_df['group'].unique()):
        mask = case_df['group'] == group
        ax.scatter(case_df[mask]['case_umap_x'],
                  case_df[mask]['case_umap_y'],
                  c=config.GROUP_COLORS.get(group, 'gray'),
                  label=group, alpha=0.8, s=150, 
                  edgecolors='black', linewidth=0.5)
   
    ax.set_xlabel('Case UMAP 1 (from tile means)', fontsize=12)
    ax.set_ylabel('Case UMAP 2 (from tile means)', fontsize=12)
    ax.set_title('Case-Level UMAP (Averaged from Tile Embeddings)',
                 fontsize=14, fontweight='bold')
    ax.legend(markerscale=1)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'case_umap_by_group.png', dpi=config.DPI, bbox_inches='tight')
    plt.close()
    
    # Plot 4: Case-level UMAP re-embedded
    if 'case_umap_reembedded_x' in case_df.columns:
        fig, ax = plt.subplots(figsize=config.FIGURE_SIZE)
        for group in sorted(case_df['group'].unique()):
            mask = case_df['group'] == group
            ax.scatter(case_df[mask]['case_umap_reembedded_x'],
                      case_df[mask]['case_umap_reembedded_y'],
                      c=config.GROUP_COLORS.get(group, 'gray'),
                      label=group, alpha=0.8, s=150, 
                      edgecolors='black', linewidth=0.5)
        
        ax.set_xlabel('Case UMAP 1 (re-embedded)', fontsize=12)
        ax.set_ylabel('Case UMAP 2 (re-embedded)', fontsize=12)
        ax.set_title('Case-Level UMAP (Re-embedded from Case Features)',
                     fontsize=14, fontweight='bold')
        
        ax.legend(markerscale=1)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'case_umap_reembedded.png', dpi=config.DPI, bbox_inches='tight')
        plt.close()

def main():
    """Main pipeline execution"""
    print("HISTOPATHOLOGY UMAP ANALYSIS")
   
    config = Config()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = load_data(INPUT_CSV)
    
    # Sample if dataset is too large
    if len(df) > 100000:
        print(f"\nSampling {len(df):,} tiles -> 100,000...")
        df = df.sample(n=100000, random_state=8340)
    
    # Preprocess
    X_scaled, feature_cols = preprocess(df, config)
    
    # Run UMAP
    umap_embedding, umap_model = run_umap(X_scaled, config)
    df['umap_x'] = umap_embedding[:, 0]
    df['umap_y'] = umap_embedding[:, 1]
    
    # Visualize tile-level
    visualize_tile_embeddings(df, umap_embedding, config)
    
    # Aggregate to case level
    case_df = aggregate_case_level(df, config)
    
    # Visualize case-level
    visualize_case_level(case_df, config)
    
    # Save results
    df.to_csv(config.OUTPUT_DIR / 'tile_embeddings.csv', index=False)
    
    case_df.to_csv(config.OUTPUT_DIR / 'case_embeddings.csv', index=False)
    
    print("ANALYSIS COMPLETE")
    print(f"Results saved to: {config.OUTPUT_DIR.absolute()}")
    
    return df, case_df

if __name__ == "__main__":
    tile_df, case_df = main()