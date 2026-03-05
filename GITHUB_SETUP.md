# GitHub Setup Instructions

## Step 1: Create a GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right corner
3. Select **"New repository"**
4. Fill in the details:
   - **Repository name**: `claude-code-analytics` (or any name you prefer)
   - **Description**: "Analytics platform for Claude Code telemetry data"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **"Create repository"**

## Step 2: Push Your Code to GitHub

After creating the repository, GitHub will show you commands. Use these commands in your terminal:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/claude-code-analytics.git

# Rename branch to main (if needed)
git branch -M main

# Push your code
git push -u origin main
```

## Alternative: Using SSH (if you have SSH keys set up)

```bash
git remote add origin git@github.com:YOUR_USERNAME/claude-code-analytics.git
git branch -M main
git push -u origin main
```

## What Gets Pushed

✅ **Included:**
- All source code files
- README.md and documentation
- requirements.txt
- .gitignore

❌ **Excluded (by .gitignore):**
- `telemetry.db` (database file)
- `output/` directory (generated data files)
- `__pycache__/` (Python cache)
- `.streamlit/` (Streamlit config)
- Virtual environments

## After Pushing

Your repository will be live on GitHub! You can:
- Share the repository URL
- Clone it on other machines
- Set up CI/CD
- Add collaborators
- Create issues and pull requests
