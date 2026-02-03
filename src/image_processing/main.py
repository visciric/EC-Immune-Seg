import argparse
from pathlib import Path
from io_utils import auto_detect_format, get_wsi_info
from tile_analysis import calculate_tile_size_from_target, count_immune_cells_per_tile
from heatmap import create_heatmap
from export import create_tile_dataset_csv

def main():
    parser = argparse.ArgumentParser(description='Generate immune cell density heatmap from HoVer-Net/HoVerNext results')
    parser.add_argument('--input', required=True,
                       help='Path to HoVer-Net JSON or HoVerNext results directory')
    parser.add_argument('--wsi', required=True, help='Path to WSI .svs file')
    parser.add_argument('--output', required=True, help='Output path for heatmap image')
    parser.add_argument('--csv', default=None, help='Output path for CSV dataset (optional)')
    parser.add_argument('--tile_size', type=int, default=None, help='Tile size in pixels (default: 270)')
    parser.add_argument('--target_tiles', type=int, default=None,
                       help='Target number of tiles (overrides tile_size)')
    parser.add_argument('--wsi_alpha', type=float, default=1.0,
                       help='WSI background transparency (0.0=invisible, 1.0=fully visible, default: 1.0)')
    parser.add_argument('--magnification', type=int, default=None,
                       help='Magnification level (default: auto-detect from WSI metadata)')
    parser.add_argument('--colormap', type=str, default='green_yellow_red',
                       help='Colormap for heatmap (default: green_yellow_red). Options: colorblind_save)')
    parser.add_argument('--show_grid', action='store_true',
                       help='Show grid lines on heatmap')
   
    args = parser.parse_args()
   
    input_path = Path(args.input) 
    
    wsi_info = get_wsi_info(args.wsi)
    wsi_dimensions = wsi_info['dimensions']
    detected_magnification = wsi_info['magnification']
    detection_method = wsi_info['detection_method'] 
     
    if args.magnification is not None:
        magnification = args.magnification
        print(f"Overriding with user-specified magnification: {magnification}x")
    else:
        magnification = detected_magnification
        print(f"Using detected magnification: {magnification}x")
    
    format_type, data = auto_detect_format(args.input)
    
    data['mag'] = magnification
    
    if args.target_tiles:
        tile_size = calculate_tile_size_from_target(args.wsi, args.target_tiles)
    elif args.tile_size:
        tile_size = args.tile_size 
    else:
        tile_size = 270 
    
   
    nuclei_data = data['nuc']
    mag = data['mag']
    
    
    tile_counts = count_immune_cells_per_tile(nuclei_data, tile_size=tile_size, magnification=mag)
    
    heatmap = create_heatmap(tile_counts, args.wsi, args.output, tile_size=tile_size,
                            wsi_alpha=args.wsi_alpha, colormap=args.colormap,
                            show_grid=args.show_grid)
    
    if args.csv:
        df = create_tile_dataset_csv(nuclei_data, wsi_dimensions, args.csv, tile_size=tile_size)
   

if __name__ == '__main__':
    main()