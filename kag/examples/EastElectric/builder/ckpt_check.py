from kag.common.checkpointer import CheckPointer, CheckpointerManager

checkpointer: CheckPointer = CheckpointerManager.get_checkpointer(
    {
        "type": "diskcache",
        # "ckpt_dir": "ckpt/SchemaFreeExtractor",
        "ckpt_dir": "ckpt/OutlineExtractor",
    }
)

tmp_key = checkpointer.keys()[-1]
print(checkpointer.read_from_ckpt(tmp_key))
