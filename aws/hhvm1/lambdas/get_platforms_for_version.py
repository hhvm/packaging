from common import fetch

def lambda_handler(event, context=None):
  platforms = fetch('CURRENT_TARGETS', event['version']).strip().split('\n')

  if event['buildInput']['platforms']:
    platforms = [p for p in platforms if p in event['buildInput']['platforms']]

  return platforms
