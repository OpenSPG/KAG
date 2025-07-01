# KAG 示例：黑产挖掘（RiskMining）

[English](./README.md) |
[简体中文](./README_cn.md)

**关键词**：语义属性，实体动态多分类，面向业务知识和事实数据分层下的知识应用

![KAG RiskMining Diagram](/_static/images/examples/riskmining/kag-riskmining-diag.png)

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 复现步骤

### Step 1：进入示例目录

```bash
cd kag/examples/riskmining
```

### Step 2：配置模型

更新 [kag_config.yaml](./kag_config.yaml) 中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorize_model``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

### Step 3：初始化项目

先对项目进行初始化。

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4：知识建模

schema 文件已创建好，可执行如下命令提交。参见黑产 SPG Schema 模型 [RiskMining.schema](./schema/RiskMining.schema)。

```bash
knext schema commit
```

提交风险用户、风险 APP 的分类概念。参见黑产分类概念规则 [concept.rule](./schema/concept.rule)。

```bash
knext schema reg_concept_rule --file ./schema/concept.rule
```

### Step 5：知识构建

提交知识构建任务导入数据。

```bash
cd builder && python indexer.py && cd ..
```

### Step 6：执行图谱规则推理任务

SPG 支持 ISO GQL 语法，可用如下命令行执行查询任务。

```bash
knext reasoner execute --dsl "${ql}"
```

#### 场景 1：语义属性对比文本属性

![KAG RiskMining Data Demo](/_static/images/examples/riskmining/kag-riskmining-data-demo.png)

电话号码：标准属性 vs 文本属性。

编辑 ``dsl_task.txt``，输入如下内容：

```cypher
MATCH
    (phone:STD.ChinaMobile)<-[:hasPhone]-(u:RiskMining.Person)
RETURN
    u.id, phone.id
```

执行脚本：

```bash
knext reasoner execute --file dsl_task.txt
```

#### 场景 2：实体动态多类型

**注意**：本节定义的分类规则 [concept.rule](./schema/concept.rule) 已经在前面的“Step 4：知识建模”章节里通过命令 ``knext schema reg_concept_rule`` 提交。

以下规则的详细内容也可以在黑产分类概念规则 [concept.rule](./schema/concept.rule) 中查看。

**赌博 App 的分类**

```text
Define (s:RiskMining.App)-[p:belongTo]->(o:`RiskMining.TaxOfRiskApp`/`赌博应用`) {
    Structure {
        (s)
    }
    Constraint {
        R1("风险标记为赌博"): s.riskMark like "%赌博%"
    }
}
```

王五为赌博应用开发者，李四为赌博应用老板，两个用户实体对应了不同的概念类型。

**赌博开发者认定规则**

**规则**：用户存在大于 5 台设备，且这些设备中安装了相同的 App，则存在开发关系。

```text
Define (s:RiskMining.Person)-[p:developed]->(o:RiskMining.App) {
    Structure {
        (s)-[:hasDevice]->(d:RiskMining.Device)-[:install]->(o)
    }
    Constraint {
        deviceNum = group(s,o).count(d)
        R1("设备超过5"): deviceNum > 5
    }
}
```

```text
Define (s:RiskMining.Person)-[p:belongTo]->(o:`RiskMining.TaxOfRiskUser`/`赌博App开发者`) {
    Structure {
        (s)-[:developed]->(app:`RiskMining.TaxOfRiskApp`/`赌博应用`)
    }
    Constraint {
    }
}
```

**认定赌博 App 老板**

**规则 1**：人和 App 存在发布关系。

```text
Define (s:RiskMining.Person)-[p:release]->(o:RiskMining.App) {
    Structure {
        (s)-[:holdShare]->(c:RiskMining.Company),
        (c)-[:hasCert]->(cert:RiskMining.Cert)<-[useCert]-(o)
    }
    Constraint {
    }
}
```

**规则 2**：用户给该赌博App开发者转账，并且存在发布赌博应用行为。

```text
Define (s:RiskMining.Person)-[p:belongTo]->(o:`RiskMining.TaxOfRiskApp`/`赌博App老板`) {
    Structure {
        (s)-[:release]->(a:`RiskMining.TaxOfRiskApp`/`赌博应用`),
        (u:RiskMining.Person)-[:developed]->(a),
        (s)-[:fundTrans]->(u)
    }
    Constraint {
    }
}
```

#### 场景 3：面向业务知识和事实数据分层下的知识应用

基于 GQL 获取黑产应用对应的团伙信息。

**获取所有的赌博应用**

编辑 ``dsl_task1.txt``，输入如下内容：

```cypher
MATCH (s:`RiskMining.TaxOfRiskApp`/`赌博应用`) RETURN s.id
```

执行脚本：

```bash
knext reasoner execute --file dsl_task1.txt
```

**获取赌博 App 背后的开发者和老板**

编辑 ``dsl_task2.txt``，输入如下内容：

```cypher
MATCH
    (u:`RiskMining.TaxOfRiskUser`/`赌博App开发者`)-[:developed]->(app:`RiskMining.TaxOfRiskApp`/`赌博应用`),
    (b:`RiskMining.TaxOfRiskUser`/`赌博App老板`)-[:release]->(app)
RETURN
    u.id, b.id, app.id
```

执行脚本：

```bash
knext reasoner execute --file dsl_task2.txt
```

### Step 7：使用 KAG 实现自然语言问答

以下是 solver 目录的内容。

```text
solver
├── prompt
│   └── logic_form_plan.py
└── qa.py
```

修改 prompt，实现领域内的 NL2LF 转换。

```python
class LogicFormPlanPrompt(RetrieverLFStaticPlanningPrompt):
    default_case_zh = """"cases": [
        {
            "Action": "张*三是一个赌博App的开发者吗?",
            "answer": "Step1:查询是否张*三的分类\nAction1:get_spo(s=s1:自然人[张*三], p=p1:属于, o=o1:风险用户)\nOutput:输出o1\nAction2:get(o1)"
        }
    ],"""
```

在 ``qa.py`` 中组装 solver 代码。

```python
async def qa(self, query):
    reporter: TraceLogReporter = TraceLogReporter()
    resp = SolverPipelineABC.from_config(KAG_CONFIG.all_config["solver_pipeline"])
    answer = await resp.ainvoke(query, reporter=reporter)

    logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

    info, status = reporter.generate_report_data()
    logger.info(f"trace log info: {info.to_dict()}")
    return answer
```

执行 ``qa.py``。

```bash
python ./solver/qa.py
```

