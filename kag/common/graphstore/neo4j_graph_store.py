# -*- coding: utf-8 -*-
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
import logging
import re
import threading
import time
from abc import ABCMeta

import schedule
from neo4j import GraphDatabase

from kag.common.graphstore.graph_store import GraphStore
from kag.common.utils import escape_single_quotes
from knext.schema.model.base import IndexTypeEnum

logger = logging.getLogger(__name__)


class SingletonMeta(ABCMeta):
    """
    Thread-safe Singleton metaclass
    """

    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        uri = kwargs.get("uri")
        user = kwargs.get("user")
        password = kwargs.get("password")
        database = kwargs.get("database", "neo4j")
        key = (cls, uri, user, password, database)

        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = super().__call__(*args, **kwargs)
        return cls._instances[key]


class Neo4jClient(GraphStore, metaclass=SingletonMeta):
    def __init__(
        self,
        uri,
        user,
        password,
        database="neo4j",
        init_type="write",
        interval_minutes=10,
    ):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"init Neo4jClient uri: {uri} database: {database}")
        self._database = database
        self._lucene_special_chars = '\\+-!():^[]"{}~*?|&/'
        self._lucene_pattern = self._get_lucene_pattern()
        self._simple_ident = "[A-Za-z_][A-Za-z0-9_]*"
        self._simple_ident_pattern = re.compile(self._simple_ident)
        self._vec_meta = dict()
        self._vec_meta_ts = 0.0
        self._vec_meta_timeout = 60.0
        self._vectorizer = None
        self._allGraph = "allGraph_0"
        if init_type == "write":
            self._labels = self._create_unique_constraint()
            self._create_all_graph(self._allGraph)
        self.schedule_constraint(interval_minutes)
        # self.create_text_index(["Chunk"], ["content"])
        self.refresh_vector_index_meta(force=True)

    def close(self):
        self._driver.close()

    def schedule_constraint(self, interval_minutes):
        def job():
            try:
                self._labels = self._create_unique_constraint()
                self._update_pagerank_graph()
            except Exception as e:
                import traceback

                logger.error(
                    f"Error run scheduled job, info: {e},\ntraceback:\n {traceback.format_exc()}"
                )

        def run_scheduled_tasks():
            while True:
                schedule.run_pending()
                time.sleep(1)

        if interval_minutes > 0:
            schedule.every(interval_minutes).minutes.do(job)
            scheduler_thread = threading.Thread(target=run_scheduled_tasks, daemon=True)
            scheduler_thread.start()

    def get_all_entity_labels(self):
        with self._driver.session(database=self._database) as session:
            result = session.run("CALL db.labels()")
            labels = [record[0] for record in result]
            return labels

    def run_script(self, script):
        with self._driver.session(database=self._database) as session:
            return list(session.run(script))

    def _create_unique_constraint(self):
        with self._driver.session(database=self._database) as session:
            result = session.run("CALL db.labels()")
            labels = [record[0] for record in result if record[0] != "Entity"]
            for label in labels:
                self._create_unique_index_constraint(self, label, session)
            return labels

    @staticmethod
    def _create_unique_index_constraint(self, label, session):
        constraint_name = f"uniqueness_{label}_id"
        create_constraint_query = f"CREATE CONSTRAINT {self._escape_neo4j(constraint_name)} IF NOT EXISTS FOR (n:{self._escape_neo4j(label)}) REQUIRE n.id IS UNIQUE"

        try:
            result = session.run(create_constraint_query)
            result.consume()
            logger.debug(
                f"Unique constraint created for constraint_name: {constraint_name}"
            )
        except Exception as e:
            logger.debug(f"warn creating constraint for {constraint_name}: {e}")
            self._create_index_constraint(self, label, session)

    @staticmethod
    def _create_index_constraint(self, label, session):
        index_name = f"index_{label}_id"
        create_constraint_query = f"CREATE INDEX {self._escape_neo4j(index_name)} IF NOT EXISTS FOR (n:{self._escape_neo4j(label)}) ON (n.id)"
        try:
            result = session.run(create_constraint_query)
            result.consume()
            logger.debug(f"index constraint created for constraint_name: {index_name}")
        except Exception as e:
            logger.warn(f"warn creating index constraint for {index_name}: {e}")

    def _update_pagerank_graph(self):
        all_graph_0 = "allGraph_0"
        all_graph_1 = "allGraph_1"

        if self._allGraph == all_graph_0:
            all_graph = all_graph_1
        else:
            all_graph = all_graph_0

        logger.debug(f"update pagerank graph for {all_graph}")
        self._create_all_graph(all_graph)

        logger.debug(f"drop old pagerank graph for {self._allGraph}")
        self._drop_all_graph(self._allGraph)
        self._allGraph = all_graph

    def create_pagerank_graph(self):
        self._drop_all_graph(self._allGraph)
        self._create_all_graph(self._allGraph)

    def initialize_schema(self, schema_types):
        for spg_type in schema_types:
            label = spg_type
            properties = schema_types[spg_type].properties
            if properties:
                for property_key in properties:
                    if property_key == "name":
                        self.create_vector_index(label, property_key)
                    index_type = properties[property_key].index_type
                    if index_type:
                        if index_type == IndexTypeEnum.Text:
                            pass
                        elif index_type in (
                            IndexTypeEnum.Vector,
                            IndexTypeEnum.TextAndVector,
                        ):
                            self.create_vector_index(label, property_key)
                        elif index_type in (
                            IndexTypeEnum.SparseVector,
                            IndexTypeEnum.TextAndSparseVector,
                        ):
                            logger.info(
                                f"Neo4j doesn't support sparse vector index: {index_type}"
                            )
                        else:
                            logger.info(f"Undefined IndexTypeEnum {index_type}")
        labels, property_keys = self._collect_text_index_info(schema_types)
        self.create_text_index(labels, property_keys)
        self.create_vector_index("Entity", "name")
        self.create_vector_index("Entity", "desc")
        self.refresh_vector_index_meta(force=True)

    def _collect_text_index_info(self, schema_types):
        labels = {}
        property_keys = {}
        for spg_type in schema_types:
            label = spg_type
            properties = schema_types[spg_type].properties
            if properties:
                label_property_keys = {}
                for property_key in properties:
                    index_type = properties[property_key].index_type
                    if (
                        property_key == "name"
                        or index_type
                        and index_type
                        in (
                            IndexTypeEnum.Text,
                            IndexTypeEnum.TextAndVector,
                            IndexTypeEnum.TextAndSparseVector,
                        )
                    ):
                        label_property_keys[property_key] = True
                if label_property_keys:
                    labels[label] = True
                    property_keys.update(label_property_keys)
        return tuple(labels.keys()), tuple(property_keys.keys())

    def upsert_node(self, label, properties, id_key="id", extra_labels=("Entity",)):
        self._preprocess_node_properties(label, properties, extra_labels)
        with self._driver.session(database=self._database) as session:
            if label not in self._labels:
                self._create_unique_index_constraint(self, label, session)
            try:
                return session.execute_write(
                    self._upsert_node, self, label, id_key, properties, extra_labels
                )
            except Exception as e:
                logger.error(
                    f"upsert_node label:{label} properties:{properties} Exception: {e}"
                )
                return None

    @staticmethod
    def _upsert_node(tx, self, label, id_key, properties, extra_labels):
        if not label:
            logger.warning("label cannot be None or empty strings")
            return None
        query = (
            f"MERGE (n:{self._escape_neo4j(label)} {{{self._escape_neo4j(id_key)}: $properties.{self._escape_neo4j(id_key)}}}) "
            "SET n += $properties "
        )
        if extra_labels:
            query += f", n:{':'.join(self._escape_neo4j(extra_label) for extra_label in extra_labels)} "
        query += "RETURN n"
        result = tx.run(query, properties=properties)
        return result.single()[0]

    def upsert_nodes(
        self, label, properties_list, id_key="id", extra_labels=("Entity",)
    ):
        self._preprocess_node_properties_list(label, properties_list, extra_labels)
        with self._driver.session(database=self._database) as session:
            if label not in self._labels:
                self._create_unique_index_constraint(self, label, session)
            try:
                return session.execute_write(
                    self._upsert_nodes,
                    self,
                    label,
                    properties_list,
                    id_key,
                    extra_labels,
                )
            except Exception as e:
                logger.error(
                    f"upsert_nodes label:{label} properties:{properties_list} Exception: {e}"
                )
                return None

    @staticmethod
    def _upsert_nodes(tx, self, label, properties_list, id_key, extra_labels):
        if not label:
            logger.warning("label cannot be None or empty strings")
            return None
        query = (
            "UNWIND $properties_list AS properties "
            f"MERGE (n:{self._escape_neo4j(label)} {{{self._escape_neo4j(id_key)}: properties.{self._escape_neo4j(id_key)}}}) "
            "SET n += properties "
        )
        if extra_labels:
            query += f", n:{':'.join(self._escape_neo4j(extra_label) for extra_label in extra_labels)} "
        query += "RETURN n"
        result = tx.run(query, properties_list=properties_list)
        return [record["n"] for record in result]

    def _get_embedding_vector(self, properties, vector_field):
        for property_key, property_value in properties.items():
            field_name = self._create_vector_field_name(property_key)
            if field_name != vector_field:
                continue
            if not property_value:
                return None
            if not isinstance(property_value, str):
                message = f"property {property_key!r} must be string to generate embedding vector"
                raise RuntimeError(message)
            try:
                vector = self.vectorizer.vectorize(property_value)
                return vector
            except Exception as e:
                logger.info(
                    f"An error occurred while vectorizing property {property_key!r}: {e}"
                )
            return None
        return None

    def _preprocess_node_properties(self, label, properties, extra_labels):
        if self._vectorizer is None:
            return
        self.refresh_vector_index_meta()
        vec_meta = self._vec_meta
        labels = [label]
        if extra_labels:
            labels.extend(extra_labels)
        for label in labels:
            if label not in vec_meta:
                continue
            for vector_field in vec_meta[label]:
                if vector_field in properties:
                    continue
                embedding_vector = self._get_embedding_vector(properties, vector_field)
                if embedding_vector is not None:
                    properties[vector_field] = embedding_vector

    def _preprocess_node_properties_list(self, label, properties_list, extra_labels):
        for properties in properties_list:
            self._preprocess_node_properties(label, properties, extra_labels)

    def batch_preprocess_node_properties(self, node_batch, extra_labels=("Entity",)):
        if self._vectorizer is None:
            return

        class EmbeddingVectorPlaceholder(object):
            def __init__(
                self, number, properties, vector_field, property_key, property_value
            ):
                self._number = number
                self._properties = properties
                self._vector_field = vector_field
                self._property_key = property_key
                self._property_value = property_value
                self._embedding_vector = None

            def replace(self):
                if self._embedding_vector is not None:
                    self._properties[self._vector_field] = self._embedding_vector

            def __repr__(self):
                return repr(self._number)

        class EmbeddingVectorManager(object):
            def __init__(self):
                self._placeholders = []

            def get_placeholder(self, graph_store, properties, vector_field):
                for property_key, property_value in properties.items():
                    field_name = graph_store._create_vector_field_name(property_key)
                    if field_name != vector_field:
                        continue
                    if not property_value:
                        return None
                    if not isinstance(property_value, str):
                        message = f"property {property_key!r} must be string to generate embedding vector"
                        raise RuntimeError(message)
                    num = len(self._placeholders)
                    placeholder = EmbeddingVectorPlaceholder(
                        num, properties, vector_field, property_key, property_value
                    )
                    self._placeholders.append(placeholder)
                    return placeholder
                return None

            def _get_text_batch(self):
                text_batch = dict()
                for placeholder in self._placeholders:
                    property_value = placeholder._property_value
                    if property_value not in text_batch:
                        text_batch[property_value] = list()
                    text_batch[property_value].append(placeholder)
                return text_batch

            def _generate_vectors(self, vectorizer, text_batch):
                texts = list(text_batch)
                vectors = vectorizer.vectorize(texts)
                return vectors

            def _fill_vectors(self, vectors, text_batch):
                for vector, (_text, placeholders) in zip(vectors, text_batch.items()):
                    for placeholder in placeholders:
                        placeholder._embedding_vector = vector

            def batch_vectorize(self, vectorizer):
                text_batch = self._get_text_batch()
                vectors = self._generate_vectors(vectorizer, text_batch)
                self._fill_vectors(vectors, text_batch)

            def patch(self):
                for placeholder in self._placeholders:
                    placeholder.replace()

        manager = EmbeddingVectorManager()
        self.refresh_vector_index_meta()
        vec_meta = self._vec_meta
        for node_item in node_batch:
            label, properties = node_item
            labels = [label]
            if extra_labels:
                labels.extend(extra_labels)
            for label in labels:
                if label not in vec_meta:
                    continue
                for vector_field in vec_meta[label]:
                    if vector_field in properties:
                        continue
                    placeholder = manager.get_placeholder(
                        self, properties, vector_field
                    )
                    if placeholder is not None:
                        properties[vector_field] = placeholder
        manager.batch_vectorize(self._vectorizer)
        manager.patch()

    def get_node(self, label, id_value, id_key="id"):
        with self._driver.session(database=self._database) as session:
            return session.execute_read(self._get_node, self, label, id_key, id_value)

    @staticmethod
    def _get_node(tx, self, label, id_key, id_value):
        query = f"MATCH (n:{self._escape_neo4j(label)} {{{self._escape_neo4j(id_key)}: $id_value}}) RETURN n"
        result = tx.run(query, id_value=id_value)
        single_result = result.single()
        # print(f"single_result: {single_result}")
        if single_result is not None:
            return single_result[0]
        else:
            return None

    def delete_node(self, label, id_value, id_key="id"):
        with self._driver.session(database=self._database) as session:
            try:
                session.execute_write(self._delete_node, self, label, id_key, id_value)
            except Exception as e:
                logger.error(f"delete_node label:{label} Exception: {e}")

    @staticmethod
    def _delete_node(tx, self, label, id_key, id_value):
        query = f"MATCH (n:{self._escape_neo4j(label)} {{{self._escape_neo4j(id_key)}: $id_value}}) DETACH DELETE n"
        tx.run(query, id_value=id_value)

    def delete_nodes(self, label, id_values, id_key="id"):
        with self._driver.session(database=self._database) as session:
            session.execute_write(self._delete_nodes, self, label, id_key, id_values)

    @staticmethod
    def _delete_nodes(tx, self, label, id_key, id_values):
        query = f"UNWIND $id_values AS id_value MATCH (n:{self._escape_neo4j(label)} {{{self._escape_neo4j(id_key)}: id_value}}) DETACH DELETE n"
        tx.run(query, id_values=id_values)

    def upsert_relationship(
        self,
        start_node_label,
        start_node_id_value,
        end_node_label,
        end_node_id_value,
        rel_type,
        properties,
        upsert_nodes=True,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        rel_type = self._escape_neo4j(rel_type)
        with self._driver.session(database=self._database) as session:
            try:
                return session.execute_write(
                    self._upsert_relationship,
                    self,
                    start_node_label,
                    start_node_id_key,
                    start_node_id_value,
                    end_node_label,
                    end_node_id_key,
                    end_node_id_value,
                    rel_type,
                    properties,
                    upsert_nodes,
                )
            except Exception as e:
                logger.error(
                    f"upsert_relationship rel_type:{rel_type} properties:{properties} Exception: {e}"
                )
                return None

    @staticmethod
    def _upsert_relationship(
        tx,
        self,
        start_node_label,
        start_node_id_key,
        start_node_id_value,
        end_node_label,
        end_node_id_key,
        end_node_id_value,
        rel_type,
        properties,
        upsert_nodes,
    ):
        if not start_node_label or not end_node_label or not rel_type:
            logger.warning(
                "start_node_label, end_node_label, and rel_type cannot be None or empty strings"
            )
            return None
        if upsert_nodes:
            query = (
                f"MERGE (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: $start_node_id_value}}) "
                f"MERGE (b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: $end_node_id_value}}) "
                f"MERGE (a)-[r:{self._escape_neo4j(rel_type)}]->(b) SET r += $properties RETURN r"
            )
        else:
            query = (
                f"MATCH (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: $start_node_id_value}}), "
                f"(b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: $end_node_id_value}}) "
                f"MERGE (a)-[r:{self._escape_neo4j(rel_type)}]->(b) SET r += $properties RETURN r"
            )
        result = tx.run(
            query,
            start_node_id_value=start_node_id_value,
            end_node_id_value=end_node_id_value,
            properties=properties,
        )
        return result.single()

    def upsert_relationships(
        self,
        start_node_label,
        end_node_label,
        rel_type,
        relations,
        upsert_nodes=True,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        with self._driver.session(database=self._database) as session:
            try:
                return session.execute_write(
                    self._upsert_relationships,
                    self,
                    relations,
                    start_node_label,
                    start_node_id_key,
                    end_node_label,
                    end_node_id_key,
                    rel_type,
                    upsert_nodes,
                )
            except Exception as e:
                logger.error(
                    f"upsert_relationships rel_type:{rel_type} relations:{relations} Exception: {e}"
                )
                return None

    @staticmethod
    def _upsert_relationships(
        tx,
        self,
        relations,
        start_node_label,
        start_node_id_key,
        end_node_label,
        end_node_id_key,
        rel_type,
        upsert_nodes,
    ):
        if not start_node_label or not end_node_label or not rel_type:
            logger.warning(
                "start_node_label, end_node_label, and rel_type cannot be None or empty strings"
            )
            return None
        if upsert_nodes:
            query = (
                "UNWIND $relations AS relationship "
                f"MERGE (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: relationship.start_node_id}}) "
                f"MERGE (b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: relationship.end_node_id}}) "
                f"MERGE (a)-[r:{self._escape_neo4j(rel_type)}]->(b) SET r += relationship.properties RETURN r"
            )
        else:
            query = (
                "UNWIND $relations AS relationship "
                f"MATCH (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: relationship.start_node_id}}) "
                f"MATCH (b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: relationship.end_node_id}}) "
                f"MERGE (a)-[r:{self._escape_neo4j(rel_type)}]->(b) SET r += relationship.properties RETURN r"
            )

        result = tx.run(
            query,
            relations=relations,
            start_node_label=start_node_label,
            start_node_id_key=start_node_id_key,
            end_node_label=end_node_label,
            end_node_id_key=end_node_id_key,
            rel_type=rel_type,
        )
        return [record["r"] for record in result]

    def delete_relationship(
        self,
        start_node_label,
        start_node_id_value,
        end_node_label,
        end_node_id_value,
        rel_type,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        with self._driver.session(database=self._database) as session:
            try:
                session.execute_write(
                    self._delete_relationship,
                    self,
                    start_node_label,
                    start_node_id_key,
                    start_node_id_value,
                    end_node_label,
                    end_node_id_key,
                    end_node_id_value,
                    rel_type,
                )
            except Exception as e:
                logger.error(f"delete_relationship rel_type:{rel_type} Exception: {e}")

    @staticmethod
    def _delete_relationship(
        tx,
        self,
        start_node_label,
        start_node_id_key,
        start_node_id_value,
        end_node_label,
        end_node_id_key,
        end_node_id_value,
        rel_type,
    ):
        query = (
            f"MATCH (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: $start_node_id_value}})-[r:{self._escape_neo4j(rel_type)}]->"
            f"(b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: $end_node_id_value}}) DELETE r"
        )
        tx.run(
            query,
            start_node_id_value=start_node_id_value,
            end_node_id_value=end_node_id_value,
        )

    def delete_relationships(
        self,
        start_node_label,
        start_node_id_values,
        end_node_label,
        end_node_id_values,
        rel_type,
        start_node_id_key="id",
        end_node_id_key="id",
    ):
        with self._driver.session(database=self._database) as session:
            session.execute_write(
                self._delete_relationships,
                self,
                start_node_label,
                start_node_id_key,
                start_node_id_values,
                end_node_label,
                end_node_id_key,
                end_node_id_values,
                rel_type,
            )

    @staticmethod
    def _delete_relationships(
        tx,
        self,
        start_node_label,
        start_node_id_key,
        start_node_id_values,
        end_node_label,
        end_node_id_key,
        end_node_id_values,
        rel_type,
    ):
        query = (
            "UNWIND $start_node_id_values AS start_node_id_value "
            "UNWIND $end_node_id_values AS end_node_id_value "
            f"MATCH (a:{self._escape_neo4j(start_node_label)} {{{self._escape_neo4j(start_node_id_key)}: start_node_id_value}})-[r:{self._escape_neo4j(rel_type)}]->"
            f"(b:{self._escape_neo4j(end_node_label)} {{{self._escape_neo4j(end_node_id_key)}: end_node_id_value}}) DELETE r"
        )
        tx.run(
            query,
            start_node_id_values=start_node_id_values,
            end_node_id_values=end_node_id_values,
        )

    def _get_lucene_pattern(self):
        string = re.escape(self._lucene_special_chars)
        pattern = "([" + string + "])"
        pattern = re.compile(pattern)
        return pattern

    def _escape_lucene(self, string):
        result = self._lucene_pattern.sub(r"\\\1", string)
        return result

    def _make_lucene_query(self, string):
        string = self._escape_lucene(string)
        result = string.lower()
        return result

    def _get_utf16_codepoints(self, string):
        result = []
        for ch in string:
            data = ch.encode("utf-16-le")
            for i in range(0, len(data), 2):
                value = int.from_bytes(data[i : i + 2], "little")
                result.append(value)
        return tuple(result)

    def _escape_neo4j(self, name):
        match = self._simple_ident_pattern.fullmatch(name)
        if match is not None:
            return name
        string = "`"
        for ch in name:
            if ch == "`":
                string += "``"
            elif ch.isascii() and ch.isprintable():
                string += ch
            else:
                values = self._get_utf16_codepoints(ch)
                for value in values:
                    string += "\\u%04X" % value
        string += "`"
        return string

    def _to_snake_case(self, name):
        import re

        words = re.findall("[A-Za-z][a-z0-9]*", name)
        result = "_".join(words).lower()
        return result

    def _create_vector_index_name(self, label, property_key):
        name = f"{label}_{property_key}_vector_index"
        name = self._to_snake_case(name)
        return "_" + name

    def _create_vector_field_name(self, property_key):
        name = f"{property_key}_vector"
        name = self._to_snake_case(name)
        return "_" + name

    def create_index(self, label, property_key, index_name=None):
        with self._driver.session(database=self._database) as session:
            session.execute_write(
                self._create_index, self, label, property_key, index_name
            )

    @staticmethod
    def _create_index(tx, self, label, property_key, index_name):
        if not label or not property_key:
            return
        if index_name is None:
            query = f"CREATE INDEX IF NOT EXISTS FOR (n:{self._escape_neo4j(label)}) ON (n.{self._escape_neo4j(property_key)})"
        else:
            query = f"CREATE INDEX {self._escape_neo4j(index_name)} IF NOT EXISTS FOR (n:{self._escape_neo4j(label)}) ON (n.{self._escape_neo4j(property_key)})"
        tx.run(query)

    def create_text_index(self, labels, property_keys, index_name=None):
        if not labels or not property_keys:
            return
        if index_name is None:
            index_name = "_default_text_index"
        label_spec = "|".join(self._escape_neo4j(label) for label in labels)
        property_spec = ", ".join(
            f"n.{self._escape_neo4j(key)}" for key in property_keys
        )
        query = (
            f"CREATE FULLTEXT INDEX {self._escape_neo4j(index_name)} IF NOT EXISTS "
            f"FOR (n:{label_spec}) ON EACH [{property_spec}]"
        )

        def do_create_text_index(tx):
            tx.run(query)

        with self._driver.session(database=self._database) as session:
            session.execute_write(do_create_text_index)
        return index_name

    def create_vector_index(
        self,
        label,
        property_key,
        index_name=None,
        vector_dimensions=768,
        metric_type="cosine",
        hnsw_m=None,
        hnsw_ef_construction=None,
    ):
        if index_name is None:
            index_name = self._create_vector_index_name(label, property_key)
        if not property_key.lower().endswith("vector"):
            property_key = self._create_vector_field_name(property_key)
        with self._driver.session(database=self._database) as session:
            session.execute_write(
                self._create_vector_index,
                self,
                label,
                property_key,
                index_name,
                vector_dimensions,
                metric_type,
                hnsw_m,
                hnsw_ef_construction,
            )
        self.refresh_vector_index_meta(force=True)
        return index_name

    @staticmethod
    def _create_vector_index(
        tx,
        self,
        label,
        property_key,
        index_name,
        vector_dimensions,
        metric_type,
        hnsw_m,
        hnsw_ef_construction,
    ):
        query = (
            f"CREATE VECTOR INDEX {self._escape_neo4j(index_name)} IF NOT EXISTS FOR (n:{self._escape_neo4j(label)}) ON (n.{self._escape_neo4j(property_key)}) "
            "OPTIONS { indexConfig: {"
            "  `vector.dimensions`: $vector_dimensions,"
            "  `vector.similarity_function`: $metric_type"
        )
        if hnsw_m is not None:
            query += ",  `vector.hnsw.m`: $hnsw_m"
        if hnsw_ef_construction is not None:
            query += ",  `vector.hnsw.ef_construction`: $hnsw_ef_construction"
        query += "}}"
        tx.run(
            query,
            vector_dimensions=vector_dimensions,
            metric_type=metric_type,
            hnsw_m=hnsw_m,
            hnsw_ef_construction=hnsw_ef_construction,
        )

    def refresh_vector_index_meta(self, force=False):
        import time

        if not force and time.time() - self._vec_meta_ts < self._vec_meta_timeout:
            return

        def do_refresh_vector_index_meta(tx):
            query = "SHOW VECTOR INDEX"
            res = tx.run(query)
            data = res.data()
            meta = dict()
            for record in data:
                if record["entityType"] == "NODE":
                    (label,) = record["labelsOrTypes"]
                    (vector_field,) = record["properties"]
                    if vector_field.startswith("_") and vector_field.endswith(
                        "_vector"
                    ):
                        if label not in meta:
                            meta[label] = []
                        meta[label].append(vector_field)
            self._vec_meta = meta
            self._vec_meta_ts = time.time()

        with self._driver.session(database=self._database) as session:
            session.execute_read(do_refresh_vector_index_meta)

    def delete_index(self, index_name):
        with self._driver.session(database=self._database) as session:
            session.execute_write(self._delete_index, self, index_name)

    @staticmethod
    def _delete_index(tx, self, index_name):
        query = f"DROP INDEX {self._escape_neo4j(index_name)} IF EXISTS"
        tx.run(query)

    @property
    def vectorizer(self):
        if self._vectorizer is None:
            message = "vectorizer is not initialized"
            raise RuntimeError(message)
        return self._vectorizer

    @vectorizer.setter
    def vectorizer(self, value):
        self._vectorizer = value

    def text_search(
        self, query_string, label_constraints=None, topk=10, index_name=None
    ):
        if index_name is None:
            index_name = "_default_text_index"
        if label_constraints is None:
            pass
        elif isinstance(label_constraints, str):
            label_constraints = self._escape_neo4j(label_constraints)
        elif isinstance(label_constraints, (list, tuple)):
            label_constraints = "|".join(
                self._escape_neo4j(label_constraint)
                for label_constraint in label_constraints
            )
        else:
            message = f"invalid label_constraints: {label_constraints!r}"
            raise RuntimeError(message)
        if label_constraints is None:
            query = (
                "CALL db.index.fulltext.queryNodes($index_name, $query_string) "
                "YIELD node AS node, score "
                "RETURN node, score"
            )
        else:
            query = (
                "CALL db.index.fulltext.queryNodes($index_name, $query_string) "
                "YIELD node AS node, score "
                f"WHERE (node:{label_constraints}) "
                "RETURN node, score"
            )
        query += " LIMIT $topk"
        query_string = self._make_lucene_query(query_string)

        def do_text_search(tx):
            res = tx.run(
                query, query_string=query_string, topk=topk, index_name=index_name
            )
            data = res.data()
            return data

        with self._driver.session(database=self._database) as session:
            return session.execute_read(do_text_search)

    def vector_search(
        self,
        label,
        property_key,
        query_text_or_vector,
        topk=10,
        index_name=None,
        ef_search=None,
    ):
        if ef_search is not None:
            if ef_search < topk:
                message = f"ef_search must be greater than or equal to topk; {ef_search!r} is invalid"
                raise ValueError(message)
        self.refresh_vector_index_meta()
        if index_name is None:
            vec_meta = self._vec_meta
            if label not in vec_meta:
                logger.warning(
                    f"vector index not defined for label, return empty. label: {label}, "
                    f"property_key: {property_key}, query_text_or_vector: {query_text_or_vector}."
                )
                return []
            vector_field = self._create_vector_field_name(property_key)
            if vector_field not in vec_meta[label]:
                logger.warning(
                    f"vector index not defined for field, return empty. label: {label}, "
                    f"property_key: {property_key}, query_text_or_vector: {query_text_or_vector}."
                )
                return []
        if index_name is None:
            index_name = self._create_vector_index_name(label, property_key)
        if isinstance(query_text_or_vector, str):
            query_vector = self.vectorizer.vectorize(query_text_or_vector)
        else:
            query_vector = query_text_or_vector

        def do_vector_search(tx):
            if ef_search is not None:
                query = (
                    "CALL db.index.vector.queryNodes($index_name, $ef_search, $query_vector) "
                    "YIELD node, score "
                    "RETURN node, score, labels(node) as __labels__"
                    f"LIMIT {topk}"
                )
                res = tx.run(
                    query,
                    query_vector=query_vector,
                    ef_search=ef_search,
                    index_name=index_name,
                )
            else:
                query = (
                    "CALL db.index.vector.queryNodes($index_name, $topk, $query_vector) "
                    "YIELD node, score "
                    "RETURN node, score, labels(node) as __labels__"
                )
                res = tx.run(
                    query, query_vector=query_vector, topk=topk, index_name=index_name
                )
            data = res.data()
            for record in data:
                record["node"]["__labels__"] = record["__labels__"]
                del record["__labels__"]
            return data

        with self._driver.session(database=self._database) as session:
            return session.execute_read(do_vector_search)

    def _create_all_graph(self, graph_name):
        with self._driver.session(database=self._database) as session:
            logger.debug(
                f"create pagerank graph graph_name：{graph_name} database：{self._database}"
            )
            result = session.run(
                f"""
            CALL gds.graph.exists('{graph_name}') YIELD exists
            WHERE exists
            CALL gds.graph.drop('{graph_name}') YIELD graphName
            RETURN graphName
            """
            )
            summary = result.consume()
            logger.debug(
                f"create pagerank graph exists graph_name：{graph_name} database：{self._database} succeed "
                f"executed：{summary.result_available_after} consumed：{summary.result_consumed_after}"
            )

            result = session.run(
                f"""
            CALL gds.graph.project('{graph_name}','*','*')
            YIELD graphName, nodeCount AS nodes, relationshipCount AS rels
            RETURN graphName, nodes, rels
            """
            )
            summary = result.consume()
            logger.debug(
                f"create pagerank graph graph_name：{graph_name} database：{self._database} succeed "
                f"executed：{summary.result_available_after} consumed：{summary.result_consumed_after}"
            )

    def _drop_all_graph(self, graph_name):
        with self._driver.session(database=self._database) as session:
            logger.debug(
                f"drop pagerank graph graph_name：{graph_name} database：{self._database}"
            )
            result = session.run(
                f"""
            CALL gds.graph.exists('{graph_name}') YIELD exists
            WHERE exists
            CALL gds.graph.drop('{graph_name}') YIELD graphName
            RETURN graphName
            """
            )
            result.consume()
            logger.debug(
                f"drop pagerank graph graph_name：{graph_name} database：{self._database} succeed"
            )

    def execute_pagerank(self, iterations=20, damping_factor=0.85):
        with self._driver.session(database=self._database) as session:
            return session.execute_write(
                self._execute_pagerank, iterations, damping_factor
            )

    @staticmethod
    def _execute_pagerank(tx, iterations, damping_factor):
        query = (
            "CALL algo.pageRank.stream("
            "{iterations: $iterations, dampingFactor: $damping_factor}) "
            "YIELD nodeId, score "
            "RETURN algo.getNodeById(nodeId) AS node, score "
            "ORDER BY score DESC"
        )
        result = tx.run(query, iterations=iterations, damping_factor=damping_factor)
        return [{"node": record["node"], "score": record["score"]} for record in result]

    def get_pagerank_scores(self, start_nodes, target_type):
        with self._driver.session(database=self._database) as session:
            all_graph = self._allGraph
            self._exists_all_graph(session, all_graph)
            data = session.execute_write(
                self._get_pagerank_scores, self, all_graph, start_nodes, target_type
            )
        return data

    @staticmethod
    def _get_pagerank_scores(tx, self, graph_name, start_nodes, return_type):
        match_clauses = []
        match_identify = []
        for index, node in enumerate(start_nodes):
            node_type, node_name = node["type"], node["name"]
            node_identify = f"node_{index}"
            match_clauses.append(
                f"MATCH ({node_identify}:{self._escape_neo4j(node_type)} {{name: '{escape_single_quotes(node_name)}'}})"
            )
            match_identify.append(node_identify)

        match_query = " ".join(match_clauses)
        match_identify_str = ", ".join(match_identify)

        pagerank_query = f"""
        {match_query}
        CALL gds.pageRank.stream('{graph_name}',{{
            maxIterations: 20,
            dampingFactor: 0.85,
            sourceNodes: [{match_identify_str}]
        }})
        YIELD nodeId, score
        MATCH (m:{return_type}) WHERE id(m) = nodeId
        RETURN id(m) AS g_id, gds.util.asNode(nodeId).id AS id, score
        ORDER BY score DESC
        """

        result = tx.run(pagerank_query)
        return [{"id": record["id"], "score": record["score"]} for record in result]

    @staticmethod
    def _exists_all_graph(session, graph_name):
        try:
            logger.debug(f"exists pagerank graph graph_name：{graph_name}")
            result = session.run(
                f"""
            CALL gds.graph.exists('{graph_name}') YIELD exists
            WHERE NOT exists
            CALL gds.graph.project('{graph_name}','*','*')
            YIELD graphName, nodeCount AS nodes, relationshipCount AS rels
            RETURN graphName, nodes, rels
            """
            )
            summary = result.consume()
            logger.debug(
                f"exists pagerank graph graph_name：{graph_name} succeed "
                f"executed：{summary.result_available_after} consumed：{summary.result_consumed_after}"
            )
        except Exception as e:
            logger.debug(f"Error exists pagerank graph {graph_name}: {e}")

    def count(self, label):
        with self._driver.session(database=self._database) as session:
            return session.execute_read(self._count, self, label)

    @staticmethod
    def _count(tx, self, label):
        query = f"MATCH (n:{self._escape_neo4j(label)}) RETURN count(n)"
        result = tx.run(query)
        single_result = result.single()
        if single_result is not None:
            return single_result[0]

    def create_database(self, database):
        with self._driver.session(database=self._database) as session:
            database = database.lower()
            result = session.run(
                f"CREATE DATABASE {self._escape_neo4j(database)} IF NOT EXISTS"
            )
            summary = result.consume()
            logger.info(
                f"create_database {database} succeed "
                f"executed：{summary.result_available_after} consumed：{summary.result_consumed_after}"
            )

    def delete_all_data(self, database):
        if self._database != database:
            raise ValueError(
                f"Error: Current database ({self._database}) is not the same as the target database ({database})."
            )

        with self._driver.session(database=database) as session:
            while True:
                result = session.run(
                    "MATCH (n)  WITH n LIMIT 100000  DETACH DELETE n RETURN count(*)"
                )
                count = result.single()[0]
                logger.info(f"Deleted {count} nodes in this batch.")
                if count == 0:
                    logger.info("All data has been deleted.")
                    break

    def run_cypher_query(self, database, query, parameters=None):
        if database and self._database != database:
            raise ValueError(
                f"Current database ({self._database}) is not the same as the target database ({database})."
            )

        with self._driver.session(database=database) as session:
            result = session.run(query, parameters)
            return [record for record in result]
