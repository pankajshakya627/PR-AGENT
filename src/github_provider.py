import os
from typing import List, Dict, Any, Optional
from github import Github, Auth
from github.PullRequest import PullRequest
from github.Repository import Repository

class GitHubProvider:
    """
    Provides an interface to interact with GitHub API.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN is not set in environment variables.")
        
        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)

    def _get_repo_and_pr_number(self, pr_url: str) -> tuple[str, int]:
        """Extracts repo name and PR number from a URL."""
        # Example: https://github.com/owner/repo/pull/123
        parts = pr_url.rstrip("/").split("/")
        if "github.com" not in parts:
             raise ValueError("Invalid GitHub URL")
        
        try:
            pr_index = parts.index("pull")
            pr_number = int(parts[pr_index + 1])
            repo_name = f"{parts[pr_index - 2]}/{parts[pr_index - 1]}"
            return repo_name, pr_number
        except (ValueError, IndexError):
            raise ValueError(f"Could not parse PR URL: {pr_url}")

    def get_pr(self, pr_url: str) -> PullRequest:
        """Fetches a Pull Request object."""
        repo_name, pr_number = self._get_repo_and_pr_number(pr_url)
        repo = self.client.get_repo(repo_name)
        return repo.get_pull(pr_number)

    def get_pr_diff(self, pr_url: str) -> str:
        """Fetches the diff of a Pull Request."""
        repo_name, pr_number = self._get_repo_and_pr_number(pr_url)
        repo = self.client.get_repo(repo_name)
        # PyGithub doesn't have a direct method to get raw diff string easily without requests, 
        # but we can get files. For a true diff string, we might need to use the requests library 
        # with the Accept header 'application/vnd.github.v3.diff'.
        # However, let's try to construct a useful diff representation from files.
        
        pr = repo.get_pull(pr_number)
        files = pr.get_files()
        
        diff_output = []
        for file in files:
            diff_output.append(f"--- {file.filename}")
            diff_output.append(f"+++ {file.filename}")
            if file.patch:
                diff_output.append(file.patch)
            else:
                diff_output.append("(Binary file or large diff not shown)")
            diff_output.append("\n")
            
        return "\n".join(diff_output)

    def get_pr_details(self, pr_url: str) -> Dict[str, Any]:
        """Fetches PR details like title, description, and comments."""
        pr = self.get_pr(pr_url)
        
        comments = [c.body for c in pr.get_issue_comments()]
        
        return {
            "title": pr.title,
            "description": pr.body,
            "author": pr.user.login,
            "state": pr.state,
            "comments": comments,
            "branch": pr.head.ref,
            "base": pr.base.ref
        }

    def post_comment(self, pr_url: str, body: str) -> str:
        """Posts a comment on the PR."""
        pr = self.get_pr(pr_url)
        comment = pr.create_issue_comment(body)
        return comment.html_url

    def get_files_in_repo(self, pr_url: str) -> List[str]:
        """Returns a list of all files in the repository (recursive)."""
        # Note: This can be expensive for large repos.
        repo_name, _ = self._get_repo_and_pr_number(pr_url)
        repo = self.client.get_repo(repo_name)
        contents = repo.get_contents("")
        all_files = []
        
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                all_files.append(file_content.path)
                
        return all_files
