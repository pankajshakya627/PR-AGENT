#!/usr/bin/env python3
"""
CLI entry point for PR-Agent.

Usage:
    python cli.py --action review --pr-number 123 --repo owner/repo --post-comment
    python cli.py --action describe --pr-number 123 --repo owner/repo
    python cli.py --action all --pr-number 123 --repo owner/repo --post-comment
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.config import get_llm_config
from src.github_provider import GitHubProvider
from src.github_commenter import GitHubCommenter
from src.agents.specialized import (
    CodeReviewAgent,
    PRDescriptionAgent,
    CodeImprovementAgent,
    ChangelogAgent
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PR-Agent CLI - AI-powered Pull Request Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --action review --pr-number 123 --repo owner/repo
  python cli.py --action all --pr-number 42 --repo myorg/myrepo --post-comment
  python cli.py --action describe --pr-url https://github.com/owner/repo/pull/123
        """
    )
    
    parser.add_argument(
        "--action",
        choices=["review", "describe", "improve", "changelog", "all"],
        default="review",
        help="Action to perform (default: review)"
    )
    
    parser.add_argument(
        "--pr-number",
        type=int,
        help="Pull request number"
    )
    
    parser.add_argument(
        "--pr-url",
        type=str,
        help="Full PR URL (alternative to --pr-number and --repo)"
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository in format 'owner/repo'"
    )
    
    parser.add_argument(
        "--post-comment",
        action="store_true",
        help="Post results as PR comment (requires GITHUB_TOKEN)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    return parser.parse_args()


def extract_pr_info(args):
    """Extract PR number and repo from arguments."""
    if args.pr_url:
        # Parse URL: https://github.com/owner/repo/pull/123
        parts = args.pr_url.rstrip('/').split('/')
        if 'github.com' in args.pr_url and 'pull' in parts:
            pull_idx = parts.index('pull')
            pr_number = int(parts[pull_idx + 1])
            repo = f"{parts[pull_idx - 2]}/{parts[pull_idx - 1]}"
            return pr_number, repo
        else:
            raise ValueError(f"Invalid PR URL format: {args.pr_url}")
    elif args.pr_number and args.repo:
        return args.pr_number, args.repo
    else:
        raise ValueError("Must provide either --pr-url or both --pr-number and --repo")


async def run_agent(agent_class, state):
    """Run a single agent and return results."""
    agent = agent_class()
    return await agent.execute(state)


async def run_analysis(action: str, pr_number: int, repo: str, verbose: bool = False):
    """Run the specified analysis action(s)."""
    
    # Get PR diff from GitHub
    if verbose:
        print(f"📥 Fetching PR #{pr_number} from {repo}...")
    
    github_token = os.getenv("GITHUB_TOKEN")
    pr_url = f"https://github.com/{repo}/pull/{pr_number}"
    
    provider = GitHubProvider(github_token)
    pr_data = provider.get_pr_data(pr_url)
    
    if not pr_data:
        raise RuntimeError(f"Failed to fetch PR data from {pr_url}")
    
    diff = pr_data.get("diff", "")
    if not diff:
        raise RuntimeError("No diff content found in PR")
    
    if verbose:
        print(f"📊 Diff size: {len(diff)} characters")
    
    # Prepare state for agents
    state = {
        "pr_requirements": f"Analyze PR #{pr_number}",
        "pr_url": pr_url,
        "github_token": github_token,
        "diff": diff,
        "pr_data": pr_data,
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    
    results = {}
    
    # Determine which agents to run
    agents_to_run = []
    if action == "review" or action == "all":
        agents_to_run.append(("Code Review", CodeReviewAgent))
    if action == "describe" or action == "all":
        agents_to_run.append(("PR Description", PRDescriptionAgent))
    if action == "improve" or action == "all":
        agents_to_run.append(("Code Improvement", CodeImprovementAgent))
    if action == "changelog" or action == "all":
        agents_to_run.append(("Changelog", ChangelogAgent))
    
    # Run each agent
    for name, agent_class in agents_to_run:
        if verbose:
            print(f"🤖 Running {name}...")
        
        try:
            result = await run_agent(agent_class, state)
            results[name] = result
            if verbose:
                print(f"✅ {name} completed")
        except Exception as e:
            results[name] = {"error": str(e)}
            if verbose:
                print(f"❌ {name} failed: {e}")
    
    return results


def format_results(results: dict, output_format: str = "markdown") -> str:
    """Format results for output."""
    
    if output_format == "json":
        import json
        return json.dumps(results, indent=2)
    
    # Markdown format
    output = []
    output.append("# 🤖 PR-Agent Analysis\n")
    
    for section_name, section_result in results.items():
        output.append(f"## {section_name}\n")
        
        if isinstance(section_result, dict):
            if "error" in section_result:
                output.append(f"❌ **Error**: {section_result['error']}\n")
            else:
                # Extract the actual result
                for key, value in section_result.items():
                    if isinstance(value, str):
                        output.append(value)
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            output.append(f"### {k}\n{v}\n")
        else:
            output.append(str(section_result))
        
        output.append("\n---\n")
    
    output.append("\n*Generated by [PR-Agent](https://github.com/pankajshakya627/PR-AGENT)*")
    
    return "\n".join(output)


async def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Extract PR info
        pr_number, repo = extract_pr_info(args)
        
        if args.verbose:
            config = get_llm_config()
            print(f"🔧 Using LLM provider: {config['provider']}")
            print(f"📋 Analyzing PR #{pr_number} in {repo}")
            print(f"🎯 Action: {args.action}")
        
        # Run analysis
        results = await run_analysis(
            action=args.action,
            pr_number=pr_number,
            repo=repo,
            verbose=args.verbose
        )
        
        # Format output
        formatted_output = format_results(results, args.output)
        
        # Post comment if requested
        if args.post_comment:
            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                print("⚠️  GITHUB_TOKEN not set, cannot post comment")
            else:
                if args.verbose:
                    print("📤 Posting comment to PR...")
                
                commenter = GitHubCommenter(github_token)
                success = commenter.post_comment(
                    repo=repo,
                    pr_number=pr_number,
                    body=formatted_output
                )
                
                if success:
                    print(f"✅ Comment posted to PR #{pr_number}")
                else:
                    print(f"❌ Failed to post comment")
        
        # Print to stdout
        print(formatted_output)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
