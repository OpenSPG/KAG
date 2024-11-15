import os
from kag.common.conf import KAG_PROJECT_CONF
from knext.reasoner.client import ReasonerClient


def read_dsl_files(directory):
    """
    Read all dsl files in the reasoner directory.
    """

    dsl_contents = []

    for filename in os.listdir(directory):
        if filename.endswith(".dsl"):
            file_path = os.path.join(directory, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                dsl_contents.append(content)

    return dsl_contents


if __name__ == "__main__":
    reasoner_path = os.path.dirname(os.path.abspath(__file__))
    host_addr = KAG_PROJECT_CONF.host_addr
    project_id = KAG_PROJECT_CONF.project_id
    namespace = KAG_PROJECT_CONF.namespace
    client = ReasonerClient(
        host_addr=host_addr, project_id=project_id, namespace=namespace
    )
    dsls = read_dsl_files(reasoner_path)
    for dsl in dsls:
        client.execute(dsl)
