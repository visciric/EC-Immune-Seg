import pandas as pd
import os

def find_images_by_category(
    category='MSS/TMB-H', 
    ucec_clinical='/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/ucec_clinical.csv',
    image_base_folder='/cfs/earth/scratch/icls/shared/icls-14042025-cancer-genomics-image-analysis/ucec',
    output_dir='/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/raw'
):
    """
    Create a list of .svs image paths for a specific MSI_TMB category.
    
    Parameters:
    -----------
    category : str
        MSI_TMB category to filter (e.g., 'MSS/TMB-H', 'MSI-H', 'MSS/TMB-L')
    ucec_clinical : str
        Path to clinical data CSV
    image_base_folder : str
        Base folder containing .svs images
    output_dir : str
        Directory to save output CSV
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with matched images and case information
    """
    
    clinical = pd.read_csv(ucec_clinical)
    
    # Filter by category
    filtered_cases = clinical[clinical['MSI_TMB'] == category]
    case_ids = filtered_cases['case_submitter_id'].tolist()
    
    print(f'Category: {category}')
    print(f'Searching for {len(case_ids)} cases')
    
    # Find all .svs files using os.walk
    all_svs_files = []
    for root, dirs, files in os.walk(image_base_folder):
        for file in files:
            if file.endswith('.svs'):
                full_path = os.path.join(root, file)
                all_svs_files.append(full_path)
    
    print(f'Found {len(all_svs_files)} total .svs files')
    
    results = []
    
    # Match images to case IDs
    for case_id in case_ids:
        matching_images = [img for img in all_svs_files if case_id in os.path.basename(img)]
        if matching_images:
            for img in matching_images:
                results.append({
                    'case_submitter_id': case_id,
                    'image_path': img,
                    'image_name': os.path.basename(img),
                    'parent_folder': os.path.basename(os.path.dirname(img)),
                    'category': category
                })
            print(f"{case_id}: {len(matching_images)} image(s)")
        else:
            print(f"{case_id}: No images found")
    
    df = pd.DataFrame(results)
    
    # Generate output filename based on category
    safe_category = category.replace('/', '_').replace(' ', '_').lower()
    output_filename = f'{safe_category}_image_list.csv'
    output_path = os.path.join(output_dir, output_filename)
    
    df.to_csv(output_path, index=False)
    
    print(f"Found {len(df)} images for {df['case_submitter_id'].nunique()}/{len(case_ids)} cases")
    print(f"Saved to: {output_path}")
    
    return df


if __name__ == "__main__":

    CATEGORY = "MSI-H"
      
    df = find_images_by_category(category=CATEGORY)
    
    print("\nFirst few results:")
    print(df.head())
    
    print("\nSummary by case:")
    print(df.groupby('case_submitter_id').size().describe())