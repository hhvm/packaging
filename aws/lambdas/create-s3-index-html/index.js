'use strict'
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

const AWS = require('aws-sdk');
const path = require('path');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const prettysize = require('prettysize');

const FOLDER_EMOJI = String.fromCodePoint(0x1F4C2);
const FILE_EMOJI = String.fromCodePoint(0x1F4C3);

function handle_s3_response(err, data, event, callback, acc) {
  if (err) {
    callback(err, data);
    return;
  }
  acc = acc.concat(data.Contents);
  if (data.IsTruncated) {
    const s3 = new AWS.S3();
    s3.listObjectsV2(
      { Bucket: event.bucket, ContinuationToken: data.NextContinuationToken },
      (err2, data2) =>
        handle_s3_response(err2, data2, event, callback, acc)
    );
    return;
  }

  publish_indices(event, acc, callback);
}

function publish_indices(event, objs, callback) {
  let dirs = new Set(['']);
  objs.forEach(obj => {
    let parts = obj.Key.split('/');
    parts.pop();
    while (parts.length > 0) {
      dirs.add(parts.join('/'));
      parts.pop();
    }
  });

  dirs = Array.from(dirs.values());

  const s3 = new AWS.S3();
  const s3_upload_promises = dirs.map(dir => s3.putObject({
      ContentType: 'text/html',
      Body: get_index_html_string(dir, objs),
      Bucket: event.bucket,
      Key: (dir+'/index.html').replace(/^\/+/, '')
  }).promise());
  Promise.all(s3_upload_promises).catch(err => callback(err)).then(data => {
    if (!event.cloudfront) {
      callback(null, data);
    }
    // Invalidate the CDN
    const cloudfront = new AWS.CloudFront();
    cloudfront.createInvalidation(
      {
        DistributionId: event.cloudfront,
        InvalidationBatch: {
          CallerReference: 's3-index-update-'+(new Date()).toISOString(),
          Paths: {
            Quantity: dirs.length,
            Items: dirs.map(
              dir => dir === '' ? '/' : ('/'+dir+'/')
            )
          }
        }
      },
      (err, data) => {
        try {
          const paths = data.Invalidation.InvalidationBatch.Paths.Items;
          if (paths.length > 17) {
            data.Invalidation.InvalidationBatch.Paths.Items = [
              ...paths.slice(0, 8),
              '-- truncated --',
              ...paths.slice(-8),
            ];
          }
        } catch (e) {}
        callback(err, data);
      }
    );
  }).catch(err => callback(err));
}

function get_index_html_string(dir, objs) {
  const parent_dir_row  = dir === '' ? null : (
    <tr key="parent"><td>{FOLDER_EMOJI} <a href={('/' + path.dirname(dir)).replace(/^\/.$/, '/')}>..</a></td></tr>
  );

  let files = [];
  let dirs = new Set();

  objs.forEach(obj => {
    if (path.dirname(obj.Key) === (dir === '' ? '.' : dir)) {
      if (path.basename(obj.Key) !== 'index.html') {
        files.push(obj);
      }
      return;
    }

    if (dir === '' || obj.Key.startsWith(dir + '/')) {
      const subdir = (dir === '' ? obj.Key : obj.Key.replace(dir+'/', '')).split('/')[0];
      dirs.add(subdir);
    }
  });

  const dir_rows = Array.from(dirs.values()).sort().map(subdir =>
    <tr key={subdir}><td>{FOLDER_EMOJI} <a href={subdir+'/'}>{subdir}/</a></td></tr>
  );

  const file_rows = files.sort(
    (a, b) => (a.Key < b.Key) ? -1 : 1
  ).map(item => {
    if (item.Size === 0) {
      console.log(item);
    }
    const basename = path.basename(item.Key);
    return (
      <tr key={item.Key}>
        <td>{FILE_EMOJI} <a href={basename}>{basename}</a></td>
        <td>{item.LastModified.toUTCString()}</td>
        <td>{prettysize(item.Size)}</td>
      </tr>
    );
  });

  const pretty_dir = dir === '' ? '/' : (dir + '/');

  const html_tree = (
    <html>
      <head>
        <meta charSet="UTF-8" />
        <title>{pretty_dir} - HHVM Downloads</title>
      </head>
      <body>
        <h1>HHVM Downloads</h1>
        <h2 style={{fontFamily: 'monospace'}}>{pretty_dir}</h2>
        <table style={{width: '100%', fontFamily: 'monospace'}}>
          {parent_dir_row}
          {dir_rows}
          {file_rows}
        </table>
        <footer style={{fontSize: 'x-small', fontStyle: 'italic', color: '#aaa', marginTop: '1em'}}>
          Generated at {(new Date()).toISOString()}
        </footer>
      </body>
    </html>
  );
  return ReactDOMServer.renderToStaticMarkup(html_tree);
}

exports.handler = (event, context, callback) => {
  if (!event.bucket) {
    callback('bucket must be specified');
    return;
  }

  const s3 = new AWS.S3();
  s3.listObjectsV2(
    { Bucket: event.bucket },
    (err, data) => handle_s3_response(err, data, event, callback, [])
  );
};
