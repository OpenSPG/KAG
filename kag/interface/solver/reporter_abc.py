import logging
import asyncio

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