import logging

from kag.common.registry import import_modules_from_path
from kag.interface import RetrieverABC, Task

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    import_modules_from_path("./prompt")

    retriever = RetrieverABC.from_config("outline_chunk_retriever")
    task = Task(executor="", arguments={"query":"开关量输出有哪些设计规范"})
    retrieveOutput = retriever.invoke(task)
