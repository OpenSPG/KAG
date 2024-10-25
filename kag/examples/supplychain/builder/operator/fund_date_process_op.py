from abc import ABC
from typing import Dict, List

from knext.common.base.component import Component
from knext.common.base.runnable import Output, Input


def change_new_date(a: str, b: str):
    from datetime import datetime, timedelta

    date_format = "%Y%m%d"
    date_a = datetime.strptime(a, date_format)
    date_b = datetime.strptime(b, date_format)

    n_days_difference = (date_b - date_a).days

    current_date = datetime.now()

    new_b_date = current_date + timedelta(days=n_days_difference)

    new_b_str = new_b_date.strftime(date_format)
    return new_b_str


class FundDateProcessComponent(Component, ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process_trans_date(self, record: Dict[str, str]) -> Dict[str, str]:
        cur_trans_date = record.get("transDate")
        mock_cur_date = "20230901"
        record["transDate"] = change_new_date(mock_cur_date, cur_trans_date)
        return record

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        return [self.process_trans_date(input)]
