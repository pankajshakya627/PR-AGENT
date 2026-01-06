# PR-Agent Portable Workflow

Use PR-Agent in **any repository** with just ONE file!

## Quick Setup (2 Minutes)

### Step 1: Copy the Workflow

Copy `pr-agent-portable.yml` to your repository:

```bash
# In your target repository
mkdir -p .github/workflows
curl -o .github/workflows/pr-agent.yml \
  https://raw.githubusercontent.com/pankajshakya627/PR-AGENT/main/.github/workflows/pr-agent-portable.yml
```

Or manually download from:

- [pr-agent-portable.yml](https://github.com/pankajshakya627/PR-AGENT/blob/main/.github/workflows/pr-agent-portable.yml)

### Step 2: Add Secrets

Go to your repository **Settings → Secrets and variables → Actions → New repository secret**

| Secret               | Required         | Provider          |
| -------------------- | ---------------- | ----------------- |
| `GROQ_API_KEY`       | ✅ (recommended) | Groq (free, fast) |
| `OPENROUTER_API_KEY` | Optional         | OpenRouter        |
| `OPENAI_API_KEY`     | Optional         | OpenAI            |
| `ANTHROPIC_API_KEY`  | Optional         | Anthropic         |

> At least ONE API key is required.

### Step 3: Done! 🎉

PRs will be automatically reviewed when opened or updated.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Your Repository (target-org/target-repo)                   │
│  └── .github/workflows/pr-agent-portable.yml                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Runner                                      │
│  1. Clones pankajshakya627/PR-AGENT                         │
│  2. Installs dependencies                                   │
│  3. Runs PR analysis                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PR Comment Posted with Review Results                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Triggers

| Event                       | When                            |
| --------------------------- | ------------------------------- |
| `pull_request: opened`      | New PR created                  |
| `pull_request: synchronize` | PR updated with new commits     |
| `pull_request: reopened`    | Closed PR reopened              |
| `workflow_dispatch`         | Manual trigger from Actions tab |

---

## Manual Trigger

1. Go to **Actions** tab in your repository
2. Select **PR-Agent Review**
3. Click **Run workflow**
4. Configure:
   - **PR number**: Which PR to analyze
   - **Action**: `review`, `describe`, `improve`, `changelog`, or `all`
   - **Provider**: `groq`, `openrouter`, `openai`, or `anthropic`
   - **Model**: Select from dropdown

---

## Available Actions

| Action      | Description                                          |
| ----------- | ---------------------------------------------------- |
| `review`    | Code review with issues, suggestions, security notes |
| `describe`  | Generate PR title and description                    |
| `improve`   | Code improvement and refactoring suggestions         |
| `changelog` | Generate changelog entry                             |
| `all`       | Run all analyses                                     |

---

## Supported Models

### Groq (Recommended - Fast & Free)

- `llama-3.1-8b-instant` (default)
- `llama-3.3-70b-versatile`

### OpenRouter

- `xiaomi/mimo-v2-flash:free` (default)
- `google/gemini-2.0-flash-exp:free`

### OpenAI

- `gpt-4o-mini`
- `gpt-4o`

### Anthropic

- `claude-sonnet-4-5-20250929`

---

## Provider Fallback

If the selected provider fails, PR-Agent automatically tries the next available:

```
groq → openrouter → openai → anthropic
```

---

## Troubleshooting

### "API key not found"

- Ensure secrets are added in repository settings
- Check secret names match exactly (case-sensitive)

### "No models provided"

- Select a model from the dropdown when running manually
- Or ensure default model is set in workflow

### "Permission denied"

- Workflow needs `pull-requests: write` permission
- For private repos, ensure `GITHUB_TOKEN` has access

### Fork PRs

- By default, workflow doesn't run on PRs from forks (security)
- Fork users need to trigger manually after merge

---

## Customization

### Change Default Provider

Edit the workflow file in your repo:

```yaml
env:
  LLM_PROVIDER: ${{ inputs.provider || 'openrouter' }} # Change default here
```

### Change PR-Agent Source

To use a different branch or fork:

```yaml
env:
  PR_AGENT_REPO: "your-fork/PR-AGENT"
  PR_AGENT_BRANCH: "your-branch"
```

---

## Cost Estimation

| Provider   | Model                     | Est. Cost/Review |
| ---------- | ------------------------- | ---------------- |
| Groq       | llama-3.1-8b-instant      | Free             |
| OpenRouter | xiaomi/mimo-v2-flash:free | Free             |
| OpenAI     | gpt-4o-mini               | ~$0.01-0.05      |
| Anthropic  | claude-sonnet             | ~$0.05-0.20      |

---

## Security Notes

1. **API Keys**: Stored as encrypted secrets, never exposed in logs
2. **Fork PRs**: Disabled by default to protect secrets
3. **Token Scope**: Uses minimal required permissions

---

## Get API Keys

| Provider   | Get Key                              |
| ---------- | ------------------------------------ |
| Groq       | https://console.groq.com/keys        |
| OpenRouter | https://openrouter.ai/keys           |
| OpenAI     | https://platform.openai.com/api-keys |
| Anthropic  | https://console.anthropic.com/keys   |
