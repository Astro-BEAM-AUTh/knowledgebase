<!-- omit in toc -->
# Software Guidelines & Conventions

<!-- omit in toc -->
## Table of Contents
- [Branching Pattern](#branching-pattern)
- [Workflow Example](#workflow-example)
- [Commit Conventions](#commit-conventions)
- [Repository Standards](#repository-standards)

## Branching Pattern

**1. Main Branches**
- `main`
  - Always stable
  - Only production-ready code (releases, deploys)
- `develop`
  - The integration branch for ongoing work
  - All features, fixes, and enhancements are merged here first
  - Periodically, changes from develop are merged into main for releases

**2. Feature Branches**
- Created from `main` or `develop` (depending on the task and whether the latest dev changes are needed)
- For new features, tasks, or enhancements
- Naming: `feature/<short-description>` or `feature/<automated-issue-branch-name>`
- *Example*: `feature/html-report`, `feature/1-postgres-support`

**3. Bugfix Branches**
- Created from `main` or `develop` (depending on where the bug exists)
- For fixing bugs
- Naming: `bugfix/<short-description>`
- *Example*: `bugfix/cli-arg-parsing`, `bugfix/html-template`

## Workflow Example

**1. Start a Feature**
- Create branch using the issue's automatic branch creation system (if an issue on GitHub exists) or by yourself using:
> `git checkout develop && git checkout -b feature/html-report`
- Work on your feature and push commits.

**2. Collaborate**
- Push your branch to GitHub
> `git push origin feature/html-report`
- Open a Pull Request from your feature branch --> `develop`.
- Set others as reviewers. (at least one approval would be ideal)
- Reviewers comment and verify that the changes should be merged into `develop`

**3. Release**
- When `develop` is ready, merge it into `main` (via a PR).
- Optionally, use a release branch for final polish.

**4. Hotfix**
- If a bug is found in "production", create a `hotfix` branch from `main`.
- After fixing, merge `hotfix` into both `main` and `develop`.


## Commit Conventions
Follow Angular [Conventional Commits](https://www.conventionalcommits.org/)

Format:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: A new feature (triggers minor version bump)
- `fix`: A bug fix (triggers patch version bump)
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance (triggers patch version bump)
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools
- `ci`: Changes to CI configuration files and scripts
- `deps`: Changes to dependencies


**Examples:**
```bash
feat: add theme support with --theme option
fix: resolve dependency parsing error with special characters
docs: update README with new theme examples
chore: update dependencies to latest versions
```

**BREAKING CHANGES:**
For breaking changes, add `!` after the type or include `BREAKING CHANGE:` in the footer:
```bash
feat!: change CLI interface for better usability
# or
feat: change CLI interface

BREAKING CHANGE: --output-format flag renamed to --format
```

```bash
git commit -m "feat: add your new feature description"
git push origin 123-add-a-feature
```

## Repository Standards
Every repository should include:
- `README.md` - Purpose, setup instructions, and dependencies.  
- `CONTRIBUTING.md` - Guidelines for code style, testing, and PRs.  
- `docs/` - Diagrams, architecture notes, or relevant technical papers.  
- CI workflow under `.github/workflows/`.
