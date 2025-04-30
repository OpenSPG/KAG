#!/bin/bash


DIR_NAME='bird_dev_graph_dataset'

# 目标路径
HOST_TARGET_PATH="/root/dozerdb/logs"
CONTAINER_SOURCE_PATH="/logs/$DIR_NAME"
CONTAINER_TARGET_PATH="/var/lib/neo4j/import"

# Step 1: 拷贝当前目录下的 dir_name 到 /root/dozerdb/logs
echo "Copying $DIR_NAME to $HOST_TARGET_PATH..."
sudo cp -r "$DIR_NAME" "$HOST_TARGET_PATH/"
if [ $? -ne 0 ]; then
  echo "Failed to copy $DIR_NAME to $HOST_TARGET_PATH. Exiting."
  exit 1
fi
echo "Copy completed successfully."

# Step 2: 使用 Docker 进入容器并执行拷贝命令
# 假设容器名称为 neo4j-container（请根据实际情况修改）
CONTAINER_NAME="release-openspg-neo4j"

# 检查容器是否正在运行
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME\$"; then
  echo "Container $CONTAINER_NAME is not running. Please start the container and try again."
  exit 1
fi

echo "Copying $CONTAINER_SOURCE_PATH to $CONTAINER_TARGET_PATH inside container $CONTAINER_NAME..."
docker exec -it "$CONTAINER_NAME" bash -c "rm -rf $CONTAINER_TARGET_PATH/$DIR_NAME && cp -r $CONTAINER_SOURCE_PATH $CONTAINER_TARGET_PATH"
if [ $? -ne 0 ]; then
  echo "Failed to copy $CONTAINER_SOURCE_PATH to $CONTAINER_TARGET_PATH inside container. Exiting."
  exit 1
fi
echo "Copy inside container completed successfully."

echo "All tasks completed successfully."
