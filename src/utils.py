from typing import List

def format_file_tree(files: List[str]) -> str:
    """
    Formats a list of file paths into a tree-like string structure.
    """
    # Simple indentation based on depth
    tree_str = ""
    files.sort()
    for file in files:
        depth = file.count('/')
        indent = "  " * depth
        tree_str += f"{indent}- {file}\n"
    return tree_str
