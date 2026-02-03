#!/bin/bash
#SBATCH --job-name=hovernext_mss_tmb-h
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=48
#SBATCH --time=12:00:00
#SBATCH --qos=earth-4.1d
#SBATCH --partition=earth-4
#SBATCH --constraint=rhel8
#SBATCH --gres=gpu:l40s:3
#SBATCH --mem=256GB


echo "Job started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "CPUs allocated: $SLURM_CPUS_PER_TASK"
echo "Memory allocated: $SLURM_MEM_PER_NODE MB"
echo ""

BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
CSV_FILE="${BASE_DIR}/data/raw/mss_tmb-l_image_list.csv"
PROCESSED_DIR="${BASE_DIR}/results/hovernext/mss_tmb-h"
IMAGES_PER_BATCH=100
MIN_FILE_SIZE=100
SKIP_FIRST=304

BATCH_ID="batch_$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${BASE_DIR}/results/hovernext_output_mss_tmb-l${BATCH_ID}"
IMAGE_LIST_FILE="${BASE_DIR}/data/hovernext_image_list_${BATCH_ID}.txt"

echo "CONFIGURATION"
echo "Batch ID: $BATCH_ID"
echo "CSV file: $CSV_FILE"
echo "Checking processed images in: $PROCESSED_DIR"
echo "Images per batch: $IMAGES_PER_BATCH"
echo "Skip first: $SKIP_FIRST images"
echo ""

mkdir -p "$OUTPUT_DIR"
rm -f "$IMAGE_LIST_FILE"

echo "Scanning for all existing output directories..."
ALL_OUTPUT_DIRS=()
ALL_OUTPUT_DIRS+=("$PROCESSED_DIR")
while IFS= read -r dir; do
    ALL_OUTPUT_DIRS+=("$dir")
done < <(find "${BASE_DIR}/results" -maxdepth 1 -type d -name "hovernext_output*" 2>/dev/null)

echo "Found ${#ALL_OUTPUT_DIRS[@]} directories to check for processed images"
echo ""

echo "SCANNING FOR UNPROCESSED IMAGES"

processed_count=0
unprocessed_count=0
error_count=0
skipped_count=0

while IFS=, read -r case_id image_path image_name parent_folder category; do
    if [ $unprocessed_count -ge $IMAGES_PER_BATCH ]; then
        break
    fi
    
    image_path=$(echo "$image_path" | tr -d '"' | xargs)
    image_name=$(echo "$image_name" | tr -d '"' | xargs)
    
    if [ -z "$image_name" ]; then
        continue
    fi
    
    base_name="${image_name%.*}"
    
    already_processed=false
    for output_dir in "${ALL_OUTPUT_DIRS[@]}"; do
        json_file="${output_dir}/${base_name}/class_inst.json"
        
        if [ -e "$json_file" ]; then
            file_size=$(stat -f%z "$json_file" 2>/dev/null || stat -c%s "$json_file" 2>/dev/null || echo "0")
            
            if [ "$file_size" -gt "$MIN_FILE_SIZE" ]; then
                already_processed=true
                ((processed_count++))
                break
            fi
        fi
    done
    
    if [ "$already_processed" = true ]; then
        continue
    fi
    
    if [ $skipped_count -lt $SKIP_FIRST ]; then
        ((skipped_count++))
        continue
    fi
    
    if [ ! -f "$image_path" ]; then
        echo "WARNING: Image not found: $image_path"
        ((error_count++))
        continue
    fi
    
    echo "$image_path" >> "$IMAGE_LIST_FILE"
    ((unprocessed_count++))
    
    if [ $unprocessed_count -le 10 ] || [ $((unprocessed_count % 10)) -eq 0 ]; then
        echo "  [$unprocessed_count] Queued: $image_name"
    fi
    
done < <(tail -n +2 "$CSV_FILE")

echo ""
echo "SCAN SUMMARY"
echo "Already processed: $processed_count"
echo "Skipped (parameter): $skipped_count"
echo "Newly queued: $unprocessed_count"
echo "Errors (missing files): $error_count"
echo ""

if [ $unprocessed_count -eq 0 ]; then
    echo "No unprocessed images found. All images are already processed."
    echo "Job finished at: $(date)"
    exit 0
fi

echo "BATCH READY FOR PROCESSING"
echo "Batch ID: $BATCH_ID"
echo "Images to process: $unprocessed_count"
echo "Image list file: $IMAGE_LIST_FILE"
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "First 5 images to process:"
head -n 5 "$IMAGE_LIST_FILE"
if [ $unprocessed_count -gt 5 ]; then
    echo "... and $((unprocessed_count - 5)) more"
fi
echo ""

cd "${BASE_DIR}/hover_next_inference" || {
    echo "ERROR: Could not find HoverNeXT directory"
    exit 1
}

echo "STARTING HOVERNEXT INFERENCE"
echo "Working directory: $(pwd)"
echo "Number of images: $unprocessed_count"
echo ""

python3 main.py \
    --input "$IMAGE_LIST_FILE" \
    --output_root "$OUTPUT_DIR" \
    --cp "pannuke_convnextv2_tiny_1" \
    --tta 4 \
    --inf_workers 16 \
    --pp_tiling 15 \
    --pp_workers 16

INFERENCE_EXIT_CODE=$?

echo ""
echo "JOB COMPLETE"
echo "Batch ID: $BATCH_ID"
echo "Exit code: $INFERENCE_EXIT_CODE"
echo ""

if [ $INFERENCE_EXIT_CODE -eq 0 ]; then
    valid_count=0
    for dir in "$OUTPUT_DIR"/*/; do
        if [ -d "$dir" ]; then
            json_file="${dir}class_inst.json"
            if [ -e "$json_file" ]; then
                file_size=$(stat -f%z "$json_file" 2>/dev/null || stat -c%s "$json_file" 2>/dev/null || echo "0")
                if [ "$file_size" -gt "$MIN_FILE_SIZE" ]; then
                    ((valid_count++))
                fi
            fi
        fi
    done
    
    echo "Processing completed successfully"
    echo "Generated $valid_count valid output folders"
    
    if [ $valid_count -ne $unprocessed_count ]; then
        echo "Warning: Expected $unprocessed_count outputs but got $valid_count"
    fi
else
    echo "Processing failed with exit code: $INFERENCE_EXIT_CODE"
fi

echo ""
echo "Output directory: $OUTPUT_DIR"
echo "Job finished at: $(date)"
echo ""
echo " Resource Usage Summary "
sacct -j $SLURM_JOB_ID --format=JobID,JobName,ReqMem,MaxRSS,Elapsed,State --units=G