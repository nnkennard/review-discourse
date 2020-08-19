export SQUAD_DIR=`pwd`/squad_data 
python run_squad.py \
      --model_type roberta \
      --model_name_or_path roberta-base \
      --do_train \
      --do_eval \
      --version_2_with_negative \
      --train_file /iesl/canvas/nnayak/review_discourse_models/co-squac/datasets/converted/squad2_train.json \
      --predict_file /iesl/canvas/nnayak/review_discourse_models/co-squac/datasets/converted/squad2_dev.json \
      --learning_rate 3e-5 \
      --num_train_epochs 4 \
      --max_seq_length 384 \
      --doc_stride 128 \
      --output_dir ./wwm_cased_finetuned_coqa/ \
      --per_gpu_eval_batch_size=2  \
          --per_gpu_train_batch_size=2   \
              --save_steps 5000
