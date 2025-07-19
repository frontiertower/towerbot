#!/usr/bin/env python3
"""Generate NodeTypeEnum and EdgeTypeEnum from ontology definitions.

This script extracts node and edge types from the ontology.py file and generates
the corresponding enums to ensure they stay in sync. Run this script whenever
the ontology is updated to maintain consistency.
"""

import ast

from pathlib import Path
from typing import List, Tuple, Dict


def extract_ontology_types() -> Tuple[List[str], List[str], Dict[Tuple[str, str], List[str]]]:
    """Extract node and edge types from ontology.py, plus relationship mappings.
    
    Returns:
        Tuple of (node_types, edge_types, edge_type_map) where edge_type_map
        maps (source_type, target_type) tuples to lists of valid edge types
    """
    # Get the path to ontology.py
    script_dir = Path(__file__).parent
    ontology_path = script_dir.parent / "app" / "schemas" / "ontology.py"
    
    if not ontology_path.exists():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
    
    # Parse the ontology file
    with open(ontology_path, 'r') as f:
        tree = ast.parse(f.read())
    
    node_types = []
    edge_types = []
    edge_type_map = {}
    
    # Walk through all class definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            
            # Look for Config class with label attribute
            for class_body_item in node.body:
                if (isinstance(class_body_item, ast.ClassDef) and 
                    class_body_item.name == "Config"):
                    
                    # Look for label assignment in Config class
                    for config_item in class_body_item.body:
                        if (isinstance(config_item, ast.Assign) and 
                            len(config_item.targets) == 1 and
                            isinstance(config_item.targets[0], ast.Name) and
                            config_item.targets[0].id == "label"):
                            
                            if isinstance(config_item.value, ast.Constant):
                                label = config_item.value.value
                                
                                # Determine if it's a node or edge type based on naming convention
                                # Edge types are typically ALL_CAPS, node types are PascalCase
                                # Also check if it's a known relationship class
                                relationship_classes = {
                                    'Sent', 'SentIn', 'InReplyTo', 'LocatedOn', 'WorksOn', 
                                    'Attends', 'InterestedIn', 'RelatedTo'
                                }
                                
                                if label.isupper() and '_' in label or class_name in relationship_classes:
                                    edge_types.append(label)
                                    
                                    # Extract relationship mappings for edge types
                                    source_types = []
                                    target_types = []
                                    
                                    for config_item in class_body_item.body:
                                        if isinstance(config_item, ast.Assign):
                                            if (len(config_item.targets) == 1 and
                                                isinstance(config_item.targets[0], ast.Name)):
                                                
                                                attr_name = config_item.targets[0].id
                                                if attr_name == "source_types" and isinstance(config_item.value, ast.List):
                                                    source_types = [elt.value for elt in config_item.value.elts if isinstance(elt, ast.Constant)]
                                                elif attr_name == "target_types" and isinstance(config_item.value, ast.List):
                                                    target_types = [elt.value for elt in config_item.value.elts if isinstance(elt, ast.Constant)]
                                    
                                    # Create mappings for all source-target combinations
                                    for source_type in source_types:
                                        for target_type in target_types:
                                            key = (source_type, target_type)
                                            if key not in edge_type_map:
                                                edge_type_map[key] = []
                                            edge_type_map[key].append(label)
                                else:
                                    node_types.append(label)
    
    return sorted(node_types), sorted(edge_types), edge_type_map


def generate_enum_code(node_types: List[str], edge_types: List[str], edge_type_map: Dict[Tuple[str, str], List[str]]) -> str:
    """Generate the enum definitions and relationship mappings code.
    
    Args:
        node_types: List of node type labels
        edge_types: List of edge type labels
        edge_type_map: Dictionary mapping (source, target) pairs to edge types
        
    Returns:
        Generated Python code for the enums and mappings
    """
    code = '''"""Auto-generated enums from ontology definitions.

This file is automatically generated by scripts/generate_enums.py.
Do not edit manually - run the script to regenerate.
"""

from enum import Enum

class NodeTypeEnum(str, Enum):
    """Enumeration of node types in the knowledge graph."""
'''
    
    # Add node type enum values
    for node_type in node_types:
        # Convert label to enum name (e.g., "User" -> "User")
        enum_name = node_type
        code += f'    {enum_name} = "{node_type}"\n'
    
    code += '''
class EdgeTypeEnum(str, Enum):
    """Enumeration of edge types in the knowledge graph."""
'''
    
    # Add edge type enum values
    for edge_type in edge_types:
        # Convert label to enum name (e.g., "SENT" -> "Sent", "IN_REPLY_TO" -> "InReplyTo")
        enum_name = ''.join(word.capitalize() for word in edge_type.split('_'))
        code += f'    {enum_name} = "{edge_type}"\n'
    
    # Add the edge type mapping
    code += '''\n# Auto-generated edge type mappings from ontology relationship definitions
EDGE_TYPE_MAP = {
'''
    
    for (source_type, target_type), edge_type_list in sorted(edge_type_map.items()):
        edge_types_str = '[' + ', '.join(f'"{edge_type}"' for edge_type in sorted(edge_type_list)) + ']'
        code += f'    ("{source_type}", "{target_type}"): {edge_types_str},\n'
    
    code += '}\n'
    
    return code


def main():
    """Main function to generate the enums."""
    try:
        print("Extracting types from ontology.py...")
        node_types, edge_types, edge_type_map = extract_ontology_types()
        
        print(f"Found {len(node_types)} node types: {', '.join(node_types)}")
        print(f"Found {len(edge_types)} edge types: {', '.join(edge_types)}")
        print(f"Found {len(edge_type_map)} relationship mappings")
        
        print("Generating enum code...")
        enum_code = generate_enum_code(node_types, edge_types, edge_type_map)
        
        # Write to generated file
        script_dir = Path(__file__).parent
        generated_path = script_dir.parent / "app" / "schemas" / "generated_enums.py"
        
        with open(generated_path, 'w') as f:
            f.write(enum_code)
        
        print(f"Generated enums written to: {generated_path}")
        print("✅ Enum generation complete!")
        
    except Exception as e:
        print(f"❌ Error generating enums: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())