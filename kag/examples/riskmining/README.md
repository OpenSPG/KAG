# KAG Example: Risk Mining Knowledge Graph (RiskMining)

[English](./README.md) |
[简体中文](./README_cn.md)

## Overview

**Keywords**: semantic properties, dynamic multi-classification of entities, knowledge application in the context of hierarchical business knowledge and factual data.

![KAG RiskMining Diagram](/_static/images/examples/riskmining/kag-riskmining-diag.png)

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/riskmining
```

### Step 2: Configure models

Update the generative model configurations ``openie_llm`` and ``chat_llm`` and the representational model configuration ``vectorize_model`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``s. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

### Step 3: Project initialization

Initiate the project with the following command.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4: Create knowledge schema

The schema file [RiskMining.schema](./schema/RiskMining.schema) has been created and you can execute the following command to submit it:

```bash
knext schema commit
```

Submit the classification rules of RiskUser and RiskApp in [concept.rule](./schema/concept.rule):

```bash
knext schema reg_concept_rule --file ./schema/concept.rule
```

### Step 5: Knowledge graph construction

Submit the knowledge importing tasks.

```bash
cd builder && python indexer.py && cd ..
```

### Step 6: Executing query tasks for knowledge graph

OpenSPG supports the ISO GQL syntax. You can use the following command-line to execute a query task:

```bash
knext reasoner execute --dsl "${ql}"
```

#### Scenario 1: Semantic attributes vs text attributes

![KAG RiskMining Data Demo](/_static/images/examples/riskmining/kag-riskmining-data-demo.png)

MobilePhone: "standard attribute" vs "text attribute".

Save the following content as file ``dsl_task.txt``.

```cypher
MATCH
    (phone:STD.ChinaMobile)<-[:hasPhone]-(u:RiskMining.Person)
RETURN
    u.id, phone.id
```

Execute the query script.

```bash
knext reasoner execute --file dsl_task.txt
```

#### Scenario 2: Dynamic multi-type entities

**Note**: The classification rules defined in this section have been submitted in the previous "4. Create knowledge schema" section using the command ``knext schema reg_concept_rule``.

The detailed content of the following rules can also be found in the file [concept.rule](./schema/concept.rule).

**Taxonomy of gambling apps**

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

Wang Wu is a gambling app developer, and Li Si is the owner of a gambling app. These two user entities correspond to different concept types.

**Gambling Developer's Identification Rule**

**Rule**: If a user has more than 5 devices, and these devices have the same app installed, then there exists a development relation.

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

**Identifying the owner of a gambling app**

**Rule 1**: There exists a publishing relation between a person and the app.

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

**Rule 2**: The user transfers money to the gambling app developer, and there exists a relation of publishing gambling app.

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

#### Scenario 3: Knowledge Application in the Context of hierarchical Business Knowledge and Factual Data

We can use GQL to query the criminal group information corresponding to black market applications.

**Retrieve all gambling applications**

Save the following content as file ``dsl_task1.txt``.

```cypher
MATCH (s:`RiskMining.TaxOfRiskApp`/`赌博应用`) RETURN s.id
```

Execute the query script.

```bash
knext reasoner execute --file dsl_task1.txt
```

**Retrieve the developers and owners of the gambling apps**

Save the following content as file ``dsl_task2.txt``.

```cypher
MATCH
    (u:`RiskMining.TaxOfRiskUser`/`赌博App开发者`)-[:developed]->(app:`RiskMining.TaxOfRiskApp`/`赌博应用`),
    (b:`RiskMining.TaxOfRiskUser`/`赌博App老板`)-[:release]->(app)
RETURN
    u.id, b.id, app.id
```

Execute the query script.

```bash
knext reasoner execute --file dsl_task2.txt
```

### Step 7: Use KAG to implement natural language QA

Here is the content of the ``solver`` directory.

```text
solver
├── prompt
│   └── logic_form_plan.py
└── qa.py
```

Modify the prompt to implement NL2LF conversion in the RiskMining domain.

```python
class LogicFormPlanPrompt(PromptOp):
    default_case_zh = """"cases": [
        {
            "Action": "张*三是一个赌博App的开发者吗?",
            "answer": "Step1:查询是否张*三的分类\nAction1:get_spo(s=s1:自然人[张*三], p=p1:属于, o=o1:风险用户)\nOutput:输出o1\nAction2:get(o1)"
        }
    ],"""
```

Assemble the solver code in ``qa.py``.

```python
def qa(self, query):
    resp = SolverPipeline()
    answer, trace_log = resp.run(query)

    logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
    return answer, trace_log
```

Execute ``qa.py``.

```bash
python ./solver/qa.py
```

