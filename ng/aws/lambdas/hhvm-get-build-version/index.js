'use strict'

exports.handler = (event, context, callback) => {
  if (event.version) {
    callback(null, { version: event.version });
  }
  const s = (new Date()).toISOString()
  const version = s.slice(0,4)+'.'+s.slice(5, 7)+'.'+s.slice(8, 10);
  callback(null, { version: version });
}
