import os
import unittest
from kag.common.llm.client import LLMClient
from kag.builder.prompt.outline_prompt import OutlinePrompt
import argparse
import base64

dir = os.path.dirname(os.path.abspath(__file__))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default=os.path.join(dir,"config/ollama.yaml"))
    args = parser.parse_args()
    return args

args = parse_args()

class TestLLMClient(unittest.TestCase):
    def setUp(self):
        self.test_path = os.path.dirname(os.path.abspath(__file__))
        
    def test_llm(self):
        llm_config_path = args.config_path
        llm_client = LLMClient.from_config(llm_config_path)
        res = llm_client("你是谁？")
        print(res)
        assert res is not None

    def test_invoke(self):
        llm_config_path = args.config_path
        llm_client = LLMClient.from_config(llm_config_path)
        prompt = OutlinePrompt(language="zh")
        var_name = prompt.template_variables
        input = {}
        for i in var_name:
            input[i] = "你是谁？"
        res = llm_client.invoke(variables=input, prompt_op=prompt)
        print(res)
        assert res is not None
def main():
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLLMClient)
    runner.run(suite)

if __name__ == "__main__":
    main()