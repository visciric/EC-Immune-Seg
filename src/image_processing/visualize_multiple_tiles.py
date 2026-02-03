import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import openslide
import pandas as pd
from pathlib import Path
import zipfile
import json
from skimage import measure
from constants import CELL_TYPES, FONT_SIZES


CELL_TYPE_COLORS = {
    0: '#808080',  # nolabel - gray
    1: '#FF00FF',  # neoplastic - magenta
    2: '#00FF00',  # inflammatory - green
    3: '#0000FF',  # connective - blue
    4: '#FF0000',  # necrosis - red
    5: '#FFFF00',  # non_neoplastic - yellow
}


def load_cells_in_tile(results_dir, tile_x, tile_y, tile_size):
    results_dir = Path(results_dir)
    
    print(f"\n=== Loading cells from: {results_dir} ===")
    
    tsv_to_type = {
        'pred_neoplastic.tsv': 1,
        'pred_inflammatory.tsv': 2,
        'pred_connective.tsv': 3,
        'pred_dead.tsv': 4,
        'pred_epithelial.tsv': 5,
    }
    
    tile_x_start = tile_x * tile_size
    tile_y_start = tile_y * tile_size
    tile_x_end = tile_x_start + tile_size
    tile_y_end = tile_y_start + tile_size
    
    print(f"Tile bounds: X=[{tile_x_start}, {tile_x_end}], Y=[{tile_y_start}, {tile_y_end}]")
    
    cells_by_type = {i: [] for i in range(6)}
    
    for tsv_file, cell_type in tsv_to_type.items():
        tsv_path = results_dir / tsv_file
        
        if not tsv_path.exists():
            print(f"   Missing: {tsv_file}")
            continue
        
        df = pd.read_csv(tsv_path, sep='\t')
        print(f"   Found {tsv_file}: {len(df)} total cells")
        
        mask = ((df['x'] >= tile_x_start) & (df['x'] < tile_x_end) &
                (df['y'] >= tile_y_start) & (df['y'] < tile_y_end))
        
        cells_in_tile = df[mask]
        print(f"    → {len(cells_in_tile)} cells in this tile")
        
        for _, row in cells_in_tile.iterrows():
            x_rel = row['x'] - tile_x_start
            y_rel = row['y'] - tile_y_start
            cells_by_type[cell_type].append((x_rel, y_rel))
    
    total_cells = sum(len(cells) for cells in cells_by_type.values())
    print(f"\n Total cells loaded: {total_cells}")
    for cell_type, cells in cells_by_type.items():
        if len(cells) > 0:
            print(f"  {CELL_TYPES[cell_type]}: {len(cells)}")
    
    return cells_by_type


def load_zarr_chunk_from_zip(zip_path, chunk_row, chunk_col):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zarray_str = zf.read('.zarray').decode('utf-8')
            zarray_meta = json.loads(zarray_str)
            
            chunk_name = f"{chunk_row}.{chunk_col}"
            
            if chunk_name not in zf.namelist():
                return None
            
            chunk_bytes = zf.read(chunk_name)
            
            compressor = zarray_meta.get('compressor')
            if compressor and compressor.get('id') == 'blosc':
                import blosc
                chunk_data = blosc.decompress(chunk_bytes)
            else:
                chunk_data = chunk_bytes
            
            dtype = np.dtype(zarray_meta['dtype'])
            shape = tuple(zarray_meta['chunks'])
            chunk_array = np.frombuffer(chunk_data, dtype=dtype).reshape(shape)
            
            return chunk_array
            
    except Exception as e:
        print(f"ERROR: Failed to load chunk ({chunk_row}, {chunk_col}): {e}")
        return None


def load_tile_mask_from_zarr(results_dir, tile_x, tile_y, tile_size):
    results_dir = Path(results_dir)
    zip_path = results_dir / 'pinst_pp.zip'
    
    print(f"\n=== Loading mask from: {zip_path} ===")
    
    if not zip_path.exists():
        print(f"   Mask file not found!")
        return None
    
    print(f"   Mask file found")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zarray_str = zf.read('.zarray').decode('utf-8')
            zarray_meta = json.loads(zarray_str)
            
            chunks = zarray_meta['chunks']
            chunk_height, chunk_width = chunks
            
            print(f"  Chunk size: {chunk_height} x {chunk_width}")
            
            tile_x_start = tile_x * tile_size
            tile_y_start = tile_y * tile_size
            
            chunk_row_start = tile_y_start // chunk_height
            chunk_col_start = tile_x_start // chunk_width
            chunk_row_end = (tile_y_start + tile_size - 1) // chunk_height
            chunk_col_end = (tile_x_start + tile_size - 1) // chunk_width
            
            print(f"  Loading chunks: rows [{chunk_row_start}, {chunk_row_end}], cols [{chunk_col_start}, {chunk_col_end}]")
            
            tile_mask = np.zeros((tile_size, tile_size), dtype=np.dtype(zarray_meta['dtype']))
            
            for chunk_row in range(chunk_row_start, chunk_row_end + 1):
                for chunk_col in range(chunk_col_start, chunk_col_end + 1):
                    chunk = load_zarr_chunk_from_zip(zip_path, chunk_row, chunk_col)
                    
                    if chunk is None:
                        continue
                    
                    chunk_y_global = chunk_row * chunk_height
                    chunk_x_global = chunk_col * chunk_width
                    
                    y_start_global = max(tile_y_start, chunk_y_global)
                    y_end_global = min(tile_y_start + tile_size, chunk_y_global + chunk_height)
                    x_start_global = max(tile_x_start, chunk_x_global)
                    x_end_global = min(tile_x_start + tile_size, chunk_x_global + chunk_width)
                    
                    y_start_chunk = y_start_global - chunk_y_global
                    y_end_chunk = y_end_global - chunk_y_global
                    x_start_chunk = x_start_global - chunk_x_global
                    x_end_chunk = x_end_global - chunk_x_global
                    
                    y_start_tile = y_start_global - tile_y_start
                    y_end_tile = y_end_global - tile_y_start
                    x_start_tile = x_start_global - tile_x_start
                    x_end_tile = x_end_global - tile_x_start
                    
                    tile_mask[y_start_tile:y_end_tile, x_start_tile:x_end_tile] = \
                        chunk[y_start_chunk:y_end_chunk, x_start_chunk:x_end_chunk]
            
            unique_cells = np.unique(tile_mask)
            unique_cells = unique_cells[unique_cells > 0]
            print(f"   Loaded mask with {len(unique_cells)} unique cell IDs")
            
            return tile_mask
            
    except Exception as e:
        print(f"ERROR: Failed to load mask: {e}")
        return None


def visualize_tile_with_cells(
    wsi_path,
    results_dir,
    tile_x,
    tile_y,
    tile_size,
    output_path,
    show_centroids=True,
    show_boundaries=True,
    centroid_size=3,
    boundary_width=1.5
):
    print(f"\n{'='*60}")
    print(f"Visualizing Tile ({tile_x}, {tile_y})")
    print(f"{'='*60}")
    print(f"WSI: {wsi_path}")
    print(f"Results dir: {results_dir}")
    print(f"Show centroids: {show_centroids}")
    print(f"Show boundaries: {show_boundaries}")
    
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

    cells_by_type = load_cells_in_tile(results_dir, tile_x, tile_y, tile_size)
    total_cells = sum(len(cells) for cells in cells_by_type.values())

    mask = None
    cell_type_map = {}
    if show_boundaries:
        mask = load_tile_mask_from_zarr(results_dir, tile_x, tile_y, tile_size)
        if mask is not None:
            print(f"\n=== Mapping cell types to mask IDs ===")
            for cell_type, cells in cells_by_type.items():
                for x, y in cells:
                    xi, yi = int(y), int(x)
                    if 0 <= xi < mask.shape[0] and 0 <= yi < mask.shape[1]:
                        cell_id = mask[xi, yi]
                        if cell_id > 0:
                            cell_type_map[cell_id] = cell_type
            print(f"  Mapped {len(cell_type_map)} cell IDs to types")

    fig, ax = plt.subplots(figsize=(14, 14), dpi=150)
    ax.imshow(tile_array)

    if show_boundaries and mask is not None:
        cell_ids = np.unique(mask)
        cell_ids = cell_ids[cell_ids > 0]
        
        print(f"\n=== Drawing boundaries ===")
        print(f"  Drawing {len(cell_ids)} cells")

        for cell_id in cell_ids:
            cell_mask = (mask == cell_id)
            contours = measure.find_contours(cell_mask, 0.5)

            for contour in contours:
                cell_type = cell_type_map.get(cell_id, 0)
                cell_color = CELL_TYPE_COLORS.get(cell_type, "#FFFFFF")

                ax.plot(
                    contour[:, 1],
                    contour[:, 0],
                    linewidth=boundary_width,
                    color=cell_color,
                    alpha=0.9,
                )

    if show_centroids:
        print(f"\n=== Drawing centroids ===")
        for cell_type, cells in cells_by_type.items():
            if len(cells) == 0:
                continue

            print(f"  Drawing {len(cells)} {CELL_TYPES[cell_type]} centroids")
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

    from matplotlib.patches import Patch

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
        "with boundaries" if (show_boundaries and mask is not None) else "centroids only"
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

    print(f"\n Saved: {output_path}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Visualize cells in a specific tile')
    parser.add_argument('--input', required=True, help='HoVerNext results directory')
    parser.add_argument('--wsi', required=True, help='WSI file')
    parser.add_argument('--tile_x', type=int, required=True, help='Tile X coordinate')
    parser.add_argument('--tile_y', type=int, required=True, help='Tile Y coordinate')
    parser.add_argument('--tile_size', type=int, default=896, help='Tile size (default: 896)')
    parser.add_argument('--output', required=True, help='Output image path')
    parser.add_argument('--centroid_size', type=int, default=3, help='Centroid size (default: 3)')
    parser.add_argument('--no_centroids', action='store_true', help='Hide centroids')
    parser.add_argument('--no_boundaries', action='store_true', help='Hide boundaries')
    parser.add_argument('--boundary_width', type=float, default=1.5, help='Boundary width (default: 1.5)')
    
    args = parser.parse_args()

    visualize_tile_with_cells(
        args.wsi,
        args.input,
        args.tile_x,
        args.tile_y,
        args.tile_size,
        args.output,
        show_centroids=not args.no_centroids,
        show_boundaries=not args.no_boundaries,
        centroid_size=args.centroid_size,
        boundary_width=args.boundary_width
    )


if __name__ == '__main__':
    main()