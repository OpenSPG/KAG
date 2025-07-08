import json
from typing import Optional

from pydantic import BaseModel, model_validator, field_serializer


class ReqBody(BaseModel):
    """Request body model containing query parameters"""

    query: str = ""
    report: bool = True
    host_addr: str = ""


class TaskReq(BaseModel):
    """Task request model with validation logic"""

    app_id: int = ""
    project_id: int = 0
    req_id: str = ""
    cmd: str = ""
    mode: str = ""
    req: str = None
    config: str = "{}"

    @model_validator(mode="after")
    def parse_req_to_req_body(self):
        """Parse req string to ReqBody object and process config field"""
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
        """Serialize ReqBody back to JSON string"""
        if isinstance(value, ReqBody):
            return value.model_dump_json()
        return value  # Return as-is if already a string


# Request model with TaskReq parsing capability
class Request(BaseModel):
    """Container model for task request data"""

    in_string: str
    task_req: Optional[TaskReq] = None

    @model_validator(mode="after")
    def parse_in_string_to_task_req(self):
        """Convert in_string JSON string to TaskReq object"""
        try:
            import json

            task_req_dict = json.loads(self.in_string)
            self.task_req = TaskReq(**task_req_dict)
        except Exception as e:
            raise ValueError(f"Invalid TaskReq JSON string: {e}")
        return self


class FeatureRequest(BaseModel):
    """Top-level request wrapper with features container"""

    features: Request


if __name__ == "__main__":

    def feature_request_parsing():
        """Demonstrate nested model parsing workflow"""
        # Build innermost ReqBody JSON string
        req_body = ReqBody(
            query="阿里巴巴财报中，2024年-截至9月30日止六个月的收入是多少？其中云智能集团收入是多少？占比是多少",
            report=True,
            host_addr="https://spg.alipay.com",
        )
        req_body_json = json.dumps(req_body.model_dump())

        # Build TaskReq dictionary and serialize to string
        task_req = TaskReq(
            req_id="9400110",
            cmd="submit",
            mode="async",
            req=req_body_json,
            app_id="app_id",
            project_id=4200050,
            config={"timeout": 10},
        )
        task_req_json = json.dumps(task_req.model_dump())

        # Construct final FeatureRequest JSON string
        input_data = {"features": {"in_string": task_req_json}}

        # Deserialize to FeatureRequest model
        feature_request = FeatureRequest(**input_data)

        # Validate in_string parsed to TaskReq
        assert isinstance(feature_request.features.task_req, TaskReq)
        assert feature_request.features.task_req.req_id == "abc123"
        assert feature_request.features.task_req.cmd == "run"
        assert feature_request.features.task_req.mode == "sync"
        assert feature_request.features.task_req.config == {"timeout": 10}

        # Validate TaskReq.req parsed to ReqBody
        req_body_parsed = feature_request.features.task_req.req
        assert isinstance(req_body_parsed, ReqBody)
        assert req_body_parsed.query == "What is AI?"
        assert req_body_parsed.report is True
        assert req_body_parsed.host_addr == "localhost"

        print("✅ All assertions passed!")

    feature_request_parsing()
