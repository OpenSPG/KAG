#!/bin/sh

rm -rf ckpt
rm -rf nohup.out

nohup python -u eval.py & 2>&1 
