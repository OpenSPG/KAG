import yaml
import json
import argparse


def read_and_modify_yaml(yml_data, key_to_update, new_value):
    """
    Read a YAML file and replace the value of a specified key.

    :param yml_data: YAML data
    :param key_to_update: Key to update (supports nested keys, separated by dots, e.g., 'parent.child.key')
    :param new_value: New value
    """

    # Update the value of the specified key
    keys = key_to_update.split(".")  # Split nested keys into a list
    current_level = yml_data
    for key in keys[:-1]:
        if key not in current_level:
            raise KeyError(f"Key '{key}' not found in the YAML structure.")
        current_level = current_level[key]  # Step into the nested structure
    current_level[keys[-1]] = new_value  # Replace the value of the target key


def replace_values_in_yaml(yaml_file, replacements):
    """
    Replace values in a YAML file based on a dictionary of replacements.

    :param yaml_file: Path to the YAML file
    :param replacements: Dictionary of keys and their new values
    """
    # Read the YAML file
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)

    for k, v in replacements.items():
        read_and_modify_yaml(data, k, v)

    with open(yaml_file, "w") as file:
        yaml.dump(data, file, sort_keys=False, default_flow_style=False)

    print("YAML env finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Environment arguments")
    parser.add_argument(
        "--yml_file_path",
        type=str,
        help="Path to the modified YAML configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--env_json_path",
        type=str,
        help="Path to the modified environment configuration JSON file",
        metavar="FILE",
    )
    args = parser.parse_args()
    env_json_path = args.env_json_path
    yml_file_path = args.yml_file_path
    with open(env_json_path, "r") as f:
        env_json = json.load(f)
    replace_values_in_yaml(yaml_file=yml_file_path, replacements=env_json)
    print(f"Finished replacing {yml_file_path} with {env_json_path}")
