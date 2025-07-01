import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional
from kag.common.registry import Registrable

logger = logging.getLogger()


class ReporterABC(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._running = True
        self._monitor_task_coroutine = None

    def add_report_line(self, segment, tag_name, content, status, **kwargs):
        raise NotImplementedError()

    def do_report(self):
        raise NotImplementedError()

    async def start(self):
        self._monitor_task_coroutine = asyncio.create_task(self.do_cycle_report())
        logging.info("reporter is starting")

    async def stop(self):
        """
        停止任务
        """
        self._running = False
        if self._monitor_task_coroutine:
            await self._monitor_task_coroutine
        logging.info("reporter is stop")

    async def do_cycle_report(self):
        try:
            while self._running:
                try:
                    # 定期获取数据
                    await asyncio.sleep(1)

                    self.do_report()
                except asyncio.CancelledError:
                    logging.info("reporter is cancel")
                except Exception as e:
                    logging.error(f"reporter is error: {e}", exc_info=True)
            self.do_report()
        except asyncio.CancelledError:
            logging.info("reporter is cancel")
        except Exception as e:
            logging.error(f"reporter is error: {e}", exc_info=True)
        finally:
            self._running = False


def do_report(content, status, **kwargs):
    reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
    segment_name = kwargs.get("segment_name", None)
    tag_name = kwargs.get("tag_name", None)
    if reporter and segment_name and tag_name:
        reporter.add_report_line(
            segment=segment_name, content=content, status=status, **kwargs
        )


class DotRefresher:
    def __init__(self, reporter, segment, tag_name, content, params, interval=1):
        self.reporter = reporter
        self.segment = segment
        self.tag_name = tag_name
        self.content = content
        self.interval = interval
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.future: Optional[Future] = None
        self.params = params

    def _update_status(self):
        update_dot_count = 1
        if not self.reporter:
            return
        kwargs = dict(self.params)

        while self.is_running:
            update_dot_count += 1
            show_dot = update_dot_count % 4
            kwargs["refresh"] = "".join(["."] * show_dot)
            self.reporter.add_report_line(
                self.segment, self.tag_name, self.content, "RUNNING", **kwargs
            )
            time.sleep(self.interval)

    def start(self):
        if not self.future or self.future.done():
            self.is_running = True
            self.future = self.executor.submit(self._update_status)

    def stop(self):
        self.is_running = False
        if self.future:
            self.future.done()
        self.executor.shutdown(wait=True)
