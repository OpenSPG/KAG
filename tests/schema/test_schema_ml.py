from knext.schema.marklang.schema_ml import SPGSchemaMarkLang


def test_load_schema():
    schema_file = "../../kag/examples/medicine/schema/Medicine.schema"
    ml = SPGSchemaMarkLang(schema_file, with_server=False)
    for _,m in ml.types.items():
        for r in m.relations.values():
            print(r.object_type_name)
    print(ml.types)

test_load_schema()