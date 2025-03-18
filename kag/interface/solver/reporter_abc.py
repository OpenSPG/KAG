from kag.common.registry import Registrable


class ReporterABC(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def report(self, segment, tag_name, content, status):
        raise NotImplementedError()