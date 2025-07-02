from fastapi import FastAPI
import uvicorn

from kag.solver.main_solver import SolverMain
from kag.solver.server.asyn_task_manager import AsyncTaskManager
from kag.solver.server.model.task_req import FeatureRequest, TaskReq


def run_main_solver(task: TaskReq):
    return SolverMain().invoke(
        project_id=task.project_id,
        task_id=task.req_id,
        query=task.req.query,
        is_report=task.req.report,
        host_addr=task.req.host_addr,
        app_id=task.app_id,
        params=task.config,
    )

class KAGSolverServer:
    def __init__(self, service_name: str):
        """
        初始化 FastAPI 服务实例

        Args:
            service_name (str): 服务名称，决定加载哪个路由逻辑
        """
        self.service_name = service_name
        self.app = FastAPI(title=f"{service_name} API")

        # 根据服务名绑定路由
        self._setup_routes()
        self.async_manager = AsyncTaskManager()

    def sync_task(self, task: TaskReq):
        if task.cmd == "submit":

            return {
                'success': True,
                'status': 'init',
                'result': self.async_manager.submit_task(run_main_solver, task)
            }
        elif task.cmd == "query":
            return self.async_manager.get_task_result(task_id=task.req_id)
        else:
            return {
                "success": False,
                "status": "failed",
                "result": f"invalid input cmd {task.cmd}",
            }

    def _setup_routes(self):
        """根据服务名动态绑定路由"""
        @self.app.post("/process")
        def process(req: FeatureRequest):
            return self.sync_task(task=req.features.task_req)

    def run(self, host="0.0.0.0", port=8000):
        """启动服务"""
        print(f"Starting {self.service_name} service on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)