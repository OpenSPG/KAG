from kag.common.utils import generate_hash_id
from kag.interface.builder.scanner_abc import ScannerABC
from typing import Any, Generator, List

import logging

logger = logging.getLogger(__name__)


@ScannerABC.register("odps_scanner")
class ODPSScanner(ScannerABC):
    def __init__(
        self,
        access_id,
        access_key,
        project,
        table,
        endpoint,
        col_names=None,
        col_ids=None,
        limit=None,
        pre_load=False,
    ):
        super().__init__()
        self.access_id = access_id
        self.access_key = access_key
        self.project = project
        self.table = table
        self.endpoint = endpoint
        self.col_names = col_names
        self.col_ids = col_ids
        self.limit = limit
        self.pre_load = pre_load
        from odps import ODPS

        self._o = ODPS(self.access_id, self.access_key, self.project, self.endpoint)
        if not self._o.exist_table(self.table):
            raise Exception(f"table {self.table} not exist in project {self.project}")
        self.table = self._o.get_table(self.table)

        # 打印表的基本信息
        logger.debug(f"Table {self.table.name} info:")
        logger.debug(f"  - Schema: {self.table.table_schema}")
        logger.debug(
            f"  - Partitions: {[p.name for p in self.table.table_schema.partitions]}"
        )

        # 如果有分区，列出所有分区
        if self.table.table_schema.partitions:
            logger.debug("  - Available partitions:")
            for p in self.table.partitions:
                logger.debug(f"      {p.name}")

    def size(self, input):
        partition_spec = input if input and self.table.table_schema.partitions else None
        with self.table.open_reader(partition=partition_spec) as reader:
            logger.debug(f"Reader created with partition: {partition_spec}")
            logger.debug(f"Total records available: {reader.count}")
            total_count = reader.count
            start, end = self.sharding_info.get_sharding_range(total_count)
            return end - start

    def reload(self):
        self.table.reload()

    def load_data(self, input: str, **kwargs) -> List[Any]:
        """
        Load all data from ODPS and return as a list.
        This method is used by the default generate implementation.

        Args:
            input (str): The partition specification or value
            **kwargs: Additional parameters like columns

        Returns:
            List[Any]: A list containing all records as pandas DataFrames
        """
        try:
            partition_spec = (
                input if input and self.table.table_schema.partitions else None
            )

            import pandas as pd

            # Get all data as a DataFrame
            with self.table.open_reader(partition=partition_spec) as reader:
                logger.debug(
                    f"Reading data from {self.table.name}{' with partition ' + partition_spec if partition_spec else ''}"
                )
                logger.debug(f"Total records in this query: {reader.count}")

                records = list(reader)
                logger.debug(f"Got {len(records)} records")

                df = pd.DataFrame(
                    [r.values for r in records],
                    columns=[c.name for c in reader.schema.columns],
                )
                logger.debug(f"Created DataFrame with all columns, shape: {df.shape}")

            # Apply row filtering if specified

            # Apply limit if specified
            if self.limit is not None:
                df = df.head(self.limit)
                logger.debug(
                    f"Applied row limit of {self.limit}, DataFrame shape: {df.shape}"
                )

            return [df]
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            raise Exception(f"Failed to load data from ODPS: {str(e)}\n{error_details}")

    def generate(self, input: str, **kwargs) -> Generator[Any, None, None]:
        """
        Generate rows from ODPS one by one.

        Args:
            input (str): The partition specification or value
            **kwargs: Additional parameters

        Yields:
            dict: Individual records as dictionaries
        """
        try:
            # 只有当表有分区且input不为空时才使用分区
            partition_spec = (
                input if input and self.table.table_schema.partitions else None
            )

            if self.limit is not None:
                logger.debug(f"Row limit set to {self.limit}")

            # Get the reader with partition if specified
            with self.table.open_reader(partition=partition_spec) as reader:
                logger.debug(f"Reader created with partition: {partition_spec}")
                logger.debug(f"Total records available: {reader.count}")

                raw_reader = reader

                # Calculate sharding information for proper distribution
                if self.sharding_info.shard_count > 1:
                    total_count = reader.count
                    start, end = self.sharding_info.get_sharding_range(total_count)
                    worker = f"{self.sharding_info.get_rank()}/{self.sharding_info.get_world_size()}"
                    logger.debug(
                        f"Worker {worker} processing records from {start} to {end}"
                    )

                    # 直接从起始位置开始读取
                    records_to_read = end - start
                    logger.debug(
                        f"Will read {records_to_read} records from position {start}"
                    )

                    # 使用切片直接获取该分片的数据
                    try:
                        shard_reader = reader[start:end]
                        logger.debug(
                            f"Successfully created shard reader for range {start}:{end}"
                        )
                        start = 0
                    except Exception as e:
                        logger.warning(
                            f"Failed to create shard reader: {str(e)}, falling back to manual filtering"
                        )
                else:
                    records_to_read = reader.count  # Read all records
                    shard_reader = reader[:]
                    start = 0
                    logger.debug("No sharding, will read all records")

                # Get column names for converting records to dictionaries
                column_names = [c.name for c in raw_reader.schema.columns]

                # Yield records one by one with limit
                rows_yielded = 0
                if self.pre_load:
                    records = list(shard_reader)
                    logger.info(f"Pre-loaded {len(records)} records")
                else:
                    records = shard_reader

                for record in records:
                    if self.limit is not None and rows_yielded >= self.limit:
                        logger.debug(
                            f"Reached row limit of {self.limit}, stopping generation"
                        )
                        break

                    row_dict = dict(zip(column_names, record.values))

                    col_keys = self.col_names if self.col_names else self.col_ids
                    if col_keys is None:
                        logger.debug(
                            "No columns specified, returning all rows as dictionaries"
                        )
                        yield row_dict
                        rows_yielded += 1
                    else:
                        for k, v in row_dict.items():
                            if k in col_keys:
                                v = str(v)
                                name = v if len(v) < 10 else v[:5] + "..." + v[-5:]
                                yield {
                                    "id": generate_hash_id(v),
                                    "name": name,
                                    "content": v,
                                }
                                rows_yielded += 1
                                if (
                                    self.limit is not None
                                    and rows_yielded >= self.limit
                                ):
                                    break

                    # Check limit after processing each record
                    if self.limit is not None and rows_yielded >= self.limit:
                        logger.debug(
                            f"Reached row limit of {self.limit}, stopping generation"
                        )
                        break

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            raise Exception(
                f"Failed to generate data from ODPS: {str(e)}\n{error_details}"
            )

    def invoke(self, input: str, **kwargs) -> Any:
        """
        Invoke the scanner to get all data at once.

        Args:
            input (str): The partition specification or value
            **kwargs: Additional parameters

        Returns:
            pandas.DataFrame: All data combined into a single DataFrame
        """
        import pandas as pd

        logger.debug(f"Invoking scanner with input: {input}")

        # Collect all rows from the generator
        rows = list(self.generate(input, **kwargs))

        logger.debug(f"Got {len(rows)} rows")

        if not rows:
            logger.debug("No data returned, returning empty DataFrame")
            return pd.DataFrame()

        # Convert collected rows (dictionaries) to a DataFrame
        result = pd.DataFrame(rows)
        logger.debug(f"Combined result shape: {result.shape}")

        # Process the data based on column parameters
        col_keys = self.col_names if self.col_names else self.col_ids
        if col_keys is None:
            logger.debug("No columns specified, returning all rows as dictionaries")
            return result.to_dict(orient="records")

        contents = []
        for _, row in result.iterrows():
            for k, v in row.items():
                if k in col_keys:
                    v = str(v)
                    name = v[:5] + "..." + v[-5:]
                    contents.append(
                        {"id": generate_hash_id(v), "name": name, "content": v}
                    )

        return contents
