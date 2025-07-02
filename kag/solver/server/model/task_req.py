import json
from typing import Optional

from pydantic import BaseModel, model_validator, field_serializer


class ReqBody(BaseModel):
    query: str = ""
    report: bool = True
    host_addr: str = ""


class TaskReq(BaseModel):
    app_id: int = ""
    project_id: int = 0
    req_id: str = ""
    cmd: str = ""
    mode: str = ""
    req: str = None
    config: str = "{}"

    @model_validator(mode="after")
    def parse_req_to_req_body(self):
        try:
            import json
            if isinstance(self.req, str):
                req_body_dict = json.loads(self.req)
                self.req = ReqBody(**req_body_dict)
            if isinstance(self.config, str) and self.config:
                config_dict = json.loads(self.config)
                self.config = config_dict
        except Exception as e:
            raise ValueError(f"Failed to parse 'req' field to ReqBody: {e}")
        return self

    @field_serializer("req")
    def serialize_req(self, value: object) -> object:
        """将 ReqBody 再次序列化为 JSON 字符串"""
        if isinstance(value, ReqBody):
            return value.model_dump_json()
        return value  # 如果仍为字符串则直接返回


# 新增的 Request 模型
class Request(BaseModel):
    in_string: str
    task_req: Optional[TaskReq] = None

    @model_validator(mode="after")
    def parse_in_string_to_task_req(self):
        try:
            import json
            task_req_dict = json.loads(self.in_string)
            self.task_req = TaskReq(**task_req_dict)
        except Exception as e:
            raise ValueError(f"Invalid TaskReq JSON string: {e}")
        return self


class FeatureRequest(BaseModel):
    features: Request


if __name__ == "__main__":
    def feature_request_parsing():
        # 构建最内层的 ReqBody JSON 字符串
        req_body = ReqBody(query="阿里巴巴财报中，2024年-截至9月30日止六个月的收入是多少？其中云智能集团收入是多少？占比是多少", report=True, host_addr="https://spg.alipay.com")
        req_body_json = json.dumps(req_body.model_dump())

        # 构建 TaskReq 字典并序列化成字符串
        task_req = TaskReq(
            req_id="9400110",
            cmd="submit",
            mode="async",
            req=req_body_json,
            app_id="app_id",
            project_id=4200050,
            config={"timeout": 10}
        )
        task_req_json = json.dumps(task_req.model_dump())

        # 构造最终传入的 FeatureRequest JSON 字符串
        input_data = {
            "features": {
                "in_string": task_req_json
            }
        }

        # 反序列化为 FeatureRequest 模型
        feature_request = FeatureRequest(**input_data)

        # 验证 in_string 被解析为 TaskReq
        assert isinstance(feature_request.features.task_req, TaskReq)
        assert feature_request.features.task_req.req_id == "abc123"
        assert feature_request.features.task_req.cmd == "run"
        assert feature_request.features.task_req.mode == "sync"
        assert feature_request.features.task_req.config == {"timeout": 10}

        # 验证 TaskReq.req 被解析为 ReqBody
        req_body_parsed = feature_request.features.task_req.req
        assert isinstance(req_body_parsed, ReqBody)
        assert req_body_parsed.query == "What is AI?"
        assert req_body_parsed.report is True
        assert req_body_parsed.host_addr == "localhost"

        print("✅ All assertions passed!")


    feature_request_parsing()
