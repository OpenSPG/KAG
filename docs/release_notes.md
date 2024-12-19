---
sidebar_position: 1
slug: /release_notes
---

# Release notes

Key features, improvements and bug fixes in the latest releases.

## Version 0.5.1 (2024-11-21)
This version focuses on addressing user feedback and introduces a series of new features and user experience optimizations.

---

### **New Features**
- **Support for Word Documents**
      
Users can now directly upload `.doc` or `.docx` files to streamline the knowledge base construction process.
      <img src="https://github.com/user-attachments/assets/86ad11d8-42ed-44f4-91ab-f9a7c6346df2" width="600" >

-  **New Project Deletion API**
    
Quickly clear and delete projects and related data through an API, compatible with the latest Neo4j image version.
- **Model Call Concurrency Setting**
    
Added the `builder.model.execute.num` parameter, with a default concurrency of 5, to improve efficiency in large-scale knowledge base construction.  
      <img src="https://github.com/user-attachments/assets/ac7653bd-bf0c-464f-839b-8385ae6fb2c2" width="600" >

- **Improved Logging**

Added a startup success marker in the logs to help users quickly verify if the service is running correctly.  
      <img src="https://github.com/user-attachments/assets/56d42e84-d6c7-4743-a50c-5bf38fc87f58" width="600" >

---

### **Fixed issues**
- **Neo4j Memory Overflow Issues**
    
Addressed memory overflow problems in Neo4j during large-scale data processing, ensuring stable operation for extensive datasets.
-  **Concurrent Neo4j Query Execution Issues**

Optimized execution strategies to resolve Graph Data Science (GDS) library conflicts or failures in high-concurrency scenarios.
- **Schema Preview Prefix Issue**

Fixed issues where extracted schema preview entities lacked necessary prefixes, ensuring consistency between extracted entities and predefined schemas.
- **Default Neo4j Password for Project Creation/Modification**
    
Automatically fills a secure default password if none is specified during project creation or modification, simplifying the configuration process.
- **Frontend Bug Fixes**
    
Resolved issues with JS dependencies relying on external addresses and embedded all frontend files into the image. Improved the knowledge base management interface for a smoother user experience.
- **Empty Node/Edge Type in Neo4j Writes**
    
Enhanced writing logic to handle empty node or edge types during knowledge graph construction, preventing errors or data loss in such scenarios.


## Version 0.5 (2024-10-25)
retrieval Augmentation Generation (RAG) technology promotes the integration of domain applications with large models. However, RAG has problems such as a large gap between vector similarity and knowledge reasoning correlation, and insensitivity to knowledge logic (such as numerical values, time relationships, expert rules, etc.), which hinder the implementation of professional knowledge services. On October 25, officially releasing the professional domain knowledge Service Framework for knowledge enhancement generation (KAG) .

---
### KAG: Knowledge Augmented Generation
KAG aims to make full use of the advantages of Knowledge Graph and vector retrieval, and bi-directionally enhance large language models and knowledge graphs through four aspects to solve RAG challenges
(1) LLM-friendly semantic knowledge management
(2) Mutual indexing between the knowledge map and the original snippet.
(3) Logical symbol-guided hybrid inference engine
(4) Knowledge alignment based on semantic reasoning
KAG is significantly better than NaiveRAG, HippoRAG and other methods in multi-hop question and answer tasks. The F1 score on hotpotQA is relatively improved by 19.6, and the F1 score on 2wiki is relatively improved by 33.5

The KAG framework includes three parts: kg-builder, kg-solver, and kag-model. This release only involves the first two parts, kag-model will be gradually open source release in the future.

#### kg-builder
implements a knowledge representation that is friendly to large-scale language models (LLM). Based on the hierarchical structure of DIKW (data, information, knowledge and wisdom), IT upgrades SPG knowledge representation ability, and is compatible with information extraction without schema constraints and professional knowledge construction with schema constraints on the same knowledge type (such as entity type and event type), it also supports the mutual index representation between the graph structure and the original text block, which supports the efficient retrieval of the reasoning question and answer stage.

#### kg-solver
uses a logical symbol-guided hybrid solving and reasoning engine that includes three types of operators: planning, reasoning, and retrieval, to transform natural language problems into a problem-solving process that combines language and symbols. In this process, each step can use different operators, such as exact match retrieval, text retrieval, numerical calculation or semantic reasoning, so as to realize the integration of four different problem solving processes: Retrieval, Knowledge Graph reasoning, language reasoning and numerical calculation.