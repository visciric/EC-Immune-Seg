import json
import openslide

def load_json_results(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def get_wsi_dimensions(wsi_path):
    slide = openslide.OpenSlide(wsi_path)
    dimensions = slide.dimensions
    slide.close()
    return dimensions