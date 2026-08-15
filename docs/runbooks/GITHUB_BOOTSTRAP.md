# GitHub bootstrap runbook

The repository is designed to be published as the private repository:

`bladerunner1984/oslt-research-engine`

## Why publication is a separate step

The research repository must not be created inside Serverity or inherit Serverity credentials. The
bootstrap script creates a new private repository from this directory, pushes `main`, and attempts to
protect `main` with the unique required status check `ci / check`.

## Windows PowerShell sequence

```powershell
winget install --id GitHub.cli

gh auth login

git config --global user.name "Mark Jennings"
git config --global user.email "YOUR_GITHUB_EMAIL"

Set-Location "C:\path\to\oslt-research-engine"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\scripts\bootstrap.ps1
.\scripts\publish-new-repo.ps1
```

The publication script:

1. verifies GitHub CLI authentication;
2. runs OSLT preflight and the complete test suite;
3. initialises `main` if necessary;
4. refuses to invent a Git author identity;
5. commits the complete intended tree;
6. creates or connects the private repository;
7. pushes `main`;
8. attempts branch protection requiring `ci / check`;
9. reports explicitly if plan/account settings require manual protection.

## Manual branch-protection fallback

In GitHub, open **Settings → Branches → Add branch protection rule** for `main` and enable:

- require a pull request before merging;
- require status checks to pass;
- require the unique check `ci / check`;
- require branches to be up to date;
- block force pushes and deletion;
- include administrators where available.

Do not add a second workflow job with the same `check` name. Required check names must remain unique.

## After first publication

All implementation work should use `agent/<description>` branches and draft pull requests. Direct
changes to `main` should be limited to the initial bootstrap needed to establish the protected
repository.
