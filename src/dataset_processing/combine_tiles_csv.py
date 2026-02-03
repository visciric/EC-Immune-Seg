import pandas as pd
from pathlib import Path
import argparse

def process_result_directory(result_dir, label):
    tile_data_dir = Path(result_dir) / 'processed' / 'tile_data'
    if not tile_data_dir.exists():
        return None
    csv_files = list(tile_data_dir.glob('*_tiles.csv'))
    if not csv_files:
        return None
    dfs = []
    for csv_file in csv_files:
        case_id = csv_file.name.replace('_tiles.csv', '')
        df = pd.read_csv(csv_file)
        df.insert(0, 'label', label)
        df.insert(0, 'case_id', case_id)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results_dirs', nargs='+', required=True)
    parser.add_argument('--labels', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if len(args.results_dirs) != len(args.labels):
        print("ERROR: Directories and labels count mismatch")
        return 1
    all_dfs = []
    for result_dir, label in zip(args.results_dirs, args.labels):
        df = process_result_directory(result_dir, label)
        if df is not None:
            all_dfs.append(df)
    if not all_dfs:
        print("ERROR: No data found")
        return 1
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df.to_csv(args.output, index=False)
    print(f"SUCCESS: {len(combined_df):,} rows, {combined_df['case_id'].nunique()} cases")
    return 0

if __name__ == '__main__':
    exit(main())