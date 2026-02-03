import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Polygon
import openslide
import json
from pathlib import Path
from constants import CELL_TYPES, FONT_SIZES


CELL_TYPE_COLORS = {
    0: '#808080',  # nolabel - gray
    1: '#FF00FF',  # neoplastic - magenta
    2: '#00FF00',  # inflammatory - green
    3: '#0000FF',  # connective - blue
    4: '#FF0000',  # necrosis - red
    5: '#FFFF00',  # non_neoplastic - yellow
}

# Global cache for JSON data
_JSON_CACHE = {}


def load_cells_in_tile_from_json(json_path, tile_x, tile_y, tile_size):
    """Load all cells within a specific tile from HoVerNet JSON with contours"""
    json_path_str = str(json_path)
    
    # Check cache first
    if json_path_str in _JSON_CACHE:
        data = _JSON_CACHE[json_path_str]
    else:
        print(f"Loading JSON: {json_path} (this may take a moment for large files...)")
        with open(json_path, 'r') as f:
            data = json.load(f)
        _JSON_CACHE[json_path_str] = data
        print(f" JSON loaded and cached")
    
    tile_x_start = tile_x * tile_size
    tile_y_start = tile_y * tile_size
    tile_x_end = tile_x_start + tile_size
    tile_y_end = tile_y_start + tile_size
    
    cells_by_type = {i: [] for i in range(6)}
    cell_contours = []  # Store (contour, cell_type) tuples
    
    nuc_data = data.get('nuc', {})
    
    for cell_id, cell_info in nuc_data.items():
        centroid = cell_info.get('centroid', [])
        cell_type = cell_info.get('type', 0)
        contour = cell_info.get('contour', None)
        
        if len(centroid) != 2:
            continue
        
        x, y = centroid
        
        # Check if centroid is in tile
        if tile_x_start <= x < tile_x_end and tile_y_start <= y < tile_y_end:
            x_rel = x - tile_x_start
            y_rel = y - tile_y_start
            cells_by_type[cell_type].append((x_rel, y_rel))
            
            # Store contour if available
            if contour is not None and len(contour) > 0:
                # Convert to numpy array and adjust coordinates to tile-relative
                # HoVerNet contours are [[x, y], [x, y], ...]
                contour_array = np.array(contour, dtype=np.float32)
                
                # Adjust to tile-relative coordinates
                contour_array[:, 0] -= tile_x_start  # x coordinates
                contour_array[:, 1] -= tile_y_start  # y coordinates
                
                # Only include if contour is within tile bounds
                if (contour_array[:, 0].min() >= -10 and 
                    contour_array[:, 0].max() <= tile_size + 10 and
                    contour_array[:, 1].min() >= -10 and 
                    contour_array[:, 1].max() <= tile_size + 10):
                    cell_contours.append((contour_array, cell_type))
    
    return cells_by_type, cell_contours


def visualize_tile_with_cells(
    wsi_path,
    json_path,
    tile_x,
    tile_y,
    tile_size,
    output_path,
    show_centroids=True,
    show_boundaries=True,
    centroid_size=3,
    boundary_width=1.5,
    boundary_alpha=0.8,
    fill_alpha=0.0,
    wsi_alpha=1.0
):
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    
    slide = openslide.OpenSlide(wsi_path)
    wsi_width, wsi_height = slide.dimensions

    tile_x_start = tile_x * tile_size
    tile_y_start = tile_y * tile_size

    if tile_x_start >= wsi_width or tile_y_start >= wsi_height:
        print(f"ERROR: Tile ({tile_x}, {tile_y}) is outside WSI bounds")
        return

    tile_width = min(tile_size, wsi_width - tile_x_start)
    tile_height = min(tile_size, wsi_height - tile_y_start)

    tile_img = slide.read_region((tile_x_start, tile_y_start), 0, (tile_width, tile_height))
    tile_array = np.array(tile_img.convert("RGB"))
    slide.close()

    cells_by_type, cell_contours = load_cells_in_tile_from_json(json_path, tile_x, tile_y, tile_size)
    total_cells = sum(len(cells) for cells in cells_by_type.values())

    print(f"\n{'='*70}")
    print(f"Tile ({tile_x}, {tile_y}) analysis:")
    print(f"{'='*70}")
    print(f"Total cells: {total_cells}")
    print(f"Total contours: {len(cell_contours)}")
    for cell_type in range(6):
        if len(cells_by_type[cell_type]) > 0:
            print(f"  Type {cell_type} ({CELL_TYPES[cell_type]}): {len(cells_by_type[cell_type])} cells")

    fig, ax = plt.subplots(figsize=(14, 14), dpi=150)
    ax.imshow(tile_array, alpha=wsi_alpha)

    # Draw boundaries from contours
    if show_boundaries and len(cell_contours) > 0:
        print(f"Drawing {len(cell_contours)} cell boundaries...")
        for contour, cell_type in cell_contours:
            cell_color = CELL_TYPE_COLORS.get(cell_type, "#FFFFFF")
            
            # Draw boundary
            ax.plot(
                contour[:, 0],  # x coordinates
                contour[:, 1],  # y coordinates
                linewidth=boundary_width,
                color=cell_color,
                alpha=boundary_alpha,
            )
            
            # Fill if requested
            if fill_alpha > 0:
                polygon = Polygon(
                    contour,
                    facecolor=cell_color,
                    alpha=fill_alpha,
                    edgecolor='none'
                )
                ax.add_patch(polygon)

    # Draw centroids
    if show_centroids:
        for cell_type, cells in cells_by_type.items():
            if len(cells) == 0:
                continue

            color = CELL_TYPE_COLORS.get(cell_type, "#FFFFFF")

            for x, y in cells:
                circle = Circle(
                    (x, y),
                    centroid_size,
                    facecolor="none",        
                    edgecolor=color,          
                    linewidth=0.8,
                    alpha=0.9,
                )
                ax.add_patch(circle)

    # Legend
    legend_elements = []
    for cell_type, cells in cells_by_type.items():
        if len(cells) > 0:
            color = CELL_TYPE_COLORS[cell_type]
            label = f"{CELL_TYPES[cell_type]}: {len(cells)}"
            legend_elements.append(Patch(facecolor=color, edgecolor="white", label=label))

    ax.legend(
        handles=legend_elements,
        loc="upper right",
        fontsize=11,
        framealpha=0.95,
        fancybox=True,
    )

    wsi_name = Path(wsi_path).stem
    boundary_status = (
        "with boundaries" if (show_boundaries and len(cell_contours) > 0) else "centroids only"
    )
    title = f"{wsi_name}\nTile ({tile_x}, {tile_y}) - {total_cells} cells ({boundary_status})"
    ax.set_title(title, fontsize=FONT_SIZES["title"], weight="bold", pad=15)

    ax.set_xlim(0, tile_width)
    ax.set_ylim(tile_height, 0)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.5)

    scale_bar_length = 100
    ax.plot([20, 20 + scale_bar_length], [tile_height - 20, tile_height - 20], "w-", linewidth=4)
    ax.text(
        20 + scale_bar_length / 2,
        tile_height - 40,
        f"{scale_bar_length}px",
        color="white",
        ha="center",
        fontsize=11,
        weight="bold",
        bbox=dict(boxstyle="round", facecolor="black", alpha=0.7),
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def visualize_multiple_tiles(
    wsi_path,
    json_path,
    tile_coords,
    tile_size,
    output_dir,
    **kwargs
):
    """
    Efficiently visualize multiple tiles by loading JSON once.
    
    tile_coords: list of (tile_x, tile_y) tuples
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for tile_x, tile_y in tile_coords:
        output_path = output_dir / f"tile_{tile_x}_{tile_y}.png"
        visualize_tile_with_cells(
            wsi_path,
            json_path,
            tile_x,
            tile_y,
            tile_size,
            output_path,
            **kwargs
        )


def main():
    parser = argparse.ArgumentParser(description='Visualize cells in a specific tile (HoVerNet - JSON only)')
    parser.add_argument('--json', required=True, help='HoVerNet JSON file')
    parser.add_argument('--wsi', required=True, help='WSI file')
    parser.add_argument('--tile_x', type=int, help='Tile X coordinate (single tile mode)')
    parser.add_argument('--tile_y', type=int, help='Tile Y coordinate (single tile mode)')
    parser.add_argument('--tile_coords', type=str, help='Multiple tiles as "x1,y1;x2,y2;x3,y3"')
    parser.add_argument('--tile_size', type=int, default=896, help='Tile size (default: 896)')
    parser.add_argument('--output', required=True, help='Output image path (single tile) or directory (multiple tiles)')
    parser.add_argument('--centroid_size', type=int, default=3, help='Centroid size (default: 3)')
    parser.add_argument('--no_centroids', action='store_true', help='Hide centroids')
    parser.add_argument('--no_boundaries', action='store_true', help='Hide boundaries')
    parser.add_argument('--boundary_width', type=float, default=1.5, help='Boundary width (default: 1.5)')
    parser.add_argument('--boundary_alpha', type=float, default=0.8, help='Boundary transparency (0.0-1.0, default: 0.8)')
    parser.add_argument('--fill_alpha', type=float, default=0.0, help='Fill transparency (0.0-1.0, default: 0.0)')
    parser.add_argument('--wsi_alpha', type=float, default=1.0, help='WSI background transparency (0.0-1.0, default: 1.0)')
    
    args = parser.parse_args()

    kwargs = {
        'show_centroids': not args.no_centroids,
        'show_boundaries': not args.no_boundaries,
        'centroid_size': args.centroid_size,
        'boundary_width': args.boundary_width,
        'boundary_alpha': args.boundary_alpha,
        'fill_alpha': args.fill_alpha,
        'wsi_alpha': args.wsi_alpha
    }

    # Multiple tiles mode
    if args.tile_coords:
        tile_coords = []
        for coord_pair in args.tile_coords.split(';'):
            x, y = map(int, coord_pair.split(','))
            tile_coords.append((x, y))
        
        visualize_multiple_tiles(
            args.wsi,
            Path(args.json),
            tile_coords,
            args.tile_size,
            args.output,
            **kwargs
        )
    
    # Single tile mode
    elif args.tile_x is not None and args.tile_y is not None:
        visualize_tile_with_cells(
            args.wsi,
            Path(args.json),
            args.tile_x,
            args.tile_y,
            args.tile_size,
            args.output,
            **kwargs
        )
    
    else:
        parser.error("Must provide either --tile_x/--tile_y or --tile_coords")


if __name__ == '__main__':
    main()