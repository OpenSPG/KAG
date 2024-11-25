import os


class LogicFormConfiguration:

    def __init__(self, args={}):
        self.resource_path = args.get("resource_path", "./")

        # kg graph project ID.
        self.project_id = args.get("project_id", "1")

        # kg graph prefix.
        self.prefix = args.get("prefix", "")
        # kg graph schema file path.
        self.schema_file_name = args.get("schema_file_name",
                                         os.path.join(self.resource_path, ""))

        #
        self.el_service = args.get("el_service", "")
        self.el_service_client = args.get("el_service_client", "")
        # ms
        self.el_service_timeout = args.get("el_service_timeout", 3000)

        # 开启召回方向
        self.enabled_subgraph_direct = args.get("enabled_subgraph_direct", False)