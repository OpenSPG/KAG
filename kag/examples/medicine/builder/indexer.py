import os
import copy
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner


def import_data():
    pwd = os.path.dirname(__file__)
    spo_runner_config = KAG_CONFIG.all_config["spg_runner"]
    for spg_type_name in ["HumanBodyPart", "HospitalDepartment"]:
        runner_config = copy.deepcopy(spo_runner_config)
        runner_config["chain"]["mapping"]["spg_type_name"] = spg_type_name
        file_path = os.path.join(pwd, f"data/{spg_type_name}.csv")
        runner = BuilderChainRunner.from_config(runner_config)
        runner.invoke(file_path)

    extract_runner_config = KAG_CONFIG.all_config["extract_runner"]
    extract_runner = BuilderChainRunner.from_config(extract_runner_config)
    extract_runner.invoke(os.path.join(pwd, "data/Disease.csv"))

    spo_runner_config = KAG_CONFIG.all_config["spo_runner"]
    spo_runner = BuilderChainRunner.from_config(spo_runner_config)
    spo_runner.invoke(os.path.join(pwd, "data/SPO.csv"))


if __name__ == "__main__":
    import_modules_from_path(".")
    import_data()
