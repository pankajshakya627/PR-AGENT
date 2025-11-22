from typing import Any
import re
import yaml
import csv
import json
from toon_python import encode, EncodeOptions

def to_toon(data: Any, indent_level: int = 0) -> str:
    """
    Converts a Python object to a TOON-formatted string using the official library.
    """
    return encode(data, options=EncodeOptions(indent=2))

def from_toon(text: str) -> Any:
    """
    Parses TOON text back to Python objects.
    Since toon-python 0.1.2 does not support decoding, we use a custom robust parser
    that pre-processes TOON tables into YAML and then uses PyYAML.
    """
    # Strip markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n", "", text)
        if text.endswith("```"):
            text = text[:-3].strip()
            
    lines = text.split('\n')
    yaml_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for table header
        # Match: indent key[N]{cols}: OR indent key[N]{ OR indent key[N]:
        match = re.match(r"^(\s*)([\w_]+)(?:\[(\d+)\])?(?:\{([^}]*)\}?)?:?\s*$", line)
        
        is_table = False
        if match:
            if match.group(3) is not None: # Has [N]
                is_table = True
            elif match.group(4) is not None: # Has {cols}
                is_table = True
            elif "{" in line and not line.strip().startswith("{"): # Has open brace but not a JSON object
                is_table = True
        
        if is_table and match:
            indent = match.group(1)
            key = match.group(2)
            cols_str = match.group(4)
            
            # Parse columns
            if cols_str:
                cols = [c.strip() for c in cols_str.split(',') if c.strip()]
            else:
                cols = [] 
            
            yaml_lines.append(f"{indent}{key}:")
            key_line_index = len(yaml_lines) - 1
            
            i += 1
            rows_found = False
            # Process rows
            while i < len(lines):
                row_line = lines[i].strip()
                
                # Stop on empty line (if it looks like end of block), or closing brace/bracket
                if row_line == "}" or row_line == "]" or row_line == "},":
                    i += 1
                    break
                
                if not row_line:
                    i += 1
                    continue

                # Check if this line looks like a new key definition
                if re.match(r"^\s*[\w_]+(?:\[\d+\])?(?:\{[^}]*\})?:?\s*$", lines[i]):
                    break
                
                rows_found = True
                # Check for JSON-like row: { key: val, ... }
                if row_line.startswith("{"):
                    if row_line.endswith(","):
                        row_line = row_line[:-1]
                    yaml_lines.append(f"{indent}  - {row_line}")
                    i += 1
                    continue

                # CSV Row Processing
                # Use csv module to handle quoted values with commas correctly
                try:
                    reader = csv.reader([row_line], skipinitialspace=True)
                    vals = next(reader)
                except Exception:
                    # Fallback if csv parse fails
                    vals = row_line.split(',')
                
                vals = [v.strip() for v in vals]
                
                if not cols:
                    cols = [f"col{k}" for k in range(1, len(vals) + 1)]
                
                yaml_lines.append(f"{indent}  - {cols[0]}: {json.dumps(vals[0]) if len(vals) > 0 else 'null'}")
                for c_idx, col in enumerate(cols[1:], 1):
                    val = vals[c_idx] if c_idx < len(vals) else ""
                    # Use json.dumps to handle quoting and escaping for YAML
                    yaml_lines.append(f"{indent}    {col}: {json.dumps(val)}")
                
                i += 1
            
            if not rows_found:
                yaml_lines[key_line_index] = f"{indent}{key}: []"
            continue
        else:
            yaml_lines.append(line)
            i += 1
            
    yaml_text = "\n".join(yaml_lines)
    try:
        result = yaml.safe_load(yaml_text)
        if result is None:
            return {}
        return result
    except Exception as e:
        return {"error": str(e), "raw": text}
