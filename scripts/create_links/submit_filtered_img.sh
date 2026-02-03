#!/bin/bash
#SBATCH --job-name=hovernet_msi-h
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=22:00:00
#SBATCH --qos=earth-5.1d
#SBATCH --partition=earth-5
#SBATCH --constraint=rhel8
#SBATCH --gres=gpu:a100:2
#SBATCH --mem=256GB

echo "Job started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "CPUs allocated: $SLURM_CPUS_PER_TASK"
echo "Memory allocated: $SLURM_MEM_PER_NODE MB"

SYMLINK_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/msi-h_symlinks"
CSV_FILE="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/msi-h_image_list.csv"
MAX_NEW_IMAGES=20

echo "Creating symlinks for next $MAX_NEW_IMAGES images that don't exist yet..."
mkdir -p $SYMLINK_DIR

new_count=0

tail -n +2 $CSV_FILE | while IFS=, read -r case_id image_path image_name parent_folder category; do
    if [ $new_count -ge $MAX_NEW_IMAGES ]; then
        break
    fi
    
    image_path=$(echo $image_path | tr -d '"')
    image_name=$(echo $image_name | tr -d '"')
   
    if [ ! -e "$SYMLINK_DIR/$image_name" ]; then
        ln -s "$image_path" "$SYMLINK_DIR/$image_name"
        echo "  Linked: $image_name"
        ((new_count++))
    else
        echo "  Skipped (already exists): $image_name"
    fi
done

echo "New symlinks created: $new_count"
echo "Total symlinks: $(ls -1 $SYMLINK_DIR | wc -l)"

cd /cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net

python run_infer.py \
--gpu='0,1' \
--nr_types=6 \
--type_info_path=type_info.json \
--batch_size=64 \
--model_mode=fast \
--model_path=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net/models/hovernet_fast_pannuke_type_tf2pytorch.tar \
--nr_inference_workers=16 \
--nr_post_proc_workers=16 \
wsi \
--proc_mag=40 \
--input_dir=$SYMLINK_DIR \
--output_dir=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/msi-h_output \
--cache_path=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net/cache/ \
--save_thumb \
--save_mask

echo "Job finished at: $(date)"