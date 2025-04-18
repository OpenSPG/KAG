import os
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner

dir_path = os.path.dirname(__file__)


def import_data():
    pwd = os.path.dirname(__file__)

    spo_runner_config = KAG_CONFIG.all_config["spo_runner"]
    spo_runner = BuilderChainRunner.from_config(spo_runner_config)
    spo_runner.invoke(os.path.join(pwd, "data/kg.txt"))


if __name__ == "__main__":
    import_modules_from_path(dir_path)
    import_data()
