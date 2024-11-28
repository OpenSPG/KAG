# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

from typing import Any, Union, Iterable, Dict
from openai import OpenAI
from kag.common.vectorizer.vectorizer import Vectorizer
import requests
import json
import base64
import struct

EmbeddingVector = Iterable[float]

class SiliconFlowVectorizer(Vectorizer):
    """
    Invoke SiliconFlow API services to turn texts into embedding vectors.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model","netease-youdao/bce-embedding-base_v1")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        if not self.api_key:
            raise ValueError("SiliconFlow API key is not set")

    @classmethod
    def _from_config(cls, config: Dict[str, Any]) -> Vectorizer:
        """
        Create vectorizer from `config`.

        :param config: vectorizer config
        :type config: Dict[str, Any]
        :return: vectorizer instance
        :rtype: Vectorizer
        """
        vectorizer = cls(config)
        return vectorizer
    
    def base64_to_float_array(self, base64_string):
        # 解码base64字符串
        decoded_bytes = base64.b64decode(base64_string)
        
        # 将字节转换为浮点数，这里假设每个浮点数是4字节（即float类型）
        # '<' 表示小端格式，'f' 表示单精度浮点数
        float_array = []
        for i in range(0, len(decoded_bytes), 4):
            # 提取4个字节
            bytes_chunk = decoded_bytes[i:i+4]
            # 解码为浮点数
            float_num = struct.unpack('<f', bytes_chunk)[0]
            float_array.append(float_num)
        
        return float_array

    def vectorize(self, texts: Union[str, Iterable[str]]) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        
        if type(texts) is str:
            texts = [texts]
        
        embeddings = []
        for text in texts:
            url = "https://api.siliconflow.cn/v1/embeddings"

            payload = {
                "model": self.model,
                "input": text,
                "encoding_format": "base64"
            }
            headers = {"content-type": "application/json", "authorization": 'Bearer ' + self.api_key}

            response = requests.post(url, json=payload, headers=headers)
            json_obj = json.loads(response.text)
            emb_encoded = json_obj['data'][0]['embedding']
            emb_arr = self.base64_to_float_array(base64_string=emb_encoded)
            
            embeddings.append(emb_arr)
        
        return embeddings

if __name__ == '__main__':
    inst = SiliconFlowVectorizer(config={"api_key": "sk-ducerqngypudxuevovkmvsbatstjyikvbjdpylfsvkfqcgox", "base_url": "https://api.siliconflow.cn/v1"})
    print(inst.vectorize(texts='hello'))