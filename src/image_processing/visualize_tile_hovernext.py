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
    
    cells_by_type = {i: [] for i in range(6)}
    
    for tsv_file, cell_type in tsv_to_type.items():
        tsv_path = results_dir / tsv_file
        
        if not tsv_path.exists():
            continue
        
        df = pd.read_csv(tsv_path, sep='\t')
        
        mask = ((df['x'] >= tile_x_start) & (df['x'] < tile_x_end) &
                (df['y'] >= tile_y_start) & (df['y'] < tile_y_end))
        
        cells_in_tile = df[mask]
        
        for _, row in cells_in_tile.iterrows():
            x_rel = row['x'] - tile_x_start
            y_rel = row['y'] - tile_y_start
            cells_by_type[cell_type].append((x_rel, y_rel))
    
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
    
    if not zip_path.exists():
        return None
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zarray_str = zf.read('.zarray').decode('utf-8')
            zarray_meta = json.loads(zarray_str)
            
            chunks = zarray_meta['chunks']
            chunk_height, chunk_width = chunks
            
            tile_x_start = tile_x * tile_size
            tile_y_start = tile_y * tile_size
            
            chunk_row_start = tile_y_start // chunk_height
            chunk_col_start = tile_x_start // chunk_width
            chunk_row_end = (tile_y_start + tile_size - 1) // chunk_height
            chunk_col_end = (tile_x_start + tile_size - 1) // chunk_width
            
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

    cells_by_type = load_cells_in_tile(results_dir, tile_x, tile_y, tile_size)
    total_cells = sum(len(cells) for cells in cells_by_type.values())

    mask = None
    cell_type_map = {}
    if show_boundaries:
        mask = load_tile_mask_from_zarr(results_dir, tile_x, tile_y, tile_size)
        if mask is not None:
            for cell_type, cells in cells_by_type.items():
                for x, y in cells:
                    xi, yi = int(y), int(x)
                    if 0 <= xi < mask.shape[0] and 0 <= yi < mask.shape[1]:
                        cell_id = mask[xi, yi]
                        if cell_id > 0:
                            cell_type_map[cell_id] = cell_type

    fig, ax = plt.subplots(figsize=(14, 14), dpi=150)
    ax.imshow(tile_array, alpha=wsi_alpha)

    if show_boundaries and mask is not None:
        cell_ids = np.unique(mask)
        cell_ids = cell_ids[cell_ids > 0]

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
                    alpha=boundary_alpha,
                )
                
                if fill_alpha > 0:
                    ax.fill(
                        contour[:, 1],
                        contour[:, 0],
                        color=cell_color,
                        alpha=fill_alpha
                    )

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

    print(f"Saved: {output_path}")


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
    parser.add_argument('--boundary_alpha', type=float, default=0.8, help='Boundary transparency (0.0-1.0, default: 0.8)')
    parser.add_argument('--fill_alpha', type=float, default=0.0, help='Fill transparency (0.0-1.0, default: 0.0)')
    parser.add_argument('--wsi_alpha', type=float, default=1.0, help='WSI background transparency (0.0-1.0, default: 1.0)')
    
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
        boundary_width=args.boundary_width,
        boundary_alpha=args.boundary_alpha,
        fill_alpha=args.fill_alpha,
        wsi_alpha=args.wsi_alpha
    )


if __name__ == '__main__':
    main()