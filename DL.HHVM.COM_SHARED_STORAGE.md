# dl.hhvm.com's Shared Storage

## What it is?

It is an AWS Elastic Block Store Volume (network block device) in us-west-2a;
it contains an XFS filesystem, and can only be mounted by one host at a
time.

In particular, it is usually mounted by our 'PublishBinaryPackages' jobs.

## Why does it exist?

Some tools need to operate on a local filesystem, such as `reprepro`, which
manages `apt` repository metadata for Debian and Ubuntu. `reprepro` in
particular needs a full copy of the filesystem.

This leads to two problems:
- As of 2022-03-30, it's roughly 2TB
- It is *really* slow to download this from S3; I once cancelled this after 6
  hours (when mounting had failed and failure wasn't handled properly) - 
  ompared to < 30 minutes for the usual run with the shared filesystem

In principle, our solution is:

1. We mount the shared filesystem
2. We use `aws s3 sync` to get the shared filesystem in sync with S3, using S3
  as the source of truth
3. We run the commands we need to do on this shared filesystem, e.g. adding
  `.deb` packages to the repositories and updating the metadata
4. We use `aws s3 sync` again copy from the shared filesystem to S3

We use a network block device and XFS instead of AWS's Elastic File System as
once mounted, the EBS+XFS approach works as if it were a local POSIX-compatible
filesystem.

## What's the new problem?

Hack/HHVM grow over time, and eventually the storage gets full.
While EBS and XFS are resizable, this is not automatic. It *could* be automated
by our tooling, however this is only needed every few years; it seems likely
automation would bitrot or have unintended side effects more than help.

## Making the shared storage larger

### Overview

1. Make the EBS Volume bigger - expand the existing volume, do not delete and recreate
1. Spin up an EC2 instance manually in the same availability zone as the volume,
   i.e. us-west-2a, not just us-west-2.
1. Attach the volume to the instance; can not be done while any other EC2 instance - such as a
   PublishBinaryPackages job - attached.
1. SSH to the EC2 instance
1. Find the device name for the block device - this may be in the EC2 web UI,
   otherwise check `dmesg` and `/var/log/cloud-init-output.log`
1. Use the standard XFS tools to non-destructively enlarge the filesystem
1. Mount the filesystem
1. Check `df -h` shows the expect results. For example, if you resize from 2TB
  to 4TB, you might expect to see a 4TB filesystem with 50% usage
1. `shutdown -h now`
1. Ensure that the EC2 instance is 'terminated' via the web UI. This probably
  happened automatically when the node was shut down

### Details

These instructions are accurate as of 2022-03-30, but depend on third-party
tools, APIs, and web interfaces; it is likely that it will not be possiible
to follow them verbatim the next time this needs doing - keepG the context above
in mind when following/adapting these instructions in the future.

1. Connect to the AWS management console
1. Set region to Oregon/us-west-2 in the top right
1. Go to EC2 from 'Services' in the top left
1. Under 'Elastic Block Store' on the left, select 'Volumes'
1. Select the 'dl.hhvm.com XFS' volume
1. In the top right, actions -> modify volume
1. Enter the new desired size. Historically, I've been doubling this each time.
1. Click modify
1. You should now be back to the EBS Volumes page; go to Instances -> Instances
  in the left navigation
1. Click 'launch instance' in the top right
1. Choose an image; as long as it's 64-bit x86 Linux, it doesn't really matter,
  but I'm using "Ubuntu Server 20.04 LTS". Click 'Select'.
1. Choose an instance type (machine class). The default is usually fine for
  this, but pick something bigger if that doesn't work. Click "Next: Configure Instance Details"
1. Change the Subnet to the us-west-2a subnet
1. Click "Next: Add Storage"
1. Increase the default root partition from the tiny default value to something
  reasonable. I go for 1024GiB which is unneccessarily large, but we're not
  going to keep this instance running for long.
1. You may get a warning about operating system support for large root volumes;
  this can be ignored on any recent Linux.
1. Click "Next: Add Tags"
1. Add a Name tag, e.g. `fredemmott-dev`; this shows up in the EC2 instance list
1. Click "Review and Launch"
1. You will get warnings about ssh being open to 0.0.0.0/0, and that it will not be free. Ignore these.
1. Click 'Launch'; you will be prompted to select an SSH key pair that you have access to, or create (and download) a new one. Either works.
1. Acknowldge the warning that you need the private key, then click 'Launch Instances'
1. Wait for it to start (instance state == "Running")
1. Go back to Elastic Block Store -> Volumes in the AWS Web UI
1. Select dl.hhvm.com XFS
1. Actions -> attach volume
1. Select your new instance
1. You may see an information box about device naming between kernels: as of
  2022-03-30, the value given to AWS should be of the form `/dev/sdf`, but it
  will be `/dev/xvdf` inside the instance. This applies to our use, but is
  informational - it does not require action.
1. Click 'attach volume'
1. ssh to your instance, e.g `ssh ubuntu@PUBLIC_IP` or `ssh ec2-user@PUBLIC_IP`
  for other imsages
1. Check the device exists, e.g. `ls /dev/xvdf` - there should usually be two
  devices, `/dev/xvda` and your device, `/dev/xvdf`. There will also likely be
  `/dev/xvda1` which is a partition of `/dev/xvda`. If it's unclear:
  - the "Attach" page in the web UI hopefully gave you the needed information
  - search current EBS documentation for the device names + AWS + EBS
  - check `mnt` to see which are in use
1. As of 2022-03-22 the required XFS utilities are installed by default, but if
  not, the package is usually called `xfsprogs` and should be installed with yum/apt/...
1. `mkdir /mnt/dl.hhvm.com; mount /dev/xvdf /mnt/dl.hhvm.com`  (changing device as  needed)
1. check `df -h` has the expected old size
1. Open `man xfs_growfs` **inside the VM** to check the version you are using has
  compatible arguments for all of the following command
1. run `xfs_growfs -d /dev/xvdf -n` - `-d` is to resize **D**ata section to max size, `-n` is 'no change to the filesystem is to be made' - i.e. dry-run
1. if the values look good, run again without `-n`: `xfs_growfs -d /dev/xvdf`
1. It should print out the new data size
1. Check `df -h` has the expected new size and usage
1. `umount /mnt/dl.hhvm.com`
1. double-check: `mount /dev/xvdf /mnt/dl.hhvm.com; df -h`
1. unmount again
1. shut the instance down: `shutdown -h now`
1. if shutting down the instance does not change the instance state to 'terminated' automatically, manually terminate it through the EC2 web ui
1. once the instance state is 'terminated' (not "shut down" or similar), the EBS volume will be automatically detached and can be used by other instances, e.g. the usual build jobs
1. re-run any publish jobs that failed

The volume can alternatively be attached from the AWS CLI, but you will need to configure AWS CLI credentials: https://github.com/hhvm/packaging/blob/fb50cf9db630e8b467488693bfcb6023f0455d9f/aws/bin/update-repos#L14-L23
