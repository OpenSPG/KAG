from kag.common.checkpointer import CheckPointer, CheckpointerManager

checkpointer: CheckPointer = CheckpointerManager.get_checkpointer(
    {
        "type": "diskcache",
        # "ckpt_dir": "ckpt/SchemaFreeExtractor",
        "ckpt_dir": "ckpt/OutlineExtractor",
    }
)

if checkpointer.size() > 0:
    tmp_key = checkpointer.keys()[-1]
    print(checkpointer.read_from_ckpt(tmp_key))
else:
    print("checkpoint is empty")
