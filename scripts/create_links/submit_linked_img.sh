#!/bin/bash
#SBATCH --job-name=hovernet_tmb_h
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=20:00:00
#SBATCH --qos=earth-5.1d
#SBATCH --partition=earth-5
#SBATCH --time=18:00:00
#SBATCH --qos=earth-5.1d
#SBATCH --partition=earth-5
#SBATCH --constraint=rhel8
#SBATCH --gres=gpu:a100:2
#SBATCH --mem=128GB
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=visciric@students.zhaw.ch

echo "Job started at: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "CPUs allocated: $SLURM_CPUS_PER_TASK"
echo "Memory allocated: $SLURM_MEM_PER_NODE MB"

SYMLINK_DIR="/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/data/tmb_h_symlinks"

cd /cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net

python run_infer.py \
--gpu='0,1' \
--nr_types=6 \
--type_info_path=type_info.json \
--batch_size=64 \
--model_mode=fast \
--model_path=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net/models/hovernet_fast_pannuke_type_tf2pytorch.tar \
--nr_inference_workers=32 \
--nr_post_proc_workers=32 \
wsi \
--proc_mag=40 \
--input_dir=$SYMLINK_DIR \
--output_dir=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/results/tmb_h_output \
--cache_path=/cfs/earth/scratch/visciric/tumor-segmentation-ucec-stad/hover_net/cache/ \
--save_thumb \
--save_mask

echo "Job finished at: $(date)"
