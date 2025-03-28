from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG


def get_default_chat_llm_config():
    if "chat_llm" in KAG_CONFIG.all_config:
        return KAG_CONFIG.all_config["chat_llm"]
    if "llm" in KAG_CONFIG.all_config:
        return KAG_CONFIG.all_config["llm"]
    raise RuntimeError("not found chat_llm config")


class LogicFormConfiguration:
    def __init__(self, args={}):
        self.resource_path = args.get("resource_path", "./")

        self.prefix = args.get("prefix", "")

        # kg graph project ID.
        self.project_id = (
            args.get("KAG_PROJECT_ID", None) or KAG_PROJECT_CONF.project_id
        )
        if not self.project_id:
            raise RuntimeError(
                "init LogicFormConfiguration failed, not found params KAG_PROJECT_ID"
            )

        # kg graph schema file path.
        self.schema_file_name = args.get("schema_file_name", "")

        self.host_addr = (
            args.get("KAG_PROJECT_HOST_ADDR", None) or KAG_PROJECT_CONF.host_addr
        )

        if not self.host_addr:
            raise RuntimeError(
                "init LogicFormConfiguration failed, not found params KAG_PROJECT_HOST_ADDR"
            )
