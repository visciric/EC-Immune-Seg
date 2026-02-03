#!/bin/bash
#SBATCH --job-name=zip_folder
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --time=00:15:00
#SBATCH --partition=earth-3
#SBATCH --constraint=rhel8
#SBATCH --mem=32GB

FOLDER="combined_msi-h_part2.csv"
FOLDER_BASE="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/processed_csv"

cd "$FOLDER_BASE" || exit 1

zip -r "${FOLDER}.zip" "$FOLDER/"

echo "Zip file created: ${FOLDER_BASE}/${FOLDER}.zip"