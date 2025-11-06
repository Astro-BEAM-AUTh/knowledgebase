<!-- omit in toc -->
# How to Migrate to Organization Repos

New repos will be created under the organization for different components of the project.
But until then, the already existing repos have also been migrated to the organization.
This guide will help you migrate your local clones to point to the new organization repos.

<!-- omit in toc -->
## Table of Contents
- [VS Code Way](#vs-code-way)
- [Git/Terminal Way](#gitterminal-way)


## VS Code Way
1. Open the repository's project in VS Code.
2. Open the source control panel by clicking on the source control icon in the sidebar.
3. Click on the "..." (More Actions) button at the top of the source control panel.
4. Select "Remote" > "Add Remote..." from the dropdown menu.
5. Enter the new remote repository URL and give it a name (e.g., "organization").
   > You can find the new URL on the organization's GitHub repository page
   > eg: `https://github.com/Astro-BEAM-AUTh/ASTRO.git`
6. After adding the new remote, you can now push your changes to the new remote repository.
7. To switch between remotes, you can use the "..." (More Actions) button again and select "Remote" > "Fetch from..." or "Push to..." and choose the desired remote.

> **Note:** Bear in mind that after migration, you might want to remove the old remote if it's no longer needed. You can do this by clicking on the "..." (More Actions) button, selecting "Remote" > "Remove Remote..." and choosing the old remote (usually named "origin").

## Git/Terminal Way
1. Open your terminal or command prompt.
2. Navigate to the local repository you want to migrate.
3. Check the current remote URL by running:
   ```bash
   git remote -v
   ```
4. Add the new remote repository URL by running:
   ```bash
    git remote add organization <new-repo-url>
    ```
    Replace `<new-repo-url>` with the URL of the new organization repository.
    > You can find the new URL on the organization's GitHub repository page
    > eg: `https://github.com/Astro-BEAM-AUTh/ASTRO.git`
5. Verify that the new remote has been added by running:
   ```bash
    git remote -v
    ```
6. Push your changes to the new remote repository by running:
   ```bash
    git push organization main
    ```
    Replace `main` with the appropriate branch name if necessary.


> **Note:** Bear in mind that after migration, you might want to remove the old remote if it's no longer needed. You can do this by running:
```bash
    git remote remove origin
```