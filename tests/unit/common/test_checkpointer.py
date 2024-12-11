# -*- coding: utf-8 -*-
import time
from kag.common.checkpointer import CheckPointer


def test_txt_checkpointer():
    config = {"type": "txt", "ckpt_dir": "ckpt"}
    checkpointer = CheckPointer.from_config(config)
    k = "aaa"
    v = {"name": "aaa", "time": time.time()}
    checkpointer.write_to_ckpt(k, v)
    assert checkpointer.exists(k)
    assert v == checkpointer.read_from_ckpt(k)
    checkpointer.close()
    checkpointer2 = CheckPointer.from_config(config)
    assert checkpointer2.exists(k)
    assert v == checkpointer2.read_from_ckpt(k)
    checkpointer2.close()


def test_bin_checkpointer():
    config = {"type": "bin", "ckpt_dir": "ckpt"}
    checkpointer = CheckPointer.from_config(config)
    k = "aaa"
    v = {"name": "aaa", "time": time.time()}
    checkpointer.write_to_ckpt(k, v)
    assert checkpointer.exists(k)
    assert v == checkpointer.read_from_ckpt(k)
    checkpointer.close()
    checkpointer2 = CheckPointer.from_config(config)
    assert checkpointer2.exists(k)
    assert v == checkpointer2.read_from_ckpt(k)
    checkpointer2.close()
