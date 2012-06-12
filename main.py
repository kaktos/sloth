#!/usr/bin/env python
# -*- coding: utf-8 -*-



import sys, os
package_dir = "lib"
package_dir_path = os.path.join(os.path.dirname(__file__), package_dir)
sys.path.insert(0, package_dir_path)

import bottle
from middlewares import MethodRewriteMiddleware
from app import handlers, config

app = bottle.default_app()
myapp = MethodRewriteMiddleware(app)

bottle.debug(config.DEV_MODE) # Only for debugging purposes, set to False in production
bottle.run(app = myapp, server = 'gae')

