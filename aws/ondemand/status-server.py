# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import datetime
import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 4242))

while True:
  s.listen()
  conn, addr = s.accept()

  body = open(sys.argv[1], 'r').read()

  response = 'HTTP/1.1 200 OK\n'
  response += 'Connection: close\n'
  response += 'Content-Length: ' + str(len(body)) + '\n'
  response += 'Content-Type: text/plain\n'
  response += 'Date: ' + datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S') + ' GMT\n'
  response += 'Server: OnDemand Status Server\n'
  response += '\n'
  response += body

  conn.send(response.encode('utf-8'))
  conn.close()
