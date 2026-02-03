#!/bin/bash

# Configuration
BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
RESULTS_DIR="${BASE_DIR}/results"
CSV_FILE="${1:-${BASE_DIR}/data/msi-h_image_list.csv}"

# Required files for a fully processed image
REQUIRED_FILES=(
    "class_inst.json"
    "pinst_pp.zip"
    "pred_connective.tsv"
    "pred_dead.tsv"
    "pred_epithelial.tsv"
    "pred_inflammatory.tsv"
    "pred_neoplastic.tsv"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check mode: "full" or "quick"
CHECK_MODE="${2:-full}"

echo "========================================"
echo "  Image Processing Status Checker"
echo "========================================"
echo "CSV file: $(basename $CSV_FILE)"
echo "Check mode: $CHECK_MODE"
echo ""

# Verify CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}Error: CSV file not found: $CSV_FILE${NC}"
    echo ""
    echo "Usage: $0 [csv_file] [check_mode]"
    echo "  csv_file: path to CSV file (default: msi-h_image_list.csv)"
    echo "  check_mode: 'full' or 'quick' (default: full)"
    exit 1
fi

# Extract image names from CSV (skip header, get image_name column, remove .svs)
echo "Extracting image names from CSV..."
tail -n +2 "$CSV_FILE" | cut -d',' -f3 | sed 's/\.svs$//' | sort -u > /tmp/csv_images.txt

total_images=$(wc -l < /tmp/csv_images.txt)
echo "Total unique images in CSV: $total_images"
echo ""

# Function to find image directory
find_image_dir() {
    local base_name=$1
    for dir in "$RESULTS_DIR/"*/; do
        if [ -d "${dir}${base_name}" ]; then
            echo "${dir}${base_name}"
            return
        fi
    done
    echo ""
}

# Function to check if image is fully processed
check_image_status() {
    local base_name=$1
    local img_dir=$(find_image_dir "$base_name")
    
    if [ -z "$img_dir" ]; then
        echo "missing"
        return
    fi
    
    if [ "$CHECK_MODE" = "quick" ]; then
        if [ -f "${img_dir}/class_inst.json" ]; then
            echo "complete"
        else
            echo "partial"
        fi
        return
    fi
    
    # Full check: verify all required files
    local missing_files=()
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "${img_dir}/${file}" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        echo "complete"
    elif [ ${#missing_files[@]} -eq ${#REQUIRED_FILES[@]} ]; then
        echo "partial"
    else
        echo "incomplete:${missing_files[*]}"
    fi
}

# Analyze all images
echo "Analyzing processing status..."

complete_count=0
incomplete_count=0
missing_count=0

declare -a complete_images
declare -a incomplete_images
declare -a missing_images

# Progress indicator
processed=0

while IFS= read -r base_name; do
    ((processed++))
    if [ $((processed % 10)) -eq 0 ]; then
        printf "\rProgress: %d/%d (%.1f%%)" $processed $total_images $(awk "BEGIN {printf \"%.1f\", ($processed/$total_images)*100}")
    fi
    
    status=$(check_image_status "$base_name")
    
    case "$status" in
        complete)
            ((complete_count++))
            complete_images+=("$base_name")
            ;;
        missing)
            ((missing_count++))
            missing_images+=("$base_name")
            ;;
        incomplete:*)
            ((incomplete_count++))
            incomplete_images+=("$base_name:${status#incomplete:}")
            ;;
        partial)
            ((incomplete_count++))
            incomplete_images+=("$base_name:no files")
            ;;
    esac
done < /tmp/csv_images.txt

printf "\rProgress: %d/%d (100.0%%)  \n\n" $total_images $total_images

# Display results
echo "========================================"
echo "  RESULTS"
echo "========================================"
completion_pct=$(awk "BEGIN {printf \"%.1f\", ($complete_count/$total_images)*100}")
echo -e "${GREEN} Complete:${NC}   $complete_count / $total_images (${completion_pct}%)"
echo -e "${YELLOW}⚠ Incomplete:${NC} $incomplete_count"
echo -e "${RED} Missing:${NC}    $missing_count"
echo ""

# Show incomplete images
if [ $incomplete_count -gt 0 ]; then
    echo "========================================"
    echo "  INCOMPLETE IMAGES"
    echo "========================================"
    display_count=0
    for entry in "${incomplete_images[@]}"; do
        if [ $display_count -ge 20 ]; then
            break
        fi
        image="${entry%%:*}"
        missing="${entry#*:}"
        echo -e "${YELLOW}●${NC} $image"
        if [ "$missing" != "no files" ] && [ "$CHECK_MODE" = "full" ]; then
            echo "  Missing files: ${missing// /, }"
        fi
        ((display_count++))
    done
    
    if [ $incomplete_count -gt 20 ]; then
        echo "... and $((incomplete_count - 20)) more"
    fi
    echo ""
fi

# Show missing images
if [ $missing_count -gt 0 ]; then
    echo "========================================"
    echo "  MISSING IMAGES (No directory found)"
    echo "========================================"
    display_count=0
    for image in "${missing_images[@]}"; do
        if [ $display_count -ge 20 ]; then
            break
        fi
        echo -e "${RED}${NC} $image"
        ((display_count++))
    done
    
    if [ $missing_count -gt 20 ]; then
        echo "... and $((missing_count - 20)) more"
    fi
    echo ""
fi

# Save detailed lists
output_prefix="/tmp/$(basename $CSV_FILE .csv)"
complete_file="${output_prefix}_complete.txt"
incomplete_file="${output_prefix}_incomplete.txt"
missing_file="${output_prefix}_missing.txt"
reprocess_file="${output_prefix}_reprocess.txt"

printf "%s\n" "${complete_images[@]}" > "$complete_file"
printf "%s\n" "${incomplete_images[@]}" | cut -d: -f1 > "$incomplete_file"
printf "%s\n" "${missing_images[@]}" > "$missing_file"
cat "$incomplete_file" "$missing_file" > "$reprocess_file"

echo "========================================"
echo "  OUTPUT FILES"
echo "========================================"
echo "Complete images:   $complete_file"
echo "Incomplete images: $incomplete_file"
echo "Missing images:    $missing_file"
echo "Reprocess list:    $reprocess_file"
echo ""

# Final summary
echo "========================================"
echo "  SUMMARY"
echo "========================================"
if [ $missing_count -eq 0 ] && [ $incomplete_count -eq 0 ]; then
    echo -e "${GREEN} All images fully processed!${NC}"
else
    remaining=$((missing_count + incomplete_count))
    echo -e "${YELLOW}⚠ $remaining images need processing${NC}"
    echo ""
    echo "To create a CSV for reprocessing:"
    echo "  head -1 $CSV_FILE > reprocess.csv"
    echo "  grep -f $reprocess_file $CSV_FILE >> reprocess.csv"
fi
echo "========================================"

# Cleanup
rm -f /tmp/csv_images.txt