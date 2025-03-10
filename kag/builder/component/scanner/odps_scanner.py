from kag.common.utils import generate_hash_id
from odps import ODPS
from kag.interface.builder.scanner_abc import ScannerABC
from typing import Any, Generator, List


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
    ):
        super().__init__()
        self.access_id = access_id
        self.access_key = access_key
        self.project = project
        self.table = table
        self.endpoint = endpoint
        self.col_names = col_names
        self.col_ids = col_ids

        self._o = ODPS(self.access_id, self.access_key, self.project, self.endpoint)
        if not self._o.exist_table(self.table):
            raise Exception(f"table {self.table} not exist in project {self.project}")
        self.table = self._o.get_table(self.table)

        # 打印表的基本信息
        print(f"Table {self.table.name} info:")
        print(f"  - Schema: {self.table.table_schema}")
        print(f"  - Partitions: {[p.name for p in self.table.table_schema.partitions]}")

        # 如果有分区，列出所有分区
        if self.table.table_schema.partitions:
            print("  - Available partitions:")
            for p in self.table.partitions:
                print(f"      {p.name}")

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
            cols = kwargs.get("colns", None)
            rows = kwargs.get("rows", None)
            partition_spec = input

            import pandas as pd

            # Get all data as a DataFrame
            with self.table.open_reader(partition=partition_spec) as reader:
                print(
                    f"Reading data from {self.table.name}{' with partition ' + partition_spec if partition_spec else ''}"
                )
                print(f"Total records in this query: {reader.count}")

                records = list(reader)
                print(f"Got {len(records)} records")

                if cols:
                    df = pd.DataFrame([{k: r[k] for k in cols} for r in records])
                    print(f"Created DataFrame with columns {cols}, shape: {df.shape}")
                else:
                    df = pd.DataFrame(
                        [r.values for r in records],
                        columns=[c.name for c in reader.schema.columns],
                    )
                    print(f"Created DataFrame with all columns, shape: {df.shape}")

            # Apply row filtering if specified
            if rows:
                start, end = rows
                df = df.iloc[start:end]
                print(
                    f"After row filtering [{start}:{end}], DataFrame shape: {df.shape}"
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
            cols = kwargs.get("colns", None)
            chunk_size = kwargs.get(
                "chunk_size", 1000
            )  # Still using chunk size for internal batch fetching
            partition_spec = input

            print(f"Generating data row by row (internal batch size: {chunk_size})")

            # Get the reader with partition if specified
            with self.table.open_reader(partition=partition_spec) as reader:
                print(f"Reader created with partition: {partition_spec}")
                print(f"Total records available: {reader.count}")

                # Calculate sharding information for proper distribution
                if self.sharding_info.shard_count > 1:
                    total_count = reader.count
                    start, end = self.sharding_info.get_sharding_range(total_count)
                    worker = f"{self.sharding_info.get_rank()}/{self.sharding_info.get_world_size()}"
                    print(f"Worker {worker} processing records from {start} to {end}")

                    # Skip to the start position if needed
                    if start > 0:
                        reader.skip(start)
                        print(f"Skipped {start} records")

                    # Calculate how many records to read
                    records_to_read = end - start
                    print(f"Will read {records_to_read} records")
                else:
                    records_to_read = None  # Read all records
                    start = 0
                    print("No sharding, will read all records")

                # Implement our own chunking logic for internal fetching
                if records_to_read is not None:
                    remaining = records_to_read
                else:
                    remaining = reader.count - start

                print(
                    f"Starting to read {remaining} records (internal batch size: {chunk_size})"
                )
                current_offset = 0
                chunk_number = 0

                # Get column names for converting records to dictionaries
                column_names = [c.name for c in reader.schema.columns]

                while remaining > 0:
                    # Read a chunk of records
                    batch_size = min(chunk_size, remaining)
                    print(
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
                            print(f"Error reading batch: {str(inner_e)}")
                            batch_records = []

                    print(f"Got {len(batch_records)} records in this batch")

                    # If no records, break the loop
                    if not batch_records:
                        print("No more records to read, breaking loop")
                        break

                    # Yield records one by one
                    for record in batch_records:
                        if cols:
                            # If specific columns are requested, return only those columns
                            row_dict = {k: record[k] for k in cols}
                        else:
                            # Otherwise, return all columns
                            row_dict = dict(zip(column_names, record.values))

                        yield row_dict

                    # Update remaining count
                    remaining -= batch_size
                    current_offset += batch_size
                    chunk_number += 1
                    print(f"Remaining records: {remaining}")

                    if remaining <= 0:
                        print("No more records to read, breaking loop")
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

        print(f"Invoking scanner with input: {input}")

        # Collect all rows from the generator
        rows = list(self.generate(input, **kwargs))

        print(f"Got {len(rows)} rows")

        if not rows:
            print("No data returned, returning empty DataFrame")
            return pd.DataFrame()

        # Convert collected rows (dictionaries) to a DataFrame
        result = pd.DataFrame(rows)
        print(f"Combined result shape: {result.shape}")

        # Process the data based on column parameters
        col_keys = self.col_names if self.col_names else self.col_ids
        if col_keys is None:
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


if __name__ == "__main__":
    # 尝试多种分区格式
    odps_config = {
        "access_id": "",
        "access_key": "",
        "project": "",
        "table": "",
        "endpoint": "",
        "col_names": ["description"],
    }
    scanner = ODPSScanner(**odps_config)

    # 测试不同的分区格式
    print("\n\n==== 测试 1: 使用dt=20250225 格式 ====")
    try:
        result = scanner.invoke(input="dt=20250226")
        print(f"Total rows: {len(result)}")
        if len(result) > 0:
            print("Data sample:")
            print(result)
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n\n==== 测试 2: 只使用20250225值（自动添加分区名） ====")
    try:
        result = scanner.invoke(input="20250225")
        print(f"Total rows: {len(result)}")
        if len(result) > 0:
            print("Data sample:")
            print(result)
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n\n==== 测试 3: 不指定分区（读取整个表） ====")
    try:
        result = scanner.invoke(input="")
        print(f"Total rows: {len(result)}")
        if len(result) > 0:
            print("Data sample:")
            print(result.head(2))
    except Exception as e:
        print(f"Error: {str(e)}")
