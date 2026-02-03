#!/bin/bash
#SBATCH --job-name=hovernet_tmb_h
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=48
#SBATCH --time=19:00:00
#SBATCH --qos=earth-4.1d
#SBATCH --partition=earth-4
#SBATCH --constraint=rhel8
#SBATCH --gres=gpu:l40s:3
#SBATCH --mem=128GB

BATCH_ID="batch4"
BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
SYMLINK_DIR="${BASE_DIR}/data/tmb_h_symlinks_${BATCH_ID}"
OUTPUT_DIR="${BASE_DIR}/results/hovernet/tmb_h_output_${BATCH_ID}"
CACHE_DIR="${BASE_DIR}/hover_net/cache_${BATCH_ID}"
CSV_FILE="${BASE_DIR}/data/raw/tmb_h_image_list.csv"
MAX_NEW_IMAGES=20
SKIP_IMAGES=20

ALL_OUTPUT_JSON_DIRS=("${BASE_DIR}/results/tmb_h/json")

mkdir -p $SYMLINK_DIR $OUTPUT_DIR $CACHE_DIR

echo "Batch: $BATCH_ID | Skip: $SKIP_IMAGES | Process: $MAX_NEW_IMAGES"

new_count=0
skipped_count=0
tail -n +2 $CSV_FILE | while IFS=, read -r case_id image_path image_name parent_folder category; do
    [ $new_count -ge $MAX_NEW_IMAGES ] && break
    
    image_path=$(echo $image_path | tr -d '"')
    image_name=$(echo $image_name | tr -d '"')
    base_name="${image_name%.*}"
    
    already_processed=false
    for json_dir in "${ALL_OUTPUT_JSON_DIRS[@]}"; do
        [ -e "${json_dir}/${base_name}.json" ] && already_processed=true && break
    done
    
    [ "$already_processed" = true ] && continue
    [ $skipped_count -lt $SKIP_IMAGES ] && ((skipped_count++)) && continue
    
    [ ! -e "$SYMLINK_DIR/$image_name" ] && ln -s "$image_path" "$SYMLINK_DIR/$image_name"
    ((new_count++))
done

echo "Processing $new_count images"

cd ${BASE_DIR}/hover_net

python run_infer.py \
--gpu='0,1' \
--nr_types=6 \
--type_info_path=type_info.json \
--batch_size=64 \
--model_mode=fast \
--model_path=${BASE_DIR}/hover_net/models/hovernet_fast_pannuke_type_tf2pytorch.tar \
--nr_inference_workers=16 \
--nr_post_proc_workers=16 \
wsi \
--proc_mag=40 \
--input_dir=$SYMLINK_DIR \
--output_dir=$OUTPUT_DIR \
--cache_path=$CACHE_DIR \
--save_thumb \
--save_mask

echo "Done"