import numpy as np
import openslide
from collections import defaultdict

def calculate_tile_size_from_target(wsi_path, target_tiles=200):
    slide = openslide.OpenSlide(wsi_path)
    width, height = slide.dimensions
    slide.close()
    
    total_area = width * height
    area_per_tile = total_area / target_tiles
    tile_size = int(np.sqrt(area_per_tile))
    actual_tiles = (np.ceil(width / tile_size) * np.ceil(height / tile_size))

    return tile_size

def count_immune_cells_per_tile(nuclei_data, tile_size=256, magnification=40):
 
    tile_counts = defaultdict(int)
    total_nuclei = 0
    immune_nuclei = 0
    
    for nuc_id, nuc_info in nuclei_data.items():
        total_nuclei += 1
        centroid = nuc_info['centroid']
        nuc_type = nuc_info['type']
        
        if nuc_type == 2:
            immune_nuclei += 1 
            tile_x = int(centroid[0] // tile_size)
            tile_y = int(centroid[1] // tile_size)
            
            tile_counts[(tile_x, tile_y)] += 1 
    return tile_counts

