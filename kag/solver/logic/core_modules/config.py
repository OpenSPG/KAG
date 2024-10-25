import os


class LogicFormConfiguration:

    def __init__(self, args={}):
        self.resource_path = args.get("resource_path", "./")

        self.prefix = args.get("prefix", "")

        # kg graph project ID.
        self.project_id = args.get("KAG_PROJECT_ID", None) or os.getenv("KAG_PROJECT_ID")
        if not self.project_id:
            raise RuntimeError("init LogicFormConfiguration failed, not found params KAG_PROJECT_ID")

        # kg graph schema file path.
        self.schema_file_name = args.get("schema_file_name", "")

        self.host_addr = args.get("KAG_PROJECT_HOST_ADDR", None) or os.getenv("KAG_PROJECT_HOST_ADDR")

        if not self.host_addr:
            raise RuntimeError("init LogicFormConfiguration failed, not found params KAG_PROJECT_HOST_ADDR")

