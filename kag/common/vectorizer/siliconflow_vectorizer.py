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
import logging

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
    
    def base64_to_float_array(self, base64_string) -> EmbeddingVector:
        """
        Converts a base64 encoded string into a list of floating-point numbers.

        This method takes a base64 encoded string as input, decodes it into raw bytes,
        and then interprets these bytes as a sequence of 4-byte floating-point numbers
        in little-endian format. The resulting list of floats is returned.

        :param base64_string: The base64 encoded string to be decoded.
        :type base64_string: str
        :return: A list of floating-point numbers represented by the decoded bytes.
        :rtype: EmbeddingVector
        """
        decoded_bytes = base64.b64decode(base64_string)
        float_array = []
        for i in range(0, len(decoded_bytes), 4):
            bytes_chunk = decoded_bytes[i:i+4]
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
        
        truncated_texts = []
        for text in texts:
            truncated_texts.append(text[0:512])
        
        url = "https://api.siliconflow.cn/v1/embeddings"

        payload = {
            "model": self.model,
            "input": truncated_texts,
            "encoding_format": "base64"
        }
        headers = {"content-type": "application/json", "authorization": 'Bearer ' + self.api_key}

        try:
            response = requests.post(url, json=payload, headers=headers)
            json_obj = json.loads(response.text)
            
            embeddings = []
            for item in json_obj['data']:
                emb_encoded = item['embedding']
                emb_arr = self.base64_to_float_array(base64_string=emb_encoded)
                embeddings.append(emb_arr)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(e)
        return embeddings
