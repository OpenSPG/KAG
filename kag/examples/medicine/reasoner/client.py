import os

from knext.reasoner.client import ReasonerClient
from kag.common.env import init_kag_config

def read_dsl_files(directory):
    """
    Read all dsl files in the reasoner directory.
    """
    
    dsl_contents = [] 

    for filename in os.listdir(directory):
        if filename.endswith('.dsl'): 
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file: 
                content = file.read() 
                dsl_contents.append(content) 

    return dsl_contents

if __name__ == "__main__":
    resonser_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.dirname(resonser_path)
    cfg_path = os.path.join(project_path, "kag_config.cfg")
    init_kag_config(cfg_path)
    host_addr = os.environ["KAG_PROJECT_HOST_ADDR"]
    project_id = os.environ["KAG_PROJECT_ID"]
    namespace = os.environ["KAG_PROJECT_NAMESPACE"]
    client = ReasonerClient(host_addr=host_addr, project_id=project_id,namespace=namespace)
    dsls = read_dsl_files(resonser_path)
    for dsl in dsls:
        client.execute(dsl)
