from kag.common.utils import generate_hash_id
from kag.interface.builder.scanner_abc import ScannerABC
from typing import Any, Generator, List
import time
from aliyun.log.logclient import LogClient
from aliyun.log.getlogsrequest import GetLogsRequest
from aliyun.log.putlogsrequest import PutLogsRequest
from aliyun.log.logitem import LogItem
from aliyun.log.consumer import ConsumerProcessorBase
from threading import RLock
from aliyun.log.consumer import ConsumerWorker, LogHubConfig, CursorPosition
from queue import Queue


@ScannerABC.register("sls_scanner")
class SLSScanner(ScannerABC):
    def __init__(
        self,
        project=None,
        logstore=None,
        endpoint=None,
        access_id=None,
        access_key=None,
        cols_name=None,
        **kwargs,
    ):
        """
        Initialize the SLS Scanner.

        Args:
            project (str): SLS project name
            logstore (str): SLS logstore name
            client (LogClient): SLS client instance
            topic (str): SLS topic for filtering
            time_range (int): Time range in seconds to look back for logs
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.project = project
        self.logstore = logstore
        self.client = LogClient(
            endpoint=endpoint, accessKeyId=access_id, accessKey=access_key
        )
        self.cols_name = cols_name

    def load_data(self, input: Any, **kwargs) -> List[Any]:
        """
        Load data from SLS service.

        Args:
            input: Input source (can be used to override instance settings)
            **kwargs: Additional parameters

        Returns:
            List of log entries
        """

        if not all([self.project, self.logstore, self.client]):
            raise ValueError("Project, logstore and client must be provided")

        from_time = input[0]
        to_time = input[1]

        request = GetLogsRequest(self.project, self.logstore, from_time, to_time)
        response = self.client.get_logs(request)

        return response.get_logs()

    def generate(self, input: Any, **kwargs) -> Generator[Any, Any, None]:
        """
        Generate log entries from SLS service.

        Args:
            input: Input source (can be used to override instance settings)
            **kwargs: Additional parameters including:
                - project: SLS project name
                - logstore: SLS logstore name
                - client: SLS client
                - topic: SLS topic
                - from_time: Start time (can be timestamp or formatted time)
                - to_time: End time (can be timestamp or formatted time)
                - use_formatted_time: Whether to use formatted time
                - get_all: Whether to use get_log_all instead of get_logs

        Yields:
            Log entries from SLS
        """
        data = self.load_data(input, **kwargs)
        for log in data:
            content = log.get_contents()
            if self.cols_name:
                for k, v in content.items():
                    if k in self.cols_name:
                        v = str(v)
                        name = v if len(v) < 10 else v[:5] + "..." + v[-5:]
                        yield {
                            "id": generate_hash_id(v),
                            "name": name,
                            "content": v,
                        }
            else:
                yield content


@ScannerABC.register("sls_consumer_scanner")
class SLSConsumerScanner(ScannerABC):
    def __init__(
        self,
        project=None,
        logstore=None,
        endpoint=None,
        access_id=None,
        access_key=None,
        cols_name=None,
        consumer_group=None,
        consumer_name=None,
        **kwargs,
    ):
        """
        Initialize the SLS Scanner.

        Args:
            project (str): SLS project name
            logstore (str): SLS logstore name
            client (LogClient): SLS client instance
            topic (str): SLS topic for filtering
            time_range (int): Time range in seconds to look back for logs
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.project = project
        self.logstore = logstore
        self.endpoint = endpoint
        self.access_id = access_id
        self.access_key = access_key
        self.consumer_group = consumer_group or "kag_consumer_group"
        self.consumer_name = consumer_name or "kag_consumer"
        if self.sharding_info.shard_count > 1:
            self.consumer_name = f"{self.consumer_name}_{self.sharding_info.get_rank()}"
        self.client = LogClient(
            endpoint=endpoint, accessKeyId=access_id, accessKey=access_key
        )
        self.cols_name = cols_name

    def load_data(self, input: Any, **kwargs) -> List[Any]:
        """
        Load data from SLS service.

        Args:
            input: Input source (can be used to override instance settings)
            **kwargs: Additional parameters

        Returns:
            List of log entries
        """

        if not all([self.project, self.logstore, self.client]):
            raise ValueError("Project, logstore and client must be provided")

        option = LogHubConfig(
            self.endpoint,
            self.access_id,
            self.access_key,
            self.project,
            self.logstore,
            self.consumer_group,
            self.consumer_name,
            cursor_position=CursorPosition.BEGIN_CURSOR,
            heartbeat_interval=6,
            data_fetch_interval=1,
        )

        print("*** start to consume data...")
        client_worker = ConsumerWorker(SLSConsumer, consumer_option=option)
        client_worker.start()

    def generate(self, input: Any, **kwargs) -> Generator[Any, Any, None]:
        """
        Generate log entries from SLS service.

        Args:
            input: Input source (can be used to override instance settings)
            **kwargs: Additional parameters including:
                - project: SLS project name
                - logstore: SLS logstore name
                - client: SLS client
                - topic: SLS topic
                - from_time: Start time (can be timestamp or formatted time)
                - to_time: End time (can be timestamp or formatted time)
                - use_formatted_time: Whether to use formatted time
                - get_all: Whether to use get_log_all instead of get_logs

        Yields:
            Log entries from SLS
        """
        self.load_data(input, **kwargs)

        # Process logs one by one from the queue
        while True:
            try:
                # Non-blocking get with timeout
                log = SLSConsumer.log_queue.get(block=True, timeout=1000.0)

                if self.cols_name:
                    for k, v in log.items():
                        if k in self.cols_name:
                            v = str(v)
                            name = v if len(v) < 10 else v[:5] + "..." + v[-5:]
                            yield {
                                "id": generate_hash_id(v),
                                "name": name,
                                "content": v,
                            }
                else:
                    yield log
            except Exception:  # Queue.Empty will be caught here
                # Just continue waiting for more logs
                # We don't want to exit the loop as we need to continuously process logs
                continue


class SLSConsumer(ConsumerProcessorBase):
    shard_id = -1
    last_check_time = 0
    log_queue = Queue()
    lock = RLock()

    def initialize(self, shard):
        self.shard_id = shard

    def process(self, log_groups, check_point_tracker):
        for log_group in log_groups.LogGroups:
            items = []
            for log in log_group.Logs:
                item = dict()
                item["time"] = log.Time
                for content in log.Contents:
                    item[content.Key] = content.Value
                items.append(item)
            log_items = dict()
            log_items["topic"] = log_group.Topic
            log_items["source"] = log_group.Source
            log_items["logs"] = items

            # Put items in queue instead of appending to list
            for item in items:
                SLSConsumer.log_queue.put(item)

        current_time = time.time()
        if current_time - self.last_check_time > 3:
            try:
                self.last_check_time = current_time
                check_point_tracker.save_check_point(True)
            except Exception:
                import traceback

                traceback.print_exc()
        else:
            try:
                check_point_tracker.save_check_point(False)
            except Exception:
                import traceback

                traceback.print_exc()

        # None means succesful process
        # if need to roll-back to previous checkpoint，return check_point_tracker.get_check_point()
        return None

    def shutdown(self, check_point_tracker):
        try:
            check_point_tracker.save_check_point(True)
        except Exception:
            import traceback

            traceback.print_exc()


test_item_count = 20
config = {
    "endPoint": "cn-test-ant-eu95.log.aliyuncs.com",
    "logStore": "odps_channel_rt",
    "project": "ant-q-kgwriter-eu95-offline",
    "accessKeyId": "",
    "accessKeySecret": "",
}


def _prepare_data():
    topic = "python-ide-test"
    source = ""
    client = LogClient(
        endpoint=config["endPoint"],
        accessKeyId=config["accessKeyId"],
        accessKey=config["accessKeySecret"],
    )
    starter = 0
    for i in range(starter, starter + test_item_count):
        logitemList = []  # LogItem list

        contents = [("user", "magic_user_" + str(i)), ("avg", "magic_age_" + str(i))]
        logItem = LogItem()
        logItem.set_time(int(time.time()))
        logItem.set_contents(contents)

        logitemList.append(logItem)
        # 将日志写入Logstore。
        request = PutLogsRequest(
            config["project"], config["logStore"], topic, source, logitemList
        )

        _ = client.put_logs(request)
        print("successfully put logs in logstore")


def main():
    """
    演示如何使用SLSScanner获取日志

    示例配置:
    - endPoint: SLS服务地址
    - logStore: 日志库名称
    - project: 项目名称
    - accessKeyId: 访问ID
    - accessKeySecret: 访问密钥
    """

    # 初始化SLSScanner
    # scanner = SLSScanner(
    #     project=config["project"],
    #     logstore=config["logStore"],
    #     endpoint=config["endPoint"],
    #     access_id=config["accessKeyId"],
    #     access_key=config["accessKeySecret"],
    #     cols_name=["user", "avg"],
    # )

    consumer_scanner = SLSConsumerScanner(
        project=config["project"],
        logstore=config["logStore"],
        endpoint=config["endPoint"],
        access_id=config["accessKeyId"],
        access_key=config["accessKeySecret"],
        cols_name=["user", "avg"],
    )

    # # 获取最近10分钟的日志
    # time_range = [int(time.time()) - 600, int(time.time())]
    # for log in scanner.generate(time_range):
    #     print(log)

    for log in consumer_scanner.generate("time_range"):
        print(log)


if __name__ == "__main__":
    _prepare_data()

    # main()
