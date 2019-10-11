from common import fake_ec2, skip_ec2

def lambda_handler(event, context=None):
  if skip_ec2(event) or fake_ec2(event):
    return False

  for version in event.get('results', {}).get('ForEachVersion', []):
    if 'success' in version.get('results', {}).get('PublishBinaryPackages', {}):
        return True

  return False
