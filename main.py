#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
package_dir = "lib"
package_dir_path = os.path.join(os.path.dirname(__file__), package_dir)
sys.path.insert(0, package_dir_path)


from middlewares import MethodRewriteMiddleware
from google.appengine.ext.webapp.util import run_wsgi_app
from app import handlers


myapp = MethodRewriteMiddleware(handlers.sloth_app)
run_wsgi_app(myapp)