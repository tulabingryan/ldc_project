# Localized Demand Control Simulator


#### Misc. Notes
Git commands
- git status # check status of the repository
- git add -A  # add all changes to the repository to be commited
- git commit -m "comment"  # commit added changes with "comment as notes"
- git push  # push commited changes to the master HEAD at the cloud
- git log  # show all committed changes to the repo
- git reset --hard HEAD~1  # reset repo to latest 1 HEAD
- git rebase -i HEAD~6  # cancel last 6 commits by changing base up to 6 steps

To ignore certain files and folder create a file ".gitignore" and write the following
'''
\# folders to ignore
specs/
folder2/

\# files to ignore
file1.csv
file2.txt
'''