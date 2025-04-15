type_messages = [
    {
        "role": "system",
        "content": """{
                "instruct": "你是一个图数据专家，已知有三类问题，第一类问题是路径类问题，只需要起始节点和终点节点两点确定路径后，判断路径中的节点即可找到答案;
                    第二类问题是过滤类问题，需要起始节点和终点节点两点确定路径后，找到相应的答案，然后去除掉某个选项，典型关键词：除了、除外、不包括、排除；
                    第三类问题是多跳类问题，只需要起始节点，然后加上相应的关系，找到最终的答案，典型：存在使用连续'的'连接关系。
                    按以下步骤操作，步骤1：检测问题是否包含排除词汇（例如“除了”“不包括”）→ 如果是，归类为 过滤类问题（编号2）；
                    步骤2：检测问题是否同时指定起始和终点节点，且无排除条件(典型:存在“且”、存在“谁”、“是谁”) → 如果是，归类为 路径类问题（编号1）。
                    步骤3：检测问题是否仅有起始节点，并包含多级关系描述（例如“的...的...”） → 如果是，归类为 多跳类问题（编号3）。
                    请你确定给出的问题属于三类问题的哪一类问题，根据输入问题严格遵循规则，直接返回最终分类编号（仅限'1'、'2'、'3'）"
                }
                "example": [{
                        "query": "《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？",
                        "response": "1"
                    },{
                        "query": "《春兰花开》作者的姐姐中，谁是刘梦溪的妻子？",
                        "response": "1"
                    },{
                        "query": "谁是黄迪扬代表作品中的主要演员, 且有合作伙伴黄秋生？",
                        "response": "1"
                    },{
                        "query": "担任了金太郎的代表作品的主演的同时又是《少年们》的主要演员的人是谁？",
                        "response": "1"
                    },{
                        "query": "谁既是吴莉婕搭档的搭档，还是李乐祺的父亲？",
                        "response": "1"
                    },{
                        "query": "《山海惊奇》的作者有什么代表作品, 且出版社是中国致公出版社？"
                        "response": "1"
                    },{
                        "query": "是宜宁翁主的侄子的孙子的同时又是李芳远的曾孙的人是谁？"
                        "response": "1"
                    },{
                        "query": "谁是郑伟铭的毕业院校的知名校友，还是钟少珍的学生？",
                        "response": "1"
                    },{
                        "query": "高珊的代表作品的一位主要配音演员的的搭档除了许文广, 请问他的搭档还有谁？",
                        "response": "2"
                    },{
                        "query": "刘梦娜的毕业院校，它的哪位知名校友的搭档是安?",
                        "response": "1"
                    },{
                        "query": "《Godzilla》的歌曲原唱的某一个好友的音乐作品除了《Still Love》, 请问它的音乐作品还有哪些？",
                        "response": "2"
                    },{
                        "query": "请问《零号嫌疑犯》的主要演员参演的另一部作品中，哈利·基纳是该作品的主要角色之一，请问另外的主要角色是哪些人？"
                        "response": "2"
                    },{
                        "query": "《大国手之秦淮风月》的主要演员的搭档与李元伯有过合作，请问他还有哪些其他搭档？",
                        "response": "2"
                    },{
                        "query": "泳娜的丈夫参演了某部以姚嘉妮作为主要演员的电影，请问该电影的其他主要演员还有谁？",
                        "response": "2"
                    },{
                        "query": "赵超的毕业院校，它的知名人物的儿子有哪些?",
                        "response": "3"
                    },{
                        "query": "在爱里等你的歌曲原唱中，它老师合作过的搭档有哪些？",
                        "response": "3"
                    },{
                        "query": "如梦令这首歌的歌曲，它的原唱的前男友有哪些代表作品？",
                        "response": "3"
                    }]}"""
    }
]

path_messages = [
    {
        "role": "system",
        "content": """{
                   "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句，请分析清楚问题的起点和终点，导入到cypher语句中",
                    "example":[{
                        "query":"《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '利箭纵横' AND endNode.name =~ '陈道明' RETURN p"
                    },{
                        "query":"《春兰花开》作者的姐姐中，谁是刘梦溪的妻子？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '春兰花开' AND endNode.name =~ '刘梦溪' RETURN p"
                    },{
                        "query":"《山海惊奇》的作者有什么代表作品, 且出版社是中国致公出版社？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '山海惊奇' AND endNode.name =~ '中国致公出版社' RETURN p"
                    }，{
                        "query":"谁是郑伟铭的毕业院校的知名校友，还是钟少珍的学生？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '郑伟铭' AND endNode.name =~ '钟少珍' RETURN p"
                    }]}"""
    }
]

multi_hop_messages = [
    {
        "role": "system",
        "content": """{ 
            "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句,请仔细分析问题是几跳问题，需要的关系类型从如下关系中挑选：\n 
            需要注意的是除了“合作人”，一般情况下关系“合作”可以理解为“搭档”", 
            
            "example":[{ 
                "query":"赵超的毕业院校，它的知名人物的儿子有哪些?", 
                "response":"MATCH p=(startNode)-[:毕业院校]->()-[:知名人物]->()-[:儿子]->() WHERE startNode.name = '赵超' RETURN p" 
            },{ 
                "query":"在爱里等你的歌曲原唱中，它老师合作过的搭档有哪些？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:老师]->()-[:搭档]->() WHERE startNode.name = '在爱里等你' RETURN p" 
            },{ 
                "query":"如梦令这首歌的歌曲，它的原唱的前男友有哪些代表作品？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:前男友]->()-[:代表作品]->() WHERE startNode.name = '如梦令' RETURN p" 
            }，{
                "query":"泳娜的丈夫的搭档有哪些搭档?",
                "response":"MATCH p=(startNode)-[:丈夫]->()-[:搭档]->()-[:搭档]->() WHERE startNode.name = '泳娜' RETURN p" 
            }]}"""
    }
]

filter_messages = [
    {
        "role": "system",
        "content": """{ 
            "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句, 需要的关系类型从如下关系中挑选：\n
            需要注意的是除了“合作人”，一般情况下关系“合作”可以理解为“搭档”", 
            "example":[{ 
                "query":"高珊的代表作品的一位主要配音演员的的搭档除了许文广, 请问他的搭档还有谁？", 
                "response":"MATCH p=(startNode)-[:代表作品]->()-[:主要配音]->(actor)-[:搭档]->() WHERE startNode.name = '高珊' AND '许文广' IN [(actor)-[:搭档]->(endNode) | endNode.name] RETURN p" 
            },{ 
                "query":"《Godzilla》的歌曲原唱的某一个好友的音乐作品除了《Still Love》, 请问它的音乐作品还有哪些？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:好友]->(actor)-[:音乐作品]->() WHERE startNode.name = 'Godzilla' AND 'Still Love' IN [(actor)-[:音乐作品]->(endNode) | endNode.name] RETURN p" 
            },{ 
                "query":"《酬韦相公见寄》的作者的某一个好友的好友张蠙除外, 请问他的好友还有谁?", 
                "response":"MATCH p=(startNode)-[:作者]->()-[:好友]->(actor)-[:好友]->() WHERE startNode.name = '酬韦相公见寄' AND '张蠙' IN [(actor)-[:好友]->(endNode) | endNode.name] RETURN p" 
            },{
                "query":"《感化院》中某位主要演员的搭档和杰克·汤普森有合作过，那么这位搭档的其他搭档还有哪些人？", 
                "response":"MATCH p=(startNode)-[:主要演员]->()-[:搭档]->(actor)-[:搭档]->() WHERE startNode.name = '感化院' AND '杰克·汤普森' IN [(actor)-[:搭档]->(endNode) | endNode.name] RETURN p" 
            }]}"""
    }
]

