from kag.common.utils import generate_hash_id
from odps import ODPS
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
            chunk_size = kwargs.get("chunk_size", 1000)
            # 只有当表有分区且input不为空时才使用分区
            partition_spec = (
                input if input and self.table.table_schema.partitions else None
            )

            logger.debug(
                f"Generating data row by row (internal batch size: {chunk_size})"
            )
            if self.limit is not None:
                logger.debug(f"Row limit set to {self.limit}")

            # Get the reader with partition if specified
            with self.table.open_reader(partition=partition_spec) as reader:
                logger.debug(f"Reader created with partition: {partition_spec}")
                logger.debug(f"Total records available: {reader.count}")

                # Calculate sharding information for proper distribution
                if self.sharding_info.shard_count > 1:
                    total_count = reader.count
                    start, end = self.sharding_info.get_sharding_range(total_count)
                    worker = f"{self.sharding_info.get_rank()}/{self.sharding_info.get_world_size()}"
                    logger.debug(
                        f"Worker {worker} processing records from {start} to {end}"
                    )

                    # Skip to the start position if needed
                    if start > 0:
                        reader.skip(start)
                        logger.debug(f"Skipped {start} records")

                    # Calculate how many records to read
                    records_to_read = end - start
                    logger.debug(f"Will read {records_to_read} records")
                else:
                    records_to_read = None  # Read all records
                    start = 0
                    logger.debug("No sharding, will read all records")

                # Implement our own chunking logic for internal fetching
                if records_to_read is not None:
                    remaining = records_to_read
                else:
                    remaining = reader.count - start

                logger.debug(
                    f"Starting to read {remaining} records (internal batch size: {chunk_size})"
                )
                current_offset = 0
                chunk_number = 0

                # Get column names for converting records to dictionaries
                column_names = [c.name for c in reader.schema.columns]

                while remaining > 0:
                    # Read a chunk of records
                    batch_size = min(chunk_size, remaining)
                    logger.debug(
                        f"Reading internal batch {chunk_number}, batch size: {batch_size}"
                    )

                    try:
                        # Option 1: Use the reader as an iterator with limit
                        batch_records = list(reader[:batch_size])
                    except Exception:
                        try:
                            # Option 2: Original method but ensure it's not at the end
                            batch_records = list(reader.read(batch_size))
                        except Exception as inner_e:
                            logger.debug(f"Error reading batch: {str(inner_e)}")
                            batch_records = []

                    logger.debug(f"Got {len(batch_records)} records in this batch")

                    # If no records, break the loop
                    if not batch_records:
                        logger.debug("No more records to read, breaking loop")
                        break

                    # Yield records one by one with limit
                    rows_yielded = 0
                    for record in batch_records:
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

                    # Update remaining count
                    remaining -= batch_size
                    current_offset += batch_size
                    chunk_number += 1
                    logger.debug(f"Remaining records: {remaining}")

                    if remaining <= 0:
                        logger.debug("No more records to read, breaking loop")
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
