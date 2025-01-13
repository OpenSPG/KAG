# -*- coding: utf-8 -*-
import time
from kag.common.checkpointer import CheckpointerManager


def test_txt_checkpointer():
    config = {"type": "txt", "ckpt_dir": "ckpt/txt"}
    checkpointer = CheckpointerManager.get_checkpointer(config)
    k = "aaa"
    v = {"name": "aaa", "time": time.time()}
    checkpointer.write_to_ckpt(k, v)
    assert checkpointer.exists(k)
    assert v == checkpointer.read_from_ckpt(k)
    checkpointer2 = CheckpointerManager.get_checkpointer(config)
    assert checkpointer is checkpointer2

    CheckpointerManager.close()
    checkpointer3 = CheckpointerManager.get_checkpointer(config)
    assert checkpointer3.exists(k)
    assert v == checkpointer3.read_from_ckpt(k)
    CheckpointerManager.close()


def test_bin_checkpointer():
    config = {"type": "zodb", "ckpt_dir": "ckpt/bin"}
    checkpointer = CheckpointerManager.get_checkpointer(config)
    k = "aaa"
    v = {"name": "aaa", "time": time.time()}
    checkpointer.write_to_ckpt(k, v)
    assert checkpointer.exists(k)
    assert v == checkpointer.read_from_ckpt(k)
    checkpointer2 = CheckpointerManager.get_checkpointer(config)
    assert checkpointer is checkpointer2
    CheckpointerManager.close()
    checkpointer3 = CheckpointerManager.get_checkpointer(config)
    assert checkpointer3.exists(k)
    assert v == checkpointer3.read_from_ckpt(k)
    CheckpointerManager.close()
