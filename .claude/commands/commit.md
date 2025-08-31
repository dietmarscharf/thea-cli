---
allowed-tools: Task
argument-hint: [files to exclude, space-separated, wildcards supported]
description: Trigger git-commit-expert agent to analyze and commit changes
---

Use the git-commit-expert agent to handle all git commits.

Files to exclude from commit (if specified): $ARGUMENTS

The agent should:
1. Analyze all changes with git status and git diff
2. If exclusion patterns were provided, skip those files (supports wildcards like *.json, *.md, etc.)
3. Create logical, atomic commits from the remaining changes
4. Follow git commit best practices