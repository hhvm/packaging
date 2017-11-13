'use strict'

exports.handler = (event, context, callback) => {
  let version = event.version;
  if (!version) {
    const s = (new Date()).toISOString()
    version = s.slice(0,4)+'.'+s.slice(5, 7)+'.'+s.slice(8, 10);
  }
  const nightly = !! /^\d{4}(\.\d{2}){2}$/.exec(version);
  const source = nightly
    ? {
      bucket: 'hhvm-downloads',
      path: 'source/nightlies/hhvm-nightly-'+version+'.tar.gz'
    }
    : {
      bucket: 'hhvm-scratch',
      path: 'hhvm-'+version+'.tar.gz'
    };
  event.version = version;
  event.nightly = nightly;
  event.source = source;

  callback(null, event);
}
