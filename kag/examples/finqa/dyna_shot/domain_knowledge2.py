"""
符号错误：
47,98,152,222,290,310,655
"""


"""
47: percentage decrease，回答为负数，应该修改为正数
56: 召回错误，选择了错误的数据。
64: percentage of the decrease, 回答为负数。
66: 召回错误，intangible assets没有参考表中的数据，而是自己计算。
70: math投票错误。不应该错的题。
98: percentage decrease，答案给出的是负数。回答为正数。
100: 召回数据不完整，怀疑数据写入失败导致的。返回了no
108: 第一次召回数据为空，第二次改写了问题，召回了正确的数据，但是没有math，第三次添加了must use math operator，返回了no

130: 初始价格为100，召回数据少了一段：the graph assumes $ 100 originally invested on september 18 , 2008。错误数据取了december 31 2008的102.53，理解不精确。
261: 猜对的，因为修改了精度。
658: 问题问September 18, 2008，召回数据少了关键的一段。

178: 无召回，猜对了。有召回，求平均值是错误的，问题要求求总值。
187: 没有使用math算子进行计算，小数点后几位错误。
238: 第一次召回无数据，进行了问题改写，改写后无math算子结果错误
265: answer和exe_ans不匹配，exe_ans是对的。错题中主要是total_size获取错误。
281: total trading assets包括
285: python code为空，抛异常导致错误，应该重试。
317: 没有使用math，召回数据太多，反思两次以后也没有使用math
324: 召回了大量数据(排查best chunk is None，为什么召回了大量数据），同样的数据重复多次（可能没去重），没有使用math，两次反思都没有使用
329: 看起来是没有召回到关键字符串。排查一下是不是因为召回的问题。as of december 31 , 2008 , $ 6.2 billion of authorized repurchase capacity remained under the current stock repurchase program .
339: 问题没有给出年份，答案取了13和14年，错误答案选了14和15年。问题：what was the percent of the change in the volatility factor
341: 答案错误，没有进行单位换算。
369: total return的计算，不应该包含本金。计算公式问题
380: 可能是召回问题，没有召回关键行
414: 无召回，修改问题后还是无召回。怀疑是构建问题。
602: 答案不对，问题有in millions，正确答案按照in millions回答
686: 召回错误，表格中有个数据，文本中有个数据，两个数据都是cash flows provided by operating activities for all operations。文本中的数据之间给出了最终答案：excluding the $ 250 million impact of additional accounts receivable from the change in accounting discussed above , cash flows provided by operations were $ 765.2 million in 2010
706: 题目错误。exe_ans和answer不一致。
708: 错题召回数据不对，没有召回关键数据：rental expense was $ 54 million , $ 58 million and $ 54 million in 2002 , 2001 and 2000 , respectively .
771: math投票，index out of range，加个异常保护
826: 没召回表格数据，排查是不是构建问题
834: math投票错误，子问题已经取了正确的数值，math还是投错了
887: 召回不到chunk。或者召回的chunk有大量重复。
891: 漏掉了remain amount，召回数据不完整
910: 表格数据有两列相同，数值不同，取值问题
911: during 2013，取2012统计值和2013统计值
916: 猜对的。无召回，无math。可以排查一下，问题不难
940: 召回问题，召回数据不对。大模型选择的不好
961: 召回错误
974: 无召回，但是另外一个任务成功了。

"""


"""
5: 财年从7月开始。
12: the total noncancelable future lease commitments，理解不对。operating leases数据就行，不需要加capital leases
17: 题目错误
18: total召回取数不正确。
28: 应该是题目错误，问题2003到2005，数据中给的是在2003前是4.7，也被答案拿来用了。
29: 分子的取值不对。
34: 错题
35: 需要排查，召回大量数据，也没有用math
51: 错题
53: 错误，exe_ans错，answer对的
59: 错题
68: 单位换算问题，我们回答的是m
75：错题，exe_ans错，answer对的
79: 题目错误，同样的问法到底是用除法还是减法？理解错误，公式错误。the five year total return xxx was how much greater than，直接用除法
80: 题目错误
84: 错题
87: 召回数据不完整。uk和关键语言分布在两个chunk中。
94: 题目错误，数字抄错
95: 持股数计算太难，备注信息关注也没有对应的理解
103: 两次都不对，不看
109: 题目错误，2003 to 2003
114: 错的一致
118: 对high的理解不对，by how much，正确是计算百分比，但是我们这里计算的是减法
120: 备注信息在召回中没注意。2没有使用math算子
122: exe_ans错误
124: 召回为空，重写后年化收益计算公式不对，或者有召回，没有使用math。
129: 答案错误，in thousands，答案不是
144: 题目错误
150: 没有使用math
152: 正负号问题，是否可以在eval中修复?
157：错题
160: 召回为空，改写问题后，没有用math
170: 错题
174: 错题，单位错误
183: 错题
185: 错题
186: 错题
190: 错误，单位错误 
203: 难以做对，woburn property有两个值 
204: 召回很多重复内容，需要排查
210: 召回大量重复内容
217: 需要金融知识，计算数据需要减掉 impairment adjustment 
222: 正负号问题
231: 题目错误
234: 错题
252: 金融知识，total cash obligations和total
260: 错题
263: 召回不到数据，改写过，需要排查
270: 错的一致，召回数值不对
278: 错的一致，召回数据不对
283: 取数错误，2016 to 2018，要取2016开始的数据，而不是2016年底的数据
290： 正负号问题
298: 错题，exe_ans错误
310：正负号问题
313：理解不了，应该是错题
316: 年化收益计算公式不对, TODO
328: 问题没有说明答案的单位，我们返回1.0单位是百万，exe_ans单位是美元
348: 错题 
356: 错题
381: 错题
384: 错题，exe_ans错误
389: 错题，exe_ans错误
398: 计算公式不对。13% higher then 2016，如何计算2016？
399: 错的一致，错题 
402: 错的一致
432: 错的一致
441: 错题，不可能做对
442: 错题，题目中年份不对
459: 题目不明确，net interest income多个值，取值不对
461: 没有使用math，理解问题，排查
503: by how much计算百分比，错题计算的是差值。题目from 2014 to 2014应该是年内。
507: tax expense，金融理解。使用provision for income taxes * effective tax rate 
508: 金融知识,错的一致
528: 错题，错的一致
531: 错题
540: 符号问题
570: 召回了大量数据，TODO 排查一下，数据在表格头部里面，理解困难
573: 错的一致，分母召回错误。可能拆子问题更好
590: 年份问题，数据中有2003 compared to 2002 ，也有2004 compared to 2003，应该取2003的数据
601: 错题 
609: 召回为空，改写后答案为no，或者没有使用math，可以排查一下
615: 错题
627: 错题
636: 数据中给的是年底，问题问题的是2010到2012，可以通过领域知识，或者子问题尝试 
641: 错题
642: 错题
652：错题
655: 正负号
666: 错题
670: 应该做对，召回了大量重复数据，排查一下，TODO，in 2010，看2010到2011点数据就行
672: 金融知识
687: math错误，应该把goodwill也加进去
690: from 2010 to 2011，到底应该是到2011年初还是年底？TODO 排查一下，看看example
713: 错题
729: 错题，单位错误
730: what was the 2005 tax expense?有类似问题。要乘以effective tax rate
745: 没有做单位换算
750: exe_ans错误，answer是yes，可以在eval中修复
762: 问题不明确，问题和答案不匹配
768: 不应该错，排查一下。TODO




"""