#!/bin/bash

# Configuration
BASE_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad"
RESULTS_DIR="${BASE_DIR}/results"
CSV_FILE="${1:-${BASE_DIR}/data/msi-h_image_list.csv}"


# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "  Image Processing Status Checker"
echo "========================================"
echo "CSV file: $(basename $CSV_FILE)"
echo "Check mode: JSON files only"
echo ""

# Verify CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}Error: CSV file not found: $CSV_FILE${NC}"
    echo ""
    echo "Usage: $0 [csv_file]"
    echo "  csv_file: path to CSV file (default: msi-h_image_list.csv)"
    exit 1
fi

# Extract image names from CSV (skip header, get image_name column, remove .svs)
echo "Extracting image names from CSV..."
tail -n +2 "$CSV_FILE" | cut -d',' -f3 | sed 's/\.svs$//' | sort -u > /tmp/csv_images.txt

total_images=$(wc -l < /tmp/csv_images.txt)
echo "Total unique images in CSV: $total_images"
echo ""

# Function to find json file
find_json_file() {
    local base_name=$1
    for dir in "$RESULTS_DIR/"*/json/; do
        if [ -f "${dir}${base_name}.json" ]; then
            echo "${dir}${base_name}.json"
            return
        fi
    done
    echo ""
}

# Function to check if image has JSON file
check_image_status() {
    local base_name=$1
    local json_file=$(find_json_file "$base_name")
    
    if [ -z "$json_file" ]; then
        echo "missing"
    else
        echo "complete"
    fi
}

# Analyze all images
echo "Analyzing processing status..."

complete_count=0
missing_count=0

declare -a complete_images
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
    esac
done < /tmp/csv_images.txt

printf "\rProgress: %d/%d (100.0%%)  \n\n" $total_images $total_images

# Display results
echo "========================================"
echo "  RESULTS"
echo "========================================"
completion_pct=$(awk "BEGIN {printf \"%.1f\", ($complete_count/$total_images)*100}")
echo -e "${GREEN} Complete:${NC}   $complete_count / $total_images (${completion_pct}%)"
echo -e "${RED} Missing:${NC}    $missing_count"
echo ""

# Show missing images
if [ $missing_count -gt 0 ]; then
    echo "========================================"
    echo "  MISSING IMAGES (No JSON file found)"
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
missing_file="${output_prefix}_missing.txt"
reprocess_file="${output_prefix}_reprocess.txt"

printf "%s\n" "${complete_images[@]}" > "$complete_file"
printf "%s\n" "${missing_images[@]}" > "$missing_file"
cp "$missing_file" "$reprocess_file"

echo "========================================"
echo "  OUTPUT FILES"
echo "========================================"
echo "Complete images:   $complete_file"
echo "Missing images:    $missing_file"
echo "Reprocess list:    $reprocess_file"
echo ""

# Final summary
echo "========================================"
echo "  SUMMARY"
echo "========================================"
if [ $missing_count -eq 0 ]; then
    echo -e "${GREEN} All images have JSON files!${NC}"
else
    echo -e "${YELLOW}⚠ $missing_count images need processing${NC}"
    echo ""
    echo "To create a CSV for reprocessing:"
    echo "  head -1 $CSV_FILE > reprocess.csv"
    echo "  grep -f $reprocess_file $CSV_FILE >> reprocess.csv"
fi
echo "========================================"

# Cleanup
rm -f /tmp/csv_images.txt