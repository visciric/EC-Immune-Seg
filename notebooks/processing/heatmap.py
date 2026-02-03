import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import openslide
from pathlib import Path
from constants import HEATMAP_COLORS, MAX_THUMBNAIL_DIM


def create_heatmap(tile_counts, wsi_path, output_path, tile_size=256, wsi_alpha=1.0):
    """
    Create colored heatmap visualization with WSI background
    
    Args:
        tile_counts: Dictionary of immune cell counts per tile
        wsi_path: Path to WSI .svs file
        output_path: Where to save the heatmap image
        tile_size: Tile size in pixels
        wsi_alpha: Alpha/transparency of WSI background (0.0=invisible, 1.0=fully visible)
    """
    try:
        slide = openslide.OpenSlide(wsi_path)
        width, height = slide.dimensions
        
        aspect_ratio = width / height
        
        if aspect_ratio > 1:
            fig_width = 15
            fig_height = 15 / aspect_ratio
        else:
            fig_width = 15 * aspect_ratio
            fig_height = 15
        
        scale_factor = min(MAX_THUMBNAIL_DIM / width, MAX_THUMBNAIL_DIM / height)
        thumb_width = int(width * scale_factor)
        thumb_height = int(height * scale_factor)
        
        print(f"WSI dimensions: {width} x {height}")
        print(f"Aspect ratio: {aspect_ratio:.3f}")
        print(f"Figure size: {fig_width:.1f} x {fig_height:.1f} inches")
        print(f"Creating thumbnail: {thumb_width} x {thumb_height}")
        
        thumbnail = slide.get_thumbnail((thumb_width, thumb_height))
        thumbnail_array = np.array(thumbnail)
        
        slide.close()
    except Exception as e:
        print(f"Error opening WSI file: {e}")
        raise
    
    grid_width = int(np.ceil(width / tile_size))
    grid_height = int(np.ceil(height / tile_size))
    
    print(f"Grid dimensions: {grid_width} x {grid_height} tiles")
    
    heatmap = np.full((grid_height, grid_width), np.nan)
    
    for (tile_x, tile_y), count in tile_counts.items():
        if tile_y < grid_height and tile_x < grid_width:
            tile_x_pixel = tile_x * tile_size
            tile_y_pixel = tile_y * tile_size
            
            if tile_x_pixel < width and tile_y_pixel < height:
                heatmap[tile_y, tile_x] = count
    
    valid_data = heatmap[~np.isnan(heatmap)]
    
    if len(valid_data) > 0:
        max_count = float(np.nanmax(heatmap))
        mean_count = float(np.nanmean(valid_data))
    else:
        max_count = 1.0
        mean_count = 0.0
        print("WARNING: No inflammatory cells found in any tiles!")
    
    print(f"Max inflammatory cells per tile: {max_count}")
    print(f"Mean inflammatory cells per tile (non-zero): {mean_count:.2f}")
    
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list('inflammatory_heatmap', HEATMAP_COLORS, N=n_bins)
    cmap.set_bad(color='none')  
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    ax.imshow(thumbnail_array, extent=[0, grid_width, grid_height, 0], 
              aspect='equal',
              interpolation='bilinear', alpha=wsi_alpha)
    
    im = ax.imshow(heatmap, cmap=cmap, interpolation='nearest', vmin=0, vmax=max_count, 
                   extent=[0, grid_width, grid_height, 0], 
                   aspect='equal')
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Inflammatory Cells Count', rotation=270, labelpad=20)
    
    ax.grid(True, which='both', color='gray', linewidth=0.2, alpha=0.001)
    
    total_immune_cells = int(np.nansum(heatmap)) if len(valid_data) > 0 else 0
    total_pixels = width * height
    
    inflam_percentage = (total_immune_cells / total_pixels) * 100 if total_pixels > 0 else 0
    
    wsi_name = Path(wsi_path).stem
    ax.set_title(f'{wsi_name}: {total_immune_cells} inflammatory cells ({inflam_percentage:.4f}%)', 
                 fontsize=12)
 
    ax.set_xlim(0, grid_width)
    ax.set_ylim(grid_height, 0)
    
    ax.set_xticks([])
    ax.set_yticks([])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"Heatmap saved to: {output_path}")
    
    return heatmap