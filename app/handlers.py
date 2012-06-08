# -*- coding: utf-8 -*-

from flask import Flask, url_for, render_template, request, redirect, jsonify
from models import *
import config
from functools import wraps
import unidecode
import markdown
from datetime import datetime
from paging import PagedQuery

from google.appengine.api import users


###############################################################################
#                      decorator and view helpers                             #
###############################################################################
def login_required(func):
    """
    Decorator for checking if there's a admin user
    """
    @wraps(func)
    def check_login(*args, **kwargs):    	
        if not users.get_current_user() or not users.is_current_user_admin():
            abort(403)
        else:
            return func(*args, **kwargs)

    return check_login

    
def is_admin():
    return users.is_current_user_admin()

def current_user():
	return users.get_current_user()

def slugify(str):
    str = unidecode.unidecode(str).lower().strip()
    return re.sub(r'\W+','-',str)    


###############################################################################
#                     init                                                    #
###############################################################################
sloth_app = Flask(__name__)
sloth_app.config.from_object("app.config")
sloth_app.jinja_env.globals.update(app_config=config, current_user=current_user, is_admin=is_admin)

###############################################################################
#            controllers                                                      #
###############################################################################

#--------------------------------------------------------------------------------------------------
@sloth_app.route('/login', methods = ['GET'])
def login():
    user = users.get_current_user()
    if not user:        
        return redirect(users.create_login_url("/"))
    else:
        return redirect('/') 
               
@sloth_app.route('/logout', methods = ['GET'])    
def logout():
    return redirect(users.create_logout_url("/"))

#--------------------------------------------------------------------------------------------------    
@sloth_app.route('/')    
def index():
    current_page = int(request.args.get('page', 1))
    q = PagedQuery(Post.all(), 5)
    result = q.filter('published =', True).order('-published_at').fetch_page(current_page)
    has_next = q.has_page(current_page + 1)
    has_prev = q.has_page(current_page - 1)
    return render_template('index.html', posts=result, page = current_page, has_next = has_next, has_prev = has_prev) 
    
    

@sloth_app.route('/posts/new', methods = ['GET'])
@login_required
def post_new():
    context = {'post': Post(), 'categories' : Category.all().fetch(limit=None)}
    return render_template('post_edit.html', **context)

    
@sloth_app.route('/posts', methods = ['POST'])
@login_required
def post_create():
    p = Post()
    p.title = request.values.title
    p.slug = slugify(p.title)
    p.do_category(request.values.category)
    p.body = request.values.body
    p.body_html = markdown.markdown(p.body)
    if request.values['submit'] == 'post':
        p.published = True
        p.published_at = datetime.now()
        p.author = users.get_current_user().email()
    else:
        p.published = False
      
    p.put()
    return redirect("/")
  
@sloth_app.route('/posts/<year>/<month>/<day>/<slug>', methods = ['GET'])  
def post_show(year, month, day, slug):
    q = Post.all();                
    q.filter("slug = ", slug)        
    context = {'post': q.get()}
    return render_template('post_show.html', **context)
 

@sloth_app.route('/posts/<id>', methods = ['DELETE'])   
@login_required  
def post_destroy(id):
    p = Post.get_by_id(long(id))
    if p: p.delete()  
    return redirect("/")  



@sloth_app.route('/posts/<id>/edit', methods = ['GET'])
@login_required
def post_edit(id):
    post = Post.get_by_id(long(id))    
    context = {'post': post, 'categories' : Category.all().fetch(limit=None)}
    return render_template('post_edit.html', **context)  


@sloth_app.route('/posts/<id>', methods = ['PUT'])
@login_required
def post_update(id):
    p = Post.get_by_id(long(id))    
    p.title = request.values.title
    p.slug = slugify(p.title)
    p.do_category(request.values.category)
    p.body = request.values.body
    p.body_html = markdown.markdown(p.body)
    p.last_updated_by = users.get_current_user().email()
    if request.values['submit'] == 'post':
        p.published = True
        p.published_at = datetime.now()
    else:
        p.published = False
        
    p.put()
    return redirect("/")         
    

@sloth_app.route('/posts/draft', methods = ['GET'])
@login_required
def draft_posts():
    posts = Post.all().filter('published =', False).order("-updated_at").fetch(limit=None)
    return render_template('post_by.html', posts=posts) 

 

# @sloth_app.route('/categories.json', methods = ['GET'])
# def categories():
#     categories = Category.all().fetch(limit=None)
#     return jsonify(name=[category.name for category in categories])

@sloth_app.route('/posts/category/<category_id>', methods = ['GET'])
def categorified_post(category_id):
    c = Category.get_by_id(long(category_id)) 
    return render_template('post_by.html', posts=c.posts) 
   
    
    
    
    
    
    
    
    
