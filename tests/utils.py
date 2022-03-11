import yaml


def assert_same_yaml(file_a: str, file_b: str):
    """Assert that two yaml files are the same.

    Args:
        file_a (str): The first file.
        file_b (str): The second file.

    Raises:
        AssertionError: If the files are not the same.
    """
    with open(file_a) as f:
        a = yaml.safe_load(f)
    with open(file_b) as f:
        b = yaml.safe_load(f)
    assert a == b
