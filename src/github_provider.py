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

    def _get_repo_and_commit_sha(self, commit_url: str) -> tuple[str, str]:
        """Extracts repo name and commit SHA from a commit URL.
        
        Example: https://github.com/owner/repo/commit/abc123def456
        """
        parts = commit_url.rstrip("/").split("/")
        if "github.com" not in parts:
            raise ValueError("Invalid GitHub URL")
        
        try:
            commit_index = parts.index("commit")
            commit_sha = parts[commit_index + 1]
            repo_name = f"{parts[commit_index - 2]}/{parts[commit_index - 1]}"
            return repo_name, commit_sha
        except (ValueError, IndexError):
            raise ValueError(f"Could not parse commit URL: {commit_url}")

    def get_commit_diff(self, commit_url: str) -> str:
        """Fetches the diff of a specific commit."""
        repo_name, commit_sha = self._get_repo_and_commit_sha(commit_url)
        repo = self.client.get_repo(repo_name)
        commit = repo.get_commit(commit_sha)
        
        diff_output = []
        for file in commit.files:
            diff_output.append(f"--- {file.filename}")
            diff_output.append(f"+++ {file.filename}")
            if file.patch:
                diff_output.append(file.patch)
            else:
                diff_output.append("(Binary file or large diff not shown)")
            diff_output.append("\n")
        
        return "\n".join(diff_output)

    def get_commit_details(self, commit_url: str) -> Dict[str, Any]:
        """Fetches details about a specific commit."""
        repo_name, commit_sha = self._get_repo_and_commit_sha(commit_url)
        repo = self.client.get_repo(repo_name)
        commit = repo.get_commit(commit_sha)
        
        # Convert PaginatedList to regular list
        files_list = list(commit.files)
        
        return {
            "sha": commit.sha,
            "message": commit.commit.message,
            "author": commit.commit.author.name if commit.commit.author else "Unknown",
            "date": str(commit.commit.author.date) if commit.commit.author else "",
            "files_changed": len(files_list),
            "additions": commit.stats.additions,
            "deletions": commit.stats.deletions,
            "files": [f.filename for f in files_list]
        }

    def find_existing_pr(self, repo_name: str, head: str, base: str) -> Optional[Dict[str, Any]]:
        """Find an existing open PR from head to base branch."""
        repo = self.client.get_repo(repo_name)
        
        # Get open PRs from head to base
        pulls = repo.get_pulls(state='open', head=f"{repo_name.split('/')[0]}:{head}", base=base)
        for pr in pulls:
            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title
            }
        return None

    def create_or_update_pr(self, repo_name: str, title: str, body: str, 
                             head: str, base: str = "main") -> Dict[str, Any]:
        """
        Creates a new Pull Request or updates an existing one.
        
        Args:
            repo_name: Repository in format 'owner/repo'
            title: PR title
            body: PR description/body
            head: Source branch (the branch with your changes)
            base: Target branch (e.g., 'main' or 'master')
            
        Returns:
            Dictionary with PR details including URL and number
        """
        repo = self.client.get_repo(repo_name)
        
        # Check for existing PR
        existing = self.find_existing_pr(repo_name, head, base)
        
        try:
            if existing:
                # Update existing PR
                pr = repo.get_pull(existing["pr_number"])
                pr.edit(title=title, body=body)
                return {
                    "success": True,
                    "action": "updated",
                    "pr_number": pr.number,
                    "pr_url": pr.html_url,
                    "title": pr.title,
                    "state": pr.state
                }
            else:
                # Create new PR
                pr = repo.create_pull(
                    title=title,
                    body=body,
                    head=head,
                    base=base
                )
                return {
                    "success": True,
                    "action": "created",
                    "pr_number": pr.number,
                    "pr_url": pr.html_url,
                    "title": pr.title,
                    "state": pr.state
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_pr(self, repo_name: str, title: str, body: str, 
                  head: str, base: str = "main") -> Dict[str, Any]:
        """Alias for create_or_update_pr for backward compatibility."""
        return self.create_or_update_pr(repo_name, title, body, head, base)

    def get_repo_branches(self, repo_name: str) -> List[str]:
        """Get list of branches in a repository."""
        repo = self.client.get_repo(repo_name)
        return [branch.name for branch in repo.get_branches()]

    def get_commit_branch(self, commit_url: str) -> Optional[str]:
        """Try to find the branch containing a specific commit."""
        repo_name, commit_sha = self._get_repo_and_commit_sha(commit_url)
        repo = self.client.get_repo(repo_name)
        
        # Get branches and check if commit is in any
        for branch in repo.get_branches():
            try:
                # Check if branch head matches or contains the commit
                if branch.commit.sha == commit_sha:
                    return branch.name
            except:
                pass
        
        return None

    def compare_branches(self, repo_name: str, base: str, head: str) -> Dict[str, Any]:
        """
        Compare two branches and get the diff between them.
        
        Args:
            repo_name: Repository in format 'owner/repo'
            base: Base branch (target, e.g., 'main')
            head: Head branch (source with changes, e.g., 'develop')
            
        Returns:
            Dictionary with comparison details and combined diff
        """
        repo = self.client.get_repo(repo_name)
        comparison = repo.compare(base, head)
        
        # Convert PaginatedList to regular list
        files_list = list(comparison.files)
        commits_list = list(comparison.commits)
        
        # Build combined diff from all files
        diff_output = []
        for file in files_list:
            diff_output.append(f"--- {file.filename}")
            diff_output.append(f"+++ {file.filename}")
            if file.patch:
                diff_output.append(file.patch)
            else:
                diff_output.append("(Binary file or large diff not shown)")
            diff_output.append("\n")
        
        # Get commit messages
        commit_messages = []
        for commit in commits_list:
            commit_messages.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0],  # First line only
                "author": commit.commit.author.name if commit.commit.author else "Unknown"
            })
        
        return {
            "base": base,
            "head": head,
            "ahead_by": comparison.ahead_by,
            "behind_by": comparison.behind_by,
            "total_commits": len(commits_list),
            "files_changed": len(files_list),
            "additions": sum(f.additions for f in files_list),
            "deletions": sum(f.deletions for f in files_list),
            "diff": "\n".join(diff_output),
            "commits": commit_messages
        }

    def update_pr_description(self, repo_name: str, pr_number: int, 
                               title: str = None, body: str = None) -> Dict[str, Any]:
        """
        Update an existing PR's title and/or body.
        
        Args:
            repo_name: Repository in format 'owner/repo'
            pr_number: PR number to update
            title: New title (optional)
            body: New body/description (optional)
            
        Returns:
            Dictionary with update status
        """
        repo = self.client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        try:
            update_args = {}
            if title:
                update_args['title'] = title
            if body:
                update_args['body'] = body
            
            if update_args:
                pr.edit(**update_args)
            
            return {
                "success": True,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

