# -*- coding: utf-8 -*-
from kag.builder.runner import CKPT, BuilderRunner


def test_ckpt():
    ckpt = CKPT("./")
    ckpt.open()
    ckpt.add("aaaa")
    ckpt.add("bbbb")
    ckpt.add("cccc")
    ckpt.close()

    ckpt = CKPT("./")
    assert ckpt.is_processed("aaaa")
    assert ckpt.is_processed("bbbb")
    assert ckpt.is_processed("cccc")
