# KAG
The recently developed retrieval-augmented generation (RAG) technology enables the efficient construction of domain-specific applications. However, it also faces limitations such as the ambiguity of embedding vector similarity, unclear knowledge boundaries, and insensitivity to logic rules (such as numbers, time, expert rules), etc., which hinders the effectiveness of professional knowledge services. 

We Introduce professional domain knowledge service framework: **Knowledge Augmented Generation (KAG)** to improve generation and reasoning performance by bidirectionally enhancing large language model(LLM)s and knowledge graph(KG)s, including five key enhancements: we use 1) LLMfriendly knowledge semantic representation, 2) Mutual-indexing between knowledge graph and original chunks, and 3) Knowledge alignment based on semantic reasoning to improve the completeness and accuracy of the acquired knowledge. Meanwhile, we use 4) Logical-form-guided hybrid reasoning and solving and 3) to improve the logical rigor and explainability of question answering(Q&A). And finally, we use 5) Model for KAG to reduce the cost of knowledge acquisition and Q&A. 

We compared KAG with existing RAG methods in multi-hop Q&A. The results show that KAG performs significantly better than the state-of-the-art methods, with a relative improvement from 19.6% to 33.5% in F1. We apply KAG to two professional knowledge Q&A tasks of Ant Group, including E-Goverment Q&A and E-Health Q&A, and has achieved significant improvement in professionalism compared with RAG method. 

**The open-source release of KAG is on its way. We kindly invite you to subscribe and look forward to your support and feedback.**


# Cite

If you use this software, please cite it as below:
* [KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation](https://arxiv.org/abs/2409.13731)
* KGFabric: A Scalable Knowledge Graph Warehouse for Enterprise Data Interconnection

```bibtex
@article{liang2024kag,
  title={KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation},
  author={Liang, Lei and Sun, Mengshu and Gui, Zhengke and Zhu, Zhongshu and Jiang, Zhouyu and Zhong, Ling and Qu, Yuan and Zhao, Peilong and Bo, Zhongpu and Yang, Jin and others},
  journal={arXiv preprint arXiv:2409.13731},
  year={2024}
}

@article{yikgfabric,
  title={KGFabric: A Scalable Knowledge Graph Warehouse for Enterprise Data Interconnection},
  author={Yi, Peng and Liang, Lei and Da Zhang, Yong Chen and Zhu, Jinye and Liu, Xiangyu and Tang, Kun and Chen, Jialin and Lin, Hao and Qiu, Leijie and Zhou, Jun}
}
```

# License

[Apache License 2.0](LICENSE)
