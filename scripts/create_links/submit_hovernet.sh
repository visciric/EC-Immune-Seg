#!/bin/bash
#SBATCH --job-name=hovernet
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --time=04:10:00
#SBATCH --partition=earth-4
#SBATCH --constraint=rhel8
#SBATCH --gres=gpu:l40s:2
#SBATCH --mem=256GB
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=visciric@students.zhaw.ch

mkdir -p /cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/slurm

echo "Job started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "CPUs allocated: $SLURM_CPUS_PER_TASK"
echo "Memory allocated: $SLURM_MEM_PER_NODE MB"

cd /cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/scripts

./run_wsi.sh 

