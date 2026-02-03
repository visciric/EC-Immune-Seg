import argparse
from pathlib import Path
from io_utils import load_json_results, get_wsi_dimensions
from tile_analysis import calculate_tile_size_from_target, count_immune_cells_per_tile
from heatmap import create_heatmap
from export import create_tile_dataset_csv


def main():
    parser = argparse.ArgumentParser(description='Generate immune cell density heatmap from HoVer-Net results')
    parser.add_argument('--json', required=True, help='Path to HoVer-Net JSON output')
    parser.add_argument('--wsi', required=True, help='Path to WSI .svs file')
    parser.add_argument('--output', required=True, help='Output path for heatmap image')
    parser.add_argument('--csv', default=None, help='Output path for CSV dataset (optional)')
    parser.add_argument('--tile_size', type=int, default=None, help='Tile size in pixels (default: 270)')
    parser.add_argument('--target_tiles', type=int, default=None, help='Target number of tiles (overrides tile_size)')
    parser.add_argument('--wsi_alpha', type=float, default=1.0, help='WSI background transparency (0.0=invisible, 1.0=fully visible, default: 1.0)')
    
    args = parser.parse_args()
    
    print(f"Processing: {Path(args.json).name}")
    print(f"WSI: {Path(args.wsi).name}")
    print(f"WSI background alpha: {args.wsi_alpha}")
    print("=" * 60)
    
    wsi_dimensions = get_wsi_dimensions(args.wsi)
    
    if args.target_tiles:
        tile_size = calculate_tile_size_from_target(args.wsi, args.target_tiles)
    elif args.tile_size:
        tile_size = args.tile_size
        print(f"Using specified tile size: {tile_size}x{tile_size}")
    else:
        tile_size = 270
        print(f"Using default tile size: {tile_size}x{tile_size}")
    
    print("-" * 60)
    
    data = load_json_results(args.json)
    nuclei_data = data['nuc']
    mag = data.get('mag', 40)
    
    print(f"Magnification: {mag}x")
    print(f"Total nuclei in JSON: {len(nuclei_data)}")
    
    tile_counts = count_immune_cells_per_tile(nuclei_data, tile_size=tile_size, magnification=mag)
    
    heatmap = create_heatmap(tile_counts, args.wsi, args.output, tile_size=tile_size, wsi_alpha=args.wsi_alpha)
    
    if args.csv:
        print("-" * 60)
        df = create_tile_dataset_csv(nuclei_data, wsi_dimensions, args.csv, tile_size=tile_size)
    
    print("-" * 60)
    print("Done!")


if __name__ == '__main__':
    main()