import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator
import openslide
from pathlib import Path
from constants import (HEATMAP_COLORMAPS, DEFAULT_COLORMAP, 
                       MAX_THUMBNAIL_DIM, FONT_SIZES, OUTPUT_DPI)


def get_colormap(colormap_name):
    if colormap_name in HEATMAP_COLORMAPS:
        colors = HEATMAP_COLORMAPS[colormap_name]
        cmap = LinearSegmentedColormap.from_list(f'custom_{colormap_name}', colors, N=256)
        cmap.set_bad(color='none')
        return cmap
    return None


def create_heatmap(tile_counts, wsi_path, output_path, tile_size=256, wsi_alpha=1.0, 
                   colormap='green_yellow_red', show_grid=False):

    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    
    try:
        slide = openslide.OpenSlide(wsi_path)
        width, height = slide.dimensions
        
        aspect_ratio = width / height
        
        if aspect_ratio > 1:
            fig_width = 6  # 15
            fig_height = 6 / aspect_ratio  # 15
        else:
            fig_width = 6 * aspect_ratio  # 15
            fig_height = 6  # 15
        
        scale_factor = min(MAX_THUMBNAIL_DIM / width, MAX_THUMBNAIL_DIM / height)
        thumb_width = int(width * scale_factor)
        thumb_height = int(height * scale_factor)
        
        thumbnail = slide.get_thumbnail((thumb_width, thumb_height))
        thumbnail_array = np.array(thumbnail)
        slide.close()
        
    except Exception as e:
        print(f"ERROR: Failed to open WSI: {e}")
        raise
    
    grid_width = int(np.ceil(width / tile_size))
    grid_height = int(np.ceil(height / tile_size))
    
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
     
    cmap = get_colormap(colormap)
    if cmap is None: 
        cmap = get_colormap(DEFAULT_COLORMAP)
        
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=OUTPUT_DPI)
     
    ax.imshow(thumbnail_array, extent=[0, grid_width, grid_height, 0], 
              aspect='equal', interpolation='bilinear', alpha=wsi_alpha)
     
    im = ax.imshow(heatmap, cmap=cmap, interpolation='nearest', vmin=0, vmax=max_count, 
                   extent=[0, grid_width, grid_height, 0], aspect='equal')
     
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Inflammatory Cells Count', 
                   rotation=270, 
                   labelpad=25, 
                   fontsize=FONT_SIZES['colorbar_label'],
                   weight='bold')
     
    cbar.ax.tick_params(labelsize=FONT_SIZES['colorbar_ticks'], width=1.5, length=6)
     
    if max_count > 0:
        tick_locator = MaxNLocator(nbins=8, integer=True)
        cbar.locator = tick_locator
        cbar.update_ticks()
     
    cbar.ax.yaxis.set_minor_locator(MaxNLocator(nbins=20))
    cbar.ax.grid(True, which='major', axis='y', linestyle='-', linewidth=0.8, alpha=0.3)
    cbar.ax.grid(True, which='minor', axis='y', linestyle=':', linewidth=0.5, alpha=0.2)
    
    total_immune_cells = int(np.nansum(heatmap)) if len(valid_data) > 0 else 0
    total_pixels = width * height
    inflam_percentage = (total_immune_cells / total_pixels) * 100 if total_pixels > 0 else 0
     
    wsi_name = Path(wsi_path).stem
    title_text = f'{wsi_name}\n{total_immune_cells:,} inflammatory cells ({inflam_percentage:.4f}%)'
    ax.set_title(title_text, 
                 fontsize=FONT_SIZES['title'], 
                 weight='bold',
                 pad=20)
 
    ax.set_xlim(0, grid_width)
    ax.set_ylim(grid_height, 0)
    
    # Remove axis ticks
    ax.set_xticks([])
    ax.set_yticks([])
     
    # Keep borders visible
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    
    plt.tight_layout()
     
    plt.savefig(output_path, dpi=OUTPUT_DPI, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"Saved: {output_path}")
    
    return heatmap