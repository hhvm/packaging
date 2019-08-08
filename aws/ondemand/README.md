# ondemand

Helper scripts to set up automatic GitHub checkouts on AWS EC2.

`bootstrap.sh` is the entry point (to be called from the EC2 instance's "user data" script). Most of the actual code is in `main.sh` (runs as root) and `user.sh` (runs as a regular user).

Note: `.sh` files are executable and called directly. `.inc.sh` are non-executable and are always `source`d from the former.

## Per-repository init scripts

Directory structure follows GitHub's organization/repository structure. Each directory (both organization parent directory and repository subdirectory) may contain:

- `packages.inc.sh`: should set the shell variable `PACKAGES` to the list of deb packages that need to be installed
- `root.inc.sh`: will be `source`d at the end of `main.sh` (i.e., runs as root)
- `user.inc.sh`: will be `source`d at the end of `user.sh` (i.e., runs as regular user)

All of this is optional, there doesn't need to be a directory for any organization/repository that doesn't need custom initialization code.

## Config

The EC2 instance's "user data" script is responsible for writing `config.inc.sh` that sets all the required shell variables:

- `TEAM`: GitHub organization name (e.g. `hhvm`) for the repository that will be cloned
- `REPO`: name of the GitHub repository (e.g. `user-documentation`) that will be cloned
- `GITHUB_USER`: the user whose fork will be set as git's remote
- `GIT_NAME` (for `git commit`)
- `GIT_EMAIL` (for `git commit`)
- `SSH_KEYS`: will be appended to `~/.ssh/authorized_keys` (separated by `\n` -- actual 2 characters, not a newline character)

## Other stuff

- `status-server.py` is a trivial daemon that dumps the current status info on anyone that connects to port 4242
- `motd.sh` is called from the user's `.bashrc`, should contain any information that should be printed out on every login
- `common.inc.sh` is `source`d from all scripts

## Example EC2 "user data"

```bash
#!/bin/bash
curl -L https://github.com/hhvm/packaging/tarball/master | tar xz
mv *packaging*/aws/ondemand /home/ubuntu/.ondemand
echo '
  TEAM="%s"
  REPO="%s"
  GITHUB_USER="%s"
  GIT_NAME="%s"
  GIT_EMAIL="%s"
  SSH_KEYS="%s"
' > /home/ubuntu/.ondemand/config.inc.sh
/home/ubuntu/.ondemand/bootstrap.sh
```
