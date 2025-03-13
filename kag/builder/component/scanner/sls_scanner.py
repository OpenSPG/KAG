from kag.common.utils import generate_hash_id
from kag.interface.builder.scanner_abc import ScannerABC
from typing import Any, Generator, List
import time
from aliyun.log.logclient import LogClient
from aliyun.log.getlogsrequest import GetLogsRequest
from aliyun.log.putlogsrequest import PutLogsRequest
from aliyun.log.logitem import LogItem


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
        **kwargs
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
    for i in range(0, test_item_count):
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
    scanner = SLSScanner(
        project=config["project"],
        logstore=config["logStore"],
        endpoint=config["endPoint"],
        access_id=config["accessKeyId"],
        access_key=config["accessKeySecret"],
        cols_name=["user", "avg"],
    )

    # 获取最近10分钟的日志
    time_range = [int(time.time()) - 600, int(time.time())]
    for log in scanner.generate(time_range):
        print(log)


if __name__ == "__main__":
    main()
    _prepare_data()
