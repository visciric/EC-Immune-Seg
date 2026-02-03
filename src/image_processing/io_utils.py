import json
import openslide
import pandas as pd
from pathlib import Path
from constants import CELL_TYPES

def load_json_results(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def load_hovernext_results(results_dir, magnification=None):
    results_dir = Path(results_dir)
   
    tsv_to_type = {
        'pred_neoplastic.tsv': 1,      # neoplastic
        'pred_inflammatory.tsv': 2,     # inflammatory
        'pred_connective.tsv': 3,       # connective
        'pred_dead.tsv': 4,             # necrosis
        'pred_epithelial.tsv': 5,       # non_neoplastic (epithelial)
    }
   
    nuclei_data = {}
    nuc_id = 0
   
    for tsv_file, cell_type in tsv_to_type.items():
        tsv_path = results_dir / tsv_file
       
        df = pd.read_csv(tsv_path, sep='\t')
         
        x_col = 'x'
        y_col = 'y'
       
        for idx, row in df.iterrows():
            nuclei_data[str(nuc_id)] = {
                'centroid': [float(row[x_col]), float(row[y_col])],
                'type': cell_type
            }
            nuc_id += 1
         
    return {
        'nuc': nuclei_data,
        'mag': magnification
    }

def get_wsi_info(wsi_path):
    slide = openslide.OpenSlide(wsi_path)
     
    dimensions = slide.dimensions
     
    magnification = None
    detection_method = None
     
    if 'openslide.objective-power' in slide.properties:
        try:
            magnification = int(float(slide.properties['openslide.objective-power']))
            detection_method = "openslide.objective-power"
        except (ValueError, TypeError):
            pass
     
    if magnification is None and 'aperio.AppMag' in slide.properties:
        try:
            magnification = int(float(slide.properties['aperio.AppMag']))
            detection_method = "aperio.AppMag"
        except (ValueError, TypeError):
            pass
     
    if magnification is None:
        try:
            if 'tiff.XResolution' in slide.properties:
                x_res = float(slide.properties['tiff.XResolution'])
                if x_res > 90000:
                    magnification = 40
                    detection_method = "tiff.XResolution (heuristic)"
                elif x_res > 40000:
                    magnification = 20
                    detection_method = "tiff.XResolution (heuristic)"
        except (ValueError, TypeError, KeyError):
            pass
     
    if magnification is None:
        for key, value in slide.properties.items():
            if any(keyword in key.lower() for keyword in ['mag', 'objective', 'power', 'zoom']):
                try:
                    import re
                    numbers = re.findall(r'\d+', str(value))
                    if numbers:
                        potential_mag = int(numbers[0])
                        if 10 <= potential_mag <= 100:
                            magnification = potential_mag
                            detection_method = f"{key}"
                            break
                except (ValueError, TypeError):
                    continue
     
    if magnification is None:
        magnification = 40
        detection_method = "default (not found in metadata)"
    
    slide.close()
   
    return {
        'dimensions': dimensions,
        'magnification': magnification,
        'detection_method': detection_method
    }

def get_wsi_dimensions(wsi_path):
    """Quick function to get just dimensions without full metadata"""
    slide = openslide.OpenSlide(wsi_path)
    dimensions = slide.dimensions
    slide.close()
    return dimensions

def auto_detect_format(input_path):
    input_path = Path(input_path)
   
    if input_path.is_file() and input_path.suffix == '.json':
        print("Detected HoVer-Net JSON format")
        return 'hovernet', load_json_results(input_path)
   
    elif input_path.is_dir():
        tsv_files = list(input_path.glob('pred_*.tsv'))
        if tsv_files:
            print("Detected HoVerNext directory format")
            return 'hovernext', load_hovernext_results(input_path, magnification=None)
   
    raise ValueError(f"Could not detect format for: {input_path}")