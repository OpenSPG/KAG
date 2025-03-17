import json

from kag.common.registry import Registrable

class LFNodeData:
    def __init__(self):
        pass

    def to_str(self):
        raise NotImplementedError()

class LogicNode(Registrable):
    def __init__(self, operator, args, **kwargs):
        super().__init__(**kwargs)
        self.operator = operator
        self.args = args
        self.sub_query = args.get("sub_query", "")
        self.lf_node_res: LFNodeData = LFNodeData()

    def __repr__(self):
        params = [f"{k}={v}" for k, v in self.args.items()]
        params_str = ",".join(params)
        return f"{self.operator}({params_str})"

    def get_fl_node_result(self):
        return self.lf_node_res

    def to_dict(self):
        return json.loads(self.to_json())

    def to_json(self):
        return json.dumps(
            obj=self, default=lambda x: x.__dict__, sort_keys=False, indent=2
        )

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.sub_query = args.get("sub_query", "")




