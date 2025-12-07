# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in PR-Agent, please report it responsibly:

1. **DO NOT** open a public issue
2. Email: [your-email@example.com] with details
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to resolve the issue.

---

## Security Best Practices

### For Users

1. **API Keys**: Never commit API keys to your repository
2. **Secrets**: Always use GitHub Secrets for sensitive data
3. **Fork PRs**: Workflow is disabled for fork PRs by default (security)
4. **Token Scope**: Use minimum required permissions for `GITHUB_TOKEN`

### Environment Variables

| Variable             | Security Level | Storage              |
| -------------------- | -------------- | -------------------- |
| `GITHUB_TOKEN`       | High           | GitHub auto-provided |
| `OPENAI_API_KEY`     | High           | Repository Secrets   |
| `GROQ_API_KEY`       | High           | Repository Secrets   |
| `OPENROUTER_API_KEY` | High           | Repository Secrets   |
| `ANTHROPIC_API_KEY`  | High           | Repository Secrets   |

---

## Security Features

### Enabled

- ✅ **Dependabot**: Automatic dependency updates
- ✅ **Secret Scanning**: Prevents accidental secret commits
- ✅ **Code Scanning**: CodeQL analysis on PRs
- ✅ **Branch Protection**: Required reviews for main branch

### Workflow Security

- Fork PRs are blocked from running workflows (prevents secret exposure)
- Minimal permissions (`contents: read`, `pull-requests: write`)
- No external action dependencies except verified ones

---

## Dependency Management

Dependencies are pinned and regularly updated:

```yaml
# Dependabot configuration
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Code Security Measures

1. **Input Validation**: All user inputs are validated
2. **No Eval/Exec**: No dynamic code execution
3. **Logging**: Sensitive data is never logged
4. **Error Handling**: Errors don't expose internal details

---

## Access Control

This repository uses a **proprietary license**. Usage requires:

1. Written permission from the owner
2. Compliance with the license terms
3. No redistribution without authorization

See [LICENSE](LICENSE) for details.

---

## Supported Versions

| Version | Supported     |
| ------- | ------------- |
| main    | ✅            |
| develop | ⚠️ (unstable) |
| < 1.0   | ❌            |

---

## Security Checklist for Contributors

- [ ] No hardcoded secrets
- [ ] No sensitive data in logs
- [ ] Input validation for all user inputs
- [ ] Error messages don't expose internals
- [ ] Dependencies are from trusted sources
- [ ] No use of `eval()` or `exec()`
