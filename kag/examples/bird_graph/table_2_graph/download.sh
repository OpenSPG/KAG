#!/bin/bash

# 定义文件和目录路径
zip_file="dev.zip"
output_dir="bird_dev_table_dataset"

# 如果 dev.zip 已存在，则跳过下载
if [ -f "$zip_file" ]; then
    echo "File '$zip_file' already exists. Skipping download."
else
    # 下载 dev.zip
    echo "Downloading $zip_file..."
    wget https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip
    if [ $? -ne 0 ]; then
        echo "Error: Failed to download $zip_file"
        exit 1
    fi
fi


# 解压 dev.zip
echo "Unzipping $zip_file..."
unzip -o "$zip_file"

# 重命名解压后的目录
mv dev_20240627 "$output_dir"


pushd "$output_dir"

echo "Unzipping dev_databases.zip ..."
unzip dev_databases.zip

# 查找所有 CSV 文件，并逐一处理它们
find dev_databases -type f -name "*.csv" | while read csv_file; do
    echo "Converting file: $csv_file"

    # 使用临时文件保存处理结果，防止原地修改
    temp_file="${csv_file}.tmp"

    # iconv 处理非法字符，并同时去除 BOM 标头
    iconv -f UTF-8 -t UTF-8 "$csv_file" 2>/dev/null | sed '1 s/^\xef\xbb\xbf//' > "$temp_file"

    # 检查 iconv 是否成功
    if [ $? -eq 0 ]; then
        # 替换原文件
        mv "$temp_file" "$csv_file"
        echo "Converted successfully: $csv_file"
    else
        echo "Error converting file: $csv_file"
        # 删除临时文件
        rm -f "$temp_file"
    fi
done

popd