import logging


logger = logging.getLogger()


class TableData:
    def __init__(self):
        self.header = []
        self.data = []
        self.total = 0

    @staticmethod
    def from_dict(json_dict):
        entity = TableData()
        entity.header = json_dict["header"]
        entity.data = json_dict["data"]
        entity.total = len(entity.data)
        return entity
