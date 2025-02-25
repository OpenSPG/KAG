#!/bin/sh

rm -rf ckpt
rm -rf nohup.out

export PYTHONPATH=/home/zhenzhi/code/KAG/:$PYTHONPATH

nohup python -u eval.py & 2>&1 
