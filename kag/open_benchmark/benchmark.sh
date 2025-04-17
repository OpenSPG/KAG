#!/bin/bash

# Check if directory parameter is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory> <command> <data_set>"
  echo "Commands: build, eval, all"
  echo "Data name: all, sub, train"
  exit 1
fi

bench_dir=$1

# Check if directory exists
if [ ! -d "$bench_dir" ]; then
  echo "Error: Directory $bench_dir does not exist."
  exit 1
fi

# Check if command parameter is provided
if [ -z "$2" ]; then
  echo "Usage: $0 <directory> <command> <data_set>"
  echo "Commands: build, eval, all"
  echo "Data name: all, sub, train"
  exit 1
fi

command=$2

# Check if data set parameter is provided
if [ -z "$3" ]; then
  echo "Usage: $0 <directory> <command> <data_set>"
  echo "Commands: build, eval, all"
  echo "Data name: all, sub, train"
  exit 1
fi

data_set=$3

# Replace environment variables
python utils/key_utils.py --yml_file_path "$bench_dir/kag_config.yaml" --env_json_path env.json

# Check if python script executed successfully
if [ $? -ne 0 ]; then
  echo "Error: Failed to execute key_utils.py"
  exit 1
fi

# Change to bench_dir directory
cd "$bench_dir" || exit 1

# Execute the corresponding command
case $command in
  build)
    knext project restore --proj_path ./
    if [ $? -ne 0 ]; then
      echo "Error: Restore failed."
      exit 1
    fi
    knext schema commit
    if [ $? -ne 0 ]; then
      echo "Error: Schema failed."
      exit 1
    fi
    cd builder  || exit 1
    if [ "$data_set" == "all" ]; then
      python indexer.py --corpus_file "./data/corpus.json"
    else
      python indexer.py --corpus_file "./data/${data_set}_corpus.json"
    fi
    ;;
  eval)
    cd solver  || exit 1
    if [ "$data_set" == "all" ]; then
      python eval.py --qa_file "./data/qa.json"
    else
      python eval.py --qa_file "./data/qa_${data_set}.json"
    fi
    ;;
  all)
    knext project restore --proj_path ./
    if [ $? -ne 0 ]; then
      echo "Error: Restore failed."
      exit 1
    fi
    knext schema commit
    if [ $? -ne 0 ]; then
      echo "Error: Schema failed."
      exit 1
    fi
    cd builder  || exit 1
    if [ "$data_set" == "all" ]; then
      python indexer.py --corpus_file "./data/corpus.json"
    else
      python indexer.py --corpus_file "./data/${data_set}_corpus.json"
    fi
    if [ $? -ne 0 ]; then
      echo "Error: Build failed."
      exit 1
    fi
    cd ../solver  || exit 1
    if [ "$data_set" == "all" ]; then
      python eval.py --qa_file "./data/qa.json"
    else
      python eval.py --qa_file "./data/qa_${data_set}.json"
    fi
    ;;
  *)
    echo "Error: Unknown command $command"
    echo "Usage: $0 <directory> <command> <data_set>"
    echo "Commands: build, eval, all"
    echo "Data name: all, sub, train"
    exit 1
    ;;
esac