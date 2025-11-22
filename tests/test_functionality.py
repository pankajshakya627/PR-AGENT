import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock dependencies BEFORE importing main
sys.modules["github"] = MagicMock()
sys.modules["src.github_provider"] = MagicMock()

# Mock the GitHubProvider class specifically
mock_github_provider = MagicMock()
mock_github_provider.get_pr_diff.return_value = "diff --git a/file.py b/file.py\n+ new line"
mock_github_provider.get_pr_details.return_value = {"title": "Test PR", "body": "Test Body"}
mock_github_provider.get_files_in_repo.return_value = ["file.py"]

# Patch the class in the module
with patch("src.github_provider.GitHubProvider", return_value=mock_github_provider):
    # Mock LLM responses
    with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
        mock_llm = MagicMock()
        
        # Helper to create async response
        def create_response(content):
            print(f"DEBUG: create_response called with {content[:20]}...")
            mock_resp = MagicMock()
            mock_resp.content = content
            
            # Set return_value for synchronous call (if LangChain treats it as function)
            mock_llm.return_value = mock_resp
            
            # Set return_value for async call (if LangChain uses ainvoke)
            f = asyncio.Future()
            f.set_result(mock_resp)
            # mock_llm.ainvoke.return_value = f # This is set by the caller usually, but let's return f
            
            return f

        # Default response
        mock_llm.ainvoke.return_value = create_response("default")
        
        MockChatOpenAI.return_value = mock_llm
        
        # Now import main which imports agents which import LLM
        from main import (
            create_pull_request,
            analyze_dependencies,
            review_pr,
            describe_pr,
            improve_code,
            ask_pr,
            update_changelog
        )

        async def test_tools():
            print("Testing FastMCP Tools Functionality...")

            # 1. Test review_pr
            print("\nTesting review_pr...")
            print(f"review_pr type: {type(review_pr)}")
            print(f"review_pr dir: {dir(review_pr)}")
            
            # Setup specific response
            mock_llm.ainvoke.return_value = create_response("""
summary: Test Summary
status: APPROVE
issues[1]{type,file,line,description,suggestion}:
style,file.py,1,Test issue,Test suggestion
""")
            try:
                # Attempt to find the underlying function
                if hasattr(review_pr, "fn"):
                    func = review_pr.fn
                    result = await func("https://github.com/owner/repo/pull/1")
                elif hasattr(review_pr, "run"):
                     # It might be an async run method
                     result = await review_pr.run(pr_url="https://github.com/owner/repo/pull/1")
                else:
                    # Fallback
                    result = await review_pr("https://github.com/owner/repo/pull/1")
                
                print(f"Result: {result}")
                if "summary" in result:
                    print("  ✅ review_pr success")
                else:
                    print("  ❌ review_pr failed structure check")
            except Exception as e:
                print(f"  ❌ review_pr threw exception: {e}")

            # 2. Test describe_pr
            print("\nTesting describe_pr...")
            mock_llm.ainvoke.return_value = create_response("""
title: Test Title
type: feat
summary: Test Summary
walkthrough: Test Walkthrough
labels[1]{name}:
test-label
""")
            try:
                result = await describe_pr.fn("https://github.com/owner/repo/pull/1")
                print(f"Result: {result}")
                if "title" in result:
                     print("  ✅ describe_pr success")
                else:
                     print("  ❌ describe_pr failed structure check")
            except Exception as e:
                print(f"  ❌ describe_pr threw exception: {e}")

            # 3. Test improve_code
            print("\nTesting improve_code...")
            mock_llm.ainvoke.return_value = create_response("""
suggestions[1]{file,description,code_snippet}:
file.py,Test improvement,code
""")
            try:
                result = await improve_code.fn("https://github.com/owner/repo/pull/1")
                print(f"Result: {result}")
                if "suggestions" in result:
                     print("  ✅ improve_code success")
                else:
                     print("  ❌ improve_code failed structure check")
            except Exception as e:
                print(f"  ❌ improve_code threw exception: {e}")

            # 4. Test ask_pr
            print("\nTesting ask_pr...")
            mock_llm.ainvoke.return_value = create_response("This is an answer.")
            try:
                result = await ask_pr.fn("https://github.com/owner/repo/pull/1", "What is this?")
                print(f"Result: {result}")
                if result == "This is an answer.":
                     print("  ✅ ask_pr success")
                else:
                     print("  ❌ ask_pr failed content check")
            except Exception as e:
                print(f"  ❌ ask_pr threw exception: {e}")

            # 5. Test update_changelog
            print("\nTesting update_changelog...")
            mock_llm.ainvoke.return_value = create_response("""
entries[1]{type,description}:
feat,Test feature
""")
            try:
                result = await update_changelog.fn("https://github.com/owner/repo/pull/1")
                print(f"Result: {result}")
                if "- feat: Test feature" in result:
                     print("  ✅ update_changelog success")
                else:
                     print("  ❌ update_changelog failed content check")
            except Exception as e:
                print(f"  ❌ update_changelog threw exception: {e}")

        if __name__ == "__main__":
            asyncio.run(test_tools())
