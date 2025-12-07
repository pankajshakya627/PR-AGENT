# GitHub Actions CI/CD Integration

This guide explains how to set up PR-Agent to automatically review your pull requests using GitHub Actions.

## Quick Setup (5 minutes)

### Step 1: Add Secrets

Go to your repository **Settings → Secrets and variables → Actions** and add:

| Secret               | Required | Description                    |
| -------------------- | -------- | ------------------------------ |
| `OPENAI_API_KEY`     | Yes\*    | Your OpenAI API key            |
| `ANTHROPIC_API_KEY`  | No       | For Claude models              |
| `OPENROUTER_API_KEY` | No       | For other models (Grok, Llama) |

\*At least one LLM API key is required.

### Step 2: Add Variables (Optional)

Go to **Settings → Secrets and variables → Actions → Variables**:

| Variable       | Default  | Options                             |
| -------------- | -------- | ----------------------------------- |
| `LLM_PROVIDER` | `openai` | `openai`, `anthropic`, `openrouter` |

### Step 3: Push the Workflow

The workflow file is already at `.github/workflows/pr-agent.yml`. Just push it:

```bash
git add .github/
git commit -m "Add PR-Agent GitHub Action"
git push
```

That's it! PR-Agent will now run on every PR.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    PR Opened / Updated                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions Workflow Triggers               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 PR-Agent CLI (cli.py)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Fetch Diff  │→ │ Run Agents  │→ │ Format Results      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Post Comment to Pull Request                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Triggers

The workflow runs on:

| Event                       | When                     |
| --------------------------- | ------------------------ |
| `pull_request: opened`      | New PR created           |
| `pull_request: synchronize` | PR updated (new commits) |
| `pull_request: reopened`    | Closed PR reopened       |
| `workflow_dispatch`         | Manual trigger           |

---

## Using Labels to Control Behavior

Add labels to your PR to control what analysis runs:

| Label                    | Action                         |
| ------------------------ | ------------------------------ |
| (no label)               | Code review only               |
| `pr-agent:describe`      | Generate PR description        |
| `pr-agent:improve`       | Code improvement suggestions   |
| `pr-agent:changelog`     | Generate changelog             |
| `pr-agent:all`           | Run all analyses               |
| `pr-agent:comprehensive` | Detailed review (separate job) |

---

## Manual Trigger

You can manually run PR-Agent from the Actions tab:

1. Go to **Actions** → **PR-Agent Review**
2. Click **Run workflow**
3. Enter:
   - PR number
   - Action (review/describe/improve/changelog/all)
4. Click **Run workflow**

---

## CLI Usage

You can also run PR-Agent locally:

```bash
# Review a PR
python cli.py --action review --pr-number 123 --repo owner/repo

# Generate description
python cli.py --action describe --pr-url https://github.com/owner/repo/pull/123

# Run all analyses and post comment
python cli.py --action all --pr-number 123 --repo owner/repo --post-comment

# Verbose output
python cli.py --action review --pr-number 123 --repo owner/repo -v
```

### CLI Options

| Option           | Description                               |
| ---------------- | ----------------------------------------- |
| `--action`       | review, describe, improve, changelog, all |
| `--pr-number`    | PR number to analyze                      |
| `--pr-url`       | Full PR URL (alternative)                 |
| `--repo`         | Repository (owner/repo)                   |
| `--post-comment` | Post results to PR                        |
| `--output`       | markdown, json, text                      |
| `-v, --verbose`  | Verbose output                            |

---

## Customization

### Change LLM Provider

Set the `LLM_PROVIDER` repository variable:

```yaml
env:
  LLM_PROVIDER: anthropic # or openrouter
```

### Modify Workflow Triggers

Edit `.github/workflows/pr-agent.yml`:

```yaml
on:
  pull_request:
    types: [opened] # Only on new PRs
    branches:
      - main # Only PRs targeting main
```

### Skip Analysis

Add `[skip pr-agent]` to your commit message to skip analysis.

---

## Troubleshooting

### "API key not found"

- Ensure secrets are added in repository settings
- Check secret names match exactly

### "Rate limit exceeded"

- OpenAI: Check usage at platform.openai.com
- Use a model with higher limits
- Add delays between analyses

### "Permission denied"

- Workflow needs `pull-requests: write` permission
- For forks, analysis only runs on repo PRs (security)

### Check Logs

1. Go to **Actions** tab
2. Click the failed run
3. Expand job steps to see details

---

## Security Notes

1. **Fork PRs**: By default, workflow doesn't run on PRs from forks (secrets not available)
2. **Token Scope**: Uses `GITHUB_TOKEN` with minimal required permissions
3. **API Keys**: Stored as encrypted secrets, never logged

---

## Cost Estimation

| Model                  | Est. Cost per Review |
| ---------------------- | -------------------- |
| GPT-4o-mini            | ~$0.01-0.05          |
| GPT-4                  | ~$0.10-0.50          |
| Claude 3.5 Sonnet      | ~$0.05-0.20          |
| OpenRouter (free tier) | $0.00                |

_Depends on PR size and analysis type_
