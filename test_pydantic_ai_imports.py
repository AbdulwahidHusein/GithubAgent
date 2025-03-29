#!/usr/bin/env python3

"""
Test script to identify what modules and classes are available in the pydantic_ai package.
"""

import sys
import importlib

def check_import(module_path, class_name=None):
    """Try to import a module or class and report the result."""
    try:
        if class_name:
            module = importlib.import_module(module_path)
            getattr(module, class_name)
            print(f"✅ Successfully imported {class_name} from {module_path}")
        else:
            importlib.import_module(module_path)
            print(f"✅ Successfully imported {module_path}")
    except ImportError as e:
        print(f"❌ ImportError: {e}")
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")

if __name__ == "__main__":
    print("Testing pydantic_ai imports...")
    
    # Version check
    try:
        import pydantic_ai
        print(f"pydantic-ai version: {pydantic_ai.__version__}")
    except (ImportError, AttributeError) as e:
        print(f"Could not get pydantic-ai version: {e}")
    
    # Check main modules
    check_import("pydantic_ai")
    check_import("pydantic_ai.agent")
    check_import("pydantic_ai.messages")
    check_import("pydantic_ai.result")
    
    # Check specific classes that we're having issues with
    check_import("pydantic_ai.messages", "SystemMessage")
    check_import("pydantic_ai.messages", "UserMessage")
    check_import("pydantic_ai.messages", "SystemPromptPart")  # New name?
    
    # Check other import locations
    check_import("pydantic_ai_slim.pydantic_ai.messages", "SystemPromptPart")
    
    print("\nDone testing imports.") 