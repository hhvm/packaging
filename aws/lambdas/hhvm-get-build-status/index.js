'use strict';
const AWS = require('aws-sdk');
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

  const maj_min = version.split('.').slice(0, 2).join('.');
  const macos_prefix = nightly
    ? 'hhvm-nightly-'+version
    : maj_min === '3.30'
      ? 'hhvm@3.30-lts-'+version
      : 'hhvm-'+maj_min+'-'+version;
  const src_prefix = nightly ? macos_prefix : ('hhvm-'+version);
  const paths = {
    'macos-high_sierra':
      'homebrew-bottles/'+macos_prefix+'.high_sierra.bottle.tar.gz',
    'macos-mojave':
      'homebrew-bottles/'+macos_prefix+'.mojave.bottle.tar.gz',
  };
  const scratch_paths = {};
  if (nightly) {
    paths.source = 'source/nightlies/'+src_prefix+'.tar.gz';
    paths.source_gpg = 'source/nightlies/'+src_prefix+'.tar.gz.sig';
  } else {
    paths.source = 'source/'+src_prefix+'.tar.gz';
    paths.source_gpg = 'source/'+src_prefix+'.tar.gz.sig';
    scratch_paths[paths.source] = src_prefix+'.tar.gz';
    scratch_paths[paths.source_gpg] = src_prefix+'.tar.gz.sig';
  }

  const distros = await get_distros(branch);
  for (const distro of distros) {
    const debianish = distro.match(/^(ubuntu|debian)/);
    if (debianish !== null) {
      const file_name = (nightly ? 'hhvm-nightly_' : 'hhvm_') +
        version + '-1~' + (distro.match(/[a-z]+$/)) + '_amd64.deb';
      const path = debianish[0] + '/pool/main/h/' +
        (nightly ? 'hhvm-nightly/' : 'hhvm/') + file_name;
      paths[distro] = path;
      scratch_paths[path] = version + '/' + distro + '/' + file_name;
      continue;
    }
    // If we add a new distro kind without updating monitoring, make
    // the monitoring fail.
    paths[distro] = distro;
  }

  let success = true;
  let results = {};
  const s3 = new AWS.S3();
  await Promise.all(
    Object.values(paths).map(async path => {
      try {
        await s3.headObject(
          { Bucket: 'hhvm-downloads', Key: path }
        ).promise();
        results[path] = 'success';
      } catch (err) {
        success = false;
        results[path] = 'failure';
        if (scratch_paths[path]) {
          try {
            await s3.headObject(
              { Bucket: 'hhvm-scratch', Key: scratch_paths[path] }
            ).promise();
            results[path] = 'unpublished';
          } catch (err) {
            // failure set already
          }
        }
      }
    })
  );

  let response = {
    success,
    version,
    succeeded: [],
    failed: {},
    built_not_published: [],
    not_built: {},
  };
  for (const key in paths) {
    const path = paths[key];
    const result = results[path];
    if (result === 'success') {
      response.succeeded.push(key);
      continue;
    } else {
      // Intentionally including 'unpublished' here: consider it failed if it's
      // not available for download.
      response.failed[key] = 'https://dl.hhvm.com/'+path;
    };

    if (result === 'unpublished') {
      response.built_not_published.push(key);
      continue;
    }
    response.not_built[key] = 'https://dl.hhvm.com/'+path;
  }
  return response;
}
