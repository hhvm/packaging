'use strict';
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');


function get_version_info(event) {
  let version = event.version;
  if (!version) {
    const s = (new Date()).toISOString()
    version = s.slice(0,4)+'.'+s.slice(5, 7)+'.'+s.slice(8, 10);
  }
  const nightly = !! /^\d{4}(\.\d{2}){2}$/.exec(version);
  return {
    nightly,
    branch: nightly ? 'master' : ('HHVM-'+version.match(/^\d+\.\d+/)[0]),
    version: version
  };
}

function get_distros_uri(branch) {
  return 'https://raw.githubusercontent.com/hhvm/packaging/'
    + branch + '/CURRENT_TARGETS';
}

async function get_distros(branch) {
  const response = await rp(get_distros_uri(branch));
  return response.trim().split("\n");
}

exports.handler = async (event) => {
  const {nightly, version, branch} = get_version_info(event);

  const prefix = nightly ? 'hhvm-nightly-'+version : 'hhvm-'+version;
  const paths = {
    'macos-high_sierra':
      'homebrew-bottles/'+prefix+'.high_sierra.bottle.tar.gz',
    'macos-mojave':
      'homebrew-bottles/'+prefix+'.mojave.bottle.tar.gz',
  };
  if (nightly) {
    paths.source = 'source/nightlies/'+prefix+'.tar.gz';
    paths.source_gpg = 'source/nightlies/'+prefix+'.tar.gz.sig';
  } else {
    paths.source = 'source/'+prefix+'.tar.gz';
    paths.source_gpg = 'source/'+prefix+'.tar.gz.sig';
  }

  const distros = await get_distros(branch);
  for (const distro of distros) {
    const debianish = distro.match(/^(ubuntu|debian)/);
    if (debianish !== null) {
      paths[distro] = debianish[0] + '/pool/main/h/' +
        (nightly ? 'hhvm-nightly/hhvm-nightly_' : 'hhvm/hhvm_') +
        version + '-1~' + (distro.match(/[a-z]+$/)) + '_amd64.deb';
      continue;
    }
    // If we add a new distro kind without updating monitoring, make
    // the monitoring fail.
    paths[distro] = distro;
  }

  let success = true;
  let results = {};
  const s3 = new AWS.S3();
  await promise.all(
    Object.values(paths).map(async path => {
      try {
        await s3.headObject(
          { Bucket: 'hhvm-downloads', Key: path }
        ).promise();
        results[path] = true;
      } catch (err) {
        results[path] = false;
        success = false;
      }
    })
  );

  let response = { success, version, succeeded: [], failed: {} };
  for (const key in paths) {
    const path = paths[key];
    const success = results[path];
    if (success) {
      response.succeeded.push(key);
    } else {
      response.failed[key] = 'https://dl.hhvm.com/'+path;
    };
  }
  return response;
}
