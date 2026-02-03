import numpy as np
import pandas as pd
from collections import defaultdict
from constants import CELL_TYPES


def create_tile_dataset_csv(nuclei_data, wsi_dimensions, output_csv, tile_size=270):
    """
    Create CSV dataset with ALL tiles including coverage information
    """
    width, height = wsi_dimensions
    grid_width = int(np.ceil(width / tile_size))
    grid_height = int(np.ceil(height / tile_size))
    
    print(f"\nCreating tile dataset CSV...")
    print(f"Grid: {grid_width} x {grid_height} = {grid_width * grid_height} tiles")
    
    tile_data = {}
    for tile_y in range(grid_height):
        for tile_x in range(grid_width):
            tile_data[(tile_x, tile_y)] = defaultdict(int)
    
    for nuc_id, nuc_info in nuclei_data.items():
        centroid = nuc_info['centroid']
        nuc_type = nuc_info['type']
        
        tile_x = int(centroid[0] // tile_size)
        tile_y = int(centroid[1] // tile_size)
        
        if tile_x >= grid_width or tile_y >= grid_height:
            continue
        
        type_name = CELL_TYPES.get(nuc_type, f"unknown_{nuc_type}")
        
        tile_data[(tile_x, tile_y)][type_name] += 1
        tile_data[(tile_x, tile_y)]['total'] += 1
    
    rows = []
    for tile_y in range(grid_height):
        for tile_x in range(grid_width):
            counts = tile_data[(tile_x, tile_y)]
            
            tile_x_start = tile_x * tile_size
            tile_y_start = tile_y * tile_size
            tile_x_end = min((tile_x + 1) * tile_size, width)
            tile_y_end = min((tile_y + 1) * tile_size, height)
            
            tile_width_actual = tile_x_end - tile_x_start
            tile_height_actual = tile_y_end - tile_y_start
            tile_area_actual = tile_width_actual * tile_height_actual
            tile_area_full = tile_size * tile_size
            
            coverage = (tile_area_actual / tile_area_full) * 100
            
            is_partial = (tile_width_actual < tile_size) or (tile_height_actual < tile_size)
            is_edge_right = (tile_x_end == width) and (tile_x_end % tile_size != 0)
            is_edge_bottom = (tile_y_end == height) and (tile_y_end % tile_size != 0)
            
            row = {
                'tile_x': tile_x,
                'tile_y': tile_y,
                'tile_id': f"{tile_x}_{tile_y}",
                
                'x_start': tile_x_start,
                'y_start': tile_y_start,
                'x_end': tile_x_end,
                'y_end': tile_y_end,
                'width': tile_width_actual,
                'height': tile_height_actual,
                'area': tile_area_actual,
                'coverage_pct': coverage,
                'is_partial': is_partial,
                'is_edge_right': is_edge_right,
                'is_edge_bottom': is_edge_bottom,
                
                'nolabel': counts.get('nolabel', 0),
                'neoplastic': counts.get('neoplastic', 0),
                'inflammatory': counts.get('inflammatory', 0),
                'connective': counts.get('connective', 0),
                'necrosis': counts.get('necrosis', 0),
                'non_neoplastic': counts.get('non_neoplastic', 0),
                'total_nuclei': counts.get('total', 0)
            }
            
            total = row['total_nuclei']
            if total > 0:
                row['neoplastic_pct'] = (row['neoplastic'] / total) * 100
                row['inflammatory_pct'] = (row['inflammatory'] / total) * 100
                row['connective_pct'] = (row['connective'] / total) * 100
                row['necrosis_pct'] = (row['necrosis'] / total) * 100
                row['non_neoplastic_pct'] = (row['non_neoplastic'] / total) * 100
            else:
                row['neoplastic_pct'] = 0
                row['inflammatory_pct'] = 0
                row['connective_pct'] = 0
                row['necrosis_pct'] = 0
                row['non_neoplastic_pct'] = 0
            
            # Calculate DENSITY (cells per unit area) - normalized for tile size
            if tile_area_actual > 0:
                normalization_factor = tile_area_full / tile_area_actual
                row['neoplastic_density'] = row['neoplastic'] * normalization_factor
                row['inflammatory_density'] = row['inflammatory'] * normalization_factor
                row['connective_density'] = row['connective'] * normalization_factor
                row['necrosis_density'] = row['necrosis'] * normalization_factor
                row['non_neoplastic_density'] = row['non_neoplastic'] * normalization_factor
                row['total_density'] = row['total_nuclei'] * normalization_factor
            else:
                row['neoplastic_density'] = 0
                row['inflammatory_density'] = 0
                row['connective_density'] = 0
                row['necrosis_density'] = 0
                row['non_neoplastic_density'] = 0
                row['total_density'] = 0
            
            rows.append(row)
    
    df = pd.DataFrame(rows)
    
    df.to_csv(output_csv, index=False)
    
    print(f"Total tiles: {len(df)}")
    print(f"Tiles with nuclei: {(df['total_nuclei'] > 0).sum()}")
    print(f"Empty tiles: {(df['total_nuclei'] == 0).sum()}")
    print(f"Partial tiles: {df['is_partial'].sum()}")
    print(f"CSV saved to: {output_csv}")
    
    return df