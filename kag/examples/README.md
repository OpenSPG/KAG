# Example
## Create project
Create your new knext project from knext cli tool.
* Edit your config file like example.cfg
    ```python
    [project]
    project_name = KagDemo
    description = A knext demo project showcasing KAG features.
    namespace = KagDemo
    project_dir = kagdemo
    host_addr = http://localhost:8887

    [vectorizer]
    vectorizer = knext.common.vectorizer.OpenAIVectorizer
    model = bge-m3
    api_key = EMPTY
    base_url = http://127.0.0.1:11434/v1
    vector_dimensions = 1024

    [llm]
    client_type = ollama
    base_url = http://localhost:11434/api/generate
    model = llama3.1

    [prompt]
    biz_scene = default
    language = zh

    [indexer]
    with_semantic = False
    similarity_threshold = 0.8

    [retriever]
    with_semantic = False
    pagerank_threshold = 0.9
    match_threshold = 0.8
    top_k = 10

    [log]
    level = INFO

    ```
* Run command:
  ```sh
  kag project create --config_path example.cfg
  ```
* Put your source data in {project_dir}/builder/data (in the example kagdemo, we put a pdf file in the data directory.)
* Edit and your schema file.(**Optional**)
  * Edit the schema in {project_dir}/schema/{project_name}.schema
  * Run command in work directory {project_dir}:
    ```sh
    knext schema commit
    ```
* **Define your BuilderChain**:
  * In the {project_dir}/builder/indexer.py, define your BuilderChain by extend the BuilderChainABC class and override the build method. For example:
    ```python
        import os

        from kag.builder.component.reader import DocxReader, PDFReader
        from kag.builder.component.splitter import LengthSplitter, OutlineSplitter
        from knext.builder.builder_chain_abc import BuilderChainABC
        from kag.builder.component.extractor import KAGExtractor
        from kag.builder.component.writer import KGWriter
        from kag.solver.logic.solver_pipeline import SolverPipeline
        import logging
        from kag.common.env import init_kag_config


        logger = logging.getLogger(__name__)

        file_path = os.path.dirname(__file__)

        suffix_mapping = {
            "docx": DocxReader,
            "pdf": PDFReader
        }

        class KagDemoBuildChain(BuilderChainABC):

            def build(self, **kwargs):
                file_path = kwargs.get("file_path","a.docx")
                suffix = file_path.split(".")[-1]
                reader = suffix_mapping[suffix]()
                if reader is None:
                    raise NotImplementedError
                length_splitter = LengthSplitter(split_length=8000)
                outline_splitter = OutlineSplitter()
                project_id = int(os.getenv("KAG_PROJECT_ID"))
                extractor = KAGExtractor(project_id=project_id)
                writer = KGWriter()

                chain = reader >> length_splitter >> outline_splitter >> extractor >> writer
                return chain

        def buildKG(test_file,**kwargs):
            chain = KagDemoBuildChain(file_path = test_file)
            chain.invoke(test_file, max_workers=10)


        if __name__ == "__main__":
            init_kag_config(os.path.join(file_path,"../../../tests/builder/component/test_config.cfg"))
            test_docx = os.path.join(file_path,"../../../tests/builder/data/test_docx.docx")
            test_pdf = os.path.join(file_path,"../../../tests/builder/data/KnowledgeGraphTutorialSub.pdf")
            buildKG(test_pdf)
    ```
  * Build Knowledge Graph by run:
    ```sh
    python {project_dir}/builder/indexer.py
    ```

* Question Answer(QA):
  * Define SolverPipeline in {project_dir}/solver/evalFor{project_name}.py, for example:
    ```python
    import logging
    import os

    from kag.common.env import init_kag_config
    from kag.solver.logic.solver_pipeline import SolverPipeline

    logger = logging.getLogger(__name__)


    class KagDemo:

        """
        init for kag client
        """

        def __init__(self):
            pass

        def qa(self, query):
            # CA
            resp = SolverPipeline()
            answer, trace_log = resp.run(query)

            return answer,trace_log

        """
            parallel qa from knowledge base
            and getBenchmarks(em, f1, answer_similarity)

        """


    if __name__ == "__main__":
        demo = KagDemo()
        query = "什么知识图谱是什么？"
        answer,trace_log = demo.qa(query)
        print(f"Question: {query}")
        print(f"Answer: {answer}")
        print(f"TraceLog: {trace_log}")

    ```
  * Run command:
    ```sh
    python {project_dir}/solver/evaFor{project_name}.py
    ```


## Restore project
If you have a project locally but do **not** have in spgserver, **restore** cmd will recover your local project in the spgserver, for example:

 ```sh
knext project recover --host_addr http://{host_ip}:8887 --proj_path {proj_path}
```


## Update project
If you want to update your kag_config.cfg file, you can edit it and use update cmd, for example:
```sh
knext project update --proj_path {proj_path}
```
