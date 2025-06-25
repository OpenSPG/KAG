#!/bin/sh

rm -rf ckpt
rm -rf nohup_0
rm -rf nohup_1
rm -rf nohup_2

export PYTHONPATH=/home/zhenzhi/code/KAG/:$PYTHONPATH

nohup python -u /home/zhenzhi/code/KAG/kag/examples/finqa/solver/eval.py 0 3 > nohup_0 2>&1 &
nohup python -u /home/zhenzhi/code/KAG/kag/examples/finqa/solver/eval.py 1 3 > nohup_1 2>&1 &
nohup python -u /home/zhenzhi/code/KAG/kag/examples/finqa/solver/eval.py 2 3 > nohup_2 2>&1 &
