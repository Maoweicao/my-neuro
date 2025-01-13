#!/bin/bash
cd /$(pwd | cut -d'/' -f2)/my-neuro/finetune/chuli
python 优化格式.py
python 成品输出.py