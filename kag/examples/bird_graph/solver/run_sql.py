import os
import sqlite3


def execute_sql(dbname, sql):
    """
    从指定目录加载 SQLite 数据库并执行 SQL 查询。

    :param dbname: 数据库文件的名称（例如 'example.sqlite'）
    :param sql: 要执行的 SQL 查询
    :return: SQL 查询的执行结果
    """
    try:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "table_2_graph",
            "bird_dev_table_dataset",
            "dev_databases",
            dbname,
            f"{dbname}.sqlite",
        )

        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件 '{db_path}' 不存在。")

        # 连接到 SQLite 数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 执行 SQL 查询
        cursor.execute(sql)
        result = cursor.fetchall()

        # 关闭连接
        cursor.close()
        conn.close()

        return result

    except sqlite3.Error as e:
        print(f"SQLite 错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")


# 示例使用
if __name__ == "__main__":
    # 执行查询并打印结果
    results = execute_sql(
        "california_schools",
        """
SELECT County,ClosedDate FROM schools WHERE strftime('%Y', ClosedDate) BETWEEN '1980' AND '1989' AND StatusType = 'Closed' AND SOC = 11
-- SELECT T1.AvgScrMath, T2.County , T1.AvgScrMath, T1.AvgScrRead , T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T1.AvgScrMath IS NOT NULL ORDER BY T1.AvgScrMath + T1.AvgScrRead + T1.AvgScrWrite ASC LIMIT 1
""".strip(),
    )
    limit = 30
    if results:
        print("查询结果len=", len(results))
        print("查询结果：")
        for row in results[:limit]:
            print(row)
    else:
        print("没有结果")
