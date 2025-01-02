import json

from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.implementation.default_memory import DefaultMemory
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.solver.implementation.table.table_reasoner import TableReasoner


class FinStateSolver(SolverPipeline):
    """
    solver
    """

    def __init__(
        self, max_run=3, reflector=None, reasoner=None, generator=None, **kwargs
    ):
        super().__init__(max_run, reflector, reasoner, generator, **kwargs)
        self.table_reasoner = TableReasoner(**kwargs)

    def run(self, question):
        """
        Executes the core logic of the problem-solving system.

        Parameters:
        - question (str): The question to be answered.

        Returns:
        - tuple: answer, trace log
        """
        return self.table_reasoner.reason(question)


def load_test_case():
    import pandas as pd
    domain_knowledges = "在当前会话注入领域知识\n" + "\n".join([
        """医疗保险的剩余额度是通过从保险最高赔付额度中减去已经赔付的金额来计算的。而在计算医疗保险能够理赔的具体金额时，首先需要确定本次医疗总花费减去医保报销的部分和免赔额度后的剩余金额，然后比较这个数值与保险的剩余额度，取较小的那个值，最后根据保险合同中规定的保率来决定最终可以报销的金额。这种方式确保了理赔金额既不会超过实际需要补偿的部分，也不会超出保险当前可提供的最大赔偿范围。
示例背景
医疗保险最高赔付额度：100,000元
已赔付金额：30,000元
当前保险剩余额度：100,000元 - 30,000元 = 70,000元
本次医疗总花费：50,000元
医保报销部分：20,000元
免赔额度：5,000元
保险合同中规定的保率（报销比例）：80%
理赔计算步骤
1、计算本次医疗需由保险理赔的金额：
本次医疗总花费 - 医保报销部分 - 免赔额度 = 25000
2、比较计算出的需理赔金额与保险剩余额度：
显然25000小于70000，取较小值25000
3、根据保险合同中的保率计算最终可报销金额：
25000乘以80% = 20000
结论
根据以上计算，本次医疗事件中，保险公司最终可以报销20,000元。这一金额既不超过本次需要补偿的25,000元，也在保险当前剩余的70,000元赔付额度范围内。
""",
        """绝大部分的基金的单位净值都是1元。例如我们申购10000元的货币基金，那么，得到的货币基金份额就是10000/1=10000份。货币基金有两个重要的收益率指标：一个是7日年化收益率。7日年化收益率是计算了货币基金最近7天（包含节假日）的收益，再将其折算成年收益率。比如显示的7日年化收益率是2.12%，意思就是，将过去7天货币基金的收益折算成年收益率为2.12%。这个收益率并不代表未来一年一定能获得2.12%的收益，只能说按照过去7天的收益去推算未来一年，我们能获得的收益是2.12%。另一个收益率指标是每万份基金单位收益。货币基金的单位净值都是1元，如果我们持有10000份货币基金，那对应的基金净值就是10000元。那么，每万份基金单位收益，衡量的就是，假如我们持有10000份货币基金（也就是对应10000元的基金净值），一天能获得多少钱的收益。每万份收益比7日年化收益反映了更真实的收益水平，但只能看到一天的真实数据，还是不能展示一只货币基金的长期真实的收益水平。费率方面，货币基金不收取申购费/赎回费，但收取管理费/托管费/销售服务费，这些已在每天产生的收益中扣除，并按月支付。"""
        """"7日年化收益率计算方式：
1. **计算七日收益率**：
   七日收益率 = (结束时的价格 - 开始时的价格) / 开始时的价格
2. **计算年化收益率**：
   年化收益率 = 七日收益率 × (365 / 7)
"""
    ])
    solver = FinStateSolver(KAG_PROJECT_ID=1)
    solver.run(domain_knowledges)
    # 读取 Excel 文件
    df = pd.read_excel("/Users/peilong/Downloads/数值计算-Bailing-4.0-80B-16K-Chat-20241120-蚂蚁业务计算.xlsx")
    cases = df.to_dict()
    test_case = cases['样本内容']
    def generate_question(d):
        try:
            d = json.loads(d)
            choose = []
            for k in d.keys():
                if k == 'question':
                    continue
                choose.append(f"{k}:{d[k]}")
            choose_text = '\n'.join(choose)
            info = f"题目:{d['question']}\n 选项 {choose_text}"
        except:
            info = d
        return "以下是关于蚂蚁业务计算的单项选择题，请给出正确答案的选项和理由，如果无法确定，则不选，但要输出理由。\n" + info

    data = {
        'question': [],
        'llm_output': []
    }
    solver = FinStateSolver(KAG_PROJECT_ID=1)
    for _, c in test_case.items():
        question = generate_question(c)
        response = solver.run(question)
        # response = solver.table_reasoner.llm_module.invoke({
        #     "input": f"{domain_knowledges}\n{question}"
        # }, solver.table_reasoner.direct_call_prompt)
        print("*" * 80)
        print(question)
        print("*" * 20)
        print(response)
        print("*" * 80)
        data['question'].append(question)
        data['llm_output'].append(response)
    # 打印 DataFrame 的前几行
    df_out = pd.DataFrame(data)

    # 将 DataFrame 写入 Excel 文件
    df_out.to_excel('蚂蚁业务计算-badcase-kag.xlsx', index=False)
if __name__ == "__main__":
    solver = FinStateSolver(KAG_PROJECT_ID=1)
    #question = "阿里巴巴最新的营业收入是多少，哪个部分收入占比最高，占了百分之多少？"
    #question = "阿里国际数字商业集团24年截至9月30日止六个月的收入是多少？它的经营利润率是多少？"
    question = "阿里巴巴财报中，2024年-截至9月30日止六个月的收入是多少？收入中每个部分分别占比多少？"
    #question = "可持续发展委员会有哪些成员组成"
    #question = "公允价值计量表中，24年9月30日，第二级资产各项目哪个占比最高，占了百分之多少？"
    # question = "231243423乘以13334233等于多少？"
    # question = "李妈妈有12个糖果，她给李明了3个，李红4个，那么李妈妈还剩下多少个糖果？"
    # question = "根据财报信息，给出阿里巴巴的收入情况"
    # question = "9乘以-1是否大于0"
    question = "根据财报信息，给出阿里巴巴的收入明细情况"
    question = """请做下面的选择题{"A":"10399","B":"10400","C":"10405","D":"52000","question":"假定我所有的医疗开销为22,000元，医保负担了其中的9,000元，先前治疗已获得10,000元赔付，假定我持有一款保险产品，该产品将报销80%的医疗费用，保险的免赔额度是0元，保险的最高赔付额度是10万元，我还可以期待这份保险赔付多少？"}"""
    load_test_case()
    response = solver.run(question)
    print("*" * 80)
    print(question)
    print("*" * 20)
    print(response)
    print("*" * 80)
