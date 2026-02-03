import numpy as np
import openslide
from collections import defaultdict

def calculate_tile_size_from_target(wsi_path, target_tiles=200):
    """
    Calculate tile size to achieve approximately target number of tiles
    
    Args:
        wsi_path: Path to WSI file
        target_tiles: Desired approximate number of tiles
    
    Returns:
        tile_size: Calculated tile size in pixels
    """
    slide = openslide.OpenSlide(wsi_path)
    width, height = slide.dimensions
    slide.close()
    
    total_area = width * height
    area_per_tile = total_area / target_tiles
    tile_size = int(np.sqrt(area_per_tile))
    actual_tiles = (np.ceil(width / tile_size) * np.ceil(height / tile_size))
    
    print(f"WSI dimensions: {width} x {height}")
    print(f"Target tiles: {target_tiles}")
    print(f"Calculated tile size: {tile_size} x {tile_size} pixels")
    print(f"Actual tiles: {int(actual_tiles)}")
    
    return tile_size

def count_immune_cells_per_tile(nuclei_data, tile_size=256, magnification=40):
    """
    Count immune cells (type 2 = inflammatory) in each tile
    
    Args:
        nuclei_data: Dictionary of nuclei from JSON
        tile_size: Size of each tile in pixels
        magnification: Magnification level from JSON
    
    Returns:
        Dictionary mapping (tile_x, tile_y) to immune cell count
    """
    tile_counts = defaultdict(int)
    total_nuclei = 0
    immune_nuclei = 0
    
    for nuc_id, nuc_info in nuclei_data.items():
        total_nuclei += 1
        centroid = nuc_info['centroid']
        nuc_type = nuc_info['type']
        
        if nuc_type == 2:
            immune_nuclei += 1
            
            # Calculate which tile this nucleus belongs to
            tile_x = int(centroid[0] // tile_size)
            tile_y = int(centroid[1] // tile_size)
            
            tile_counts[(tile_x, tile_y)] += 1
    
    print(f"Total nuclei: {total_nuclei}")
    print(f"Inflammatory cells (type 2): {immune_nuclei}")
    print(f"Tiles with inflammatory cells: {len(tile_counts)}")
    
    return tile_counts