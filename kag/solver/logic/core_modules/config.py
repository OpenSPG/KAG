class LogicFormConfiguration:

    def __init__(self, args={}):
        self.resource_path = args.get("resource_path", "./")

        self.prefix = args.get("prefix", "")

        # kg graph project ID.
        self.project_id = args.get("project_id", "1")

        # kg graph schema file path.
        self.schema_file_name = args.get("schema_file_name", "")

        self.host_addr = args.get("host_addr", "http://127.0.0.1:8887")

