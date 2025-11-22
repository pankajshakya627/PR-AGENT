import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import mcp

def verify_mcp():
    print("Verifying MCP Server Configuration...")
    
    # Check Tools
    print(f"Tool Manager Attributes: {dir(mcp._tool_manager)}")
    # Assuming _tool_manager has a way to list tools, maybe _tools dict
    if hasattr(mcp._tool_manager, "_tools"):
        tools = mcp._tool_manager._tools
    else:
        # Fallback: try to see if it's a dict itself or has other attributes
        tools = {}
        print("Could not find _tools in _tool_manager")

    print(f"\nRegistered Tools: {len(tools)}")
    expected_tools = [
        "create_pull_request", "analyze_dependencies", "review_pr", 
        "describe_pr", "improve_code", "ask_pr", "update_changelog"
    ]
    for tool_name in expected_tools:
        if tool_name in tools:
            print(f"  ✅ {tool_name}")
        else:
            print(f"  ❌ {tool_name} NOT FOUND")
            
    # Check Prompts
    # print(f"Prompt Manager Attributes: {dir(mcp._prompt_manager)}")
    if hasattr(mcp._prompt_manager, "_prompts"):
        prompts = mcp._prompt_manager._prompts
    else:
        prompts = {}
        print("Could not find _prompts in _prompt_manager")

    print(f"\nRegistered Prompts: {len(prompts)}")
    expected_prompts = [
        "code_review_prompt", "pr_description_prompt", 
        "code_improvement_prompt", "pr_questions_prompt", "changelog_prompt"
    ]
    for prompt_name in expected_prompts:
        if prompt_name in prompts:
            print(f"  ✅ {prompt_name}")
        else:
            print(f"  ❌ {prompt_name} NOT FOUND")

    # Check Resources
    # print(f"Resource Manager Attributes: {dir(mcp._resource_manager)}")
    if hasattr(mcp._resource_manager, "_resources"):
        resources = mcp._resource_manager._resources
    else:
        resources = {}
        print("Could not find _resources in _resource_manager")

    print(f"\nRegistered Resources: {len(resources)}")
    expected_resources = ["config://llm", "config://agent"]
    
    found_resources = []
    for pattern in resources:
        found_resources.append(str(pattern))
        
    for res in expected_resources:
        if res in found_resources:
             print(f"  ✅ {res}")
        else:
             print(f"  ❌ {res} NOT FOUND")

    print("\nVerification Complete.")

if __name__ == "__main__":
    verify_mcp()
