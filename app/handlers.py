# -*- coding: utf-8 -*-

from bottle import route, redirect, request, url, abort, template as base_template, get, post, put, delete, install
from models import *
import config, bottleext
import functools
import unidecode
import markdown
from datetime import datetime
from paging import PagedQuery
import logging

from google.appengine.api import users


###############################################################################
#                      decorator and view helpers                             #
###############################################################################
def user_required(handler):
    """
    Decorator for checking if there's a admin user
    """

    def check_login(*args, **kwargs):    	
        if not users.get_current_user() or not users.is_current_user_admin():
            abort(403)
        else:
            return handler(*args, **kwargs)

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
settings = dict(globals = {"app_config":config, "current_user" : current_user, "is_admin" : is_admin, "url_for" : url})
template = functools.partial(base_template, 
                             template_adapter=bottleext.MyJinja2Template, 
                             template_settings=settings,
                             template_lookup=["./app/templates"]) 


install(bottleext.JSONAPIPlugin())       

                     
###############################################################################
#            controllers                                                      #
###############################################################################

#--------------------------------------------------------------------------------------------------
@get('/login')
def login():
    user = users.get_current_user()
    if not user:        
        redirect(users.create_login_url("/"))
    else:
        redirect('/') 
               
@get('/logout')    
def logout():
    redirect(users.create_logout_url("/"))

#--------------------------------------------------------------------------------------------------    
@get('/')    
def index():
    current_page = int(request.query.page) if request.query.page else 1
    q = PagedQuery(Post.all(), 5)
    result = q.filter('published =', True).order('-published_at').fetch_page(current_page)
    has_next = q.has_page(current_page + 1)
    has_prev = q.has_page(current_page - 1)
    return template('index.html', posts=result, page = current_page, has_next = has_next, has_prev = has_prev) 
    
    

@get('/posts/new', name="new_post_path")
@user_required
def post_new():
    context = {'post': Post(), 'categories' : Category.all()}
    return template('post_edit.html', **context)

    
@post('/posts', name = "posts_path")
@user_required
def post_create():
    p = Post()
    p.title = request.params.title
    p.slug = slugify(p.title)
    #p.do_tags(request.params.tags)
    p.do_category(request.params.category)
    p.body = request.params.body
    p.body_html = markdown.markdown(p.body)
    if request.params['submit'] == 'post':
        p.published = True
        p.published_at = datetime.now()
        p.author = users.get_current_user().email()
    else:
        p.published = False
      
  
    p.put()
    redirect("/")
  
@get('/posts/<year:re:\d{4}>/<month:re:\d{2}>/<day:re:\d{2}>/<slug>', name = "post_path")  
def post_show(year, month, day, slug):
    q = Post.all();                
    q.filter("slug = ", slug)        
    context = {'post': q.get()}
    return template('post_show.html', **context)
 

@delete('/posts/<id>', name = "delete_post_path")   
@user_required  
def post_destroy(id):
    p = Post.get_by_id(long(id))
    if p: p.delete()  
    redirect("/")  



@get('/posts/<id>/edit', name = "edit_post_path")
@user_required
def post_edit(id):
    post = Post.get_by_id(long(id))    
    context = {'post': post}
    return template('post_edit.html', **context)  


@put('/posts/<id>', name = "post_path")
@user_required
def post_update(id):
    #logging.info("category param is %s", request.params['category'])
    p = Post.get_by_id(long(id))    
    p.title = request.params.title
    p.slug = slugify(p.title)
    #p.do_tags(request.params.tags)
    p.do_category(request.params.category)
    p.body = request.params.body
    p.body_html = markdown.markdown(p.body)
    p.last_updated_by = users.get_current_user().email()
    if request.params['submit'] == 'post':
        p.published = True
        p.published_at = datetime.now()
    else:
        p.published = False
        
  
    p.put()
    redirect("/")         
    

@get('/posts/draft', name = "draft_posts_path")
@user_required
def draft_posts():
    posts = Post.all().filter('published =', False).order("-updated_at").fetch(limit=None)
    return template('post_by.html', posts=posts) 

#--------------------------------------------------------------------------------------------------
@get('/categories.json')
def categories():
    categories = Category.all().fetch(limit=None)
    return [category.name for category in categories]

@get('/posts/category/<category_id>', name = "category_posts_path")
def categorified_post(category_id):
    #logging.info("category name is %s", category_name)
    c = Category.get_by_id(long(category_id)) 
    return template('post_by.html', posts=c.posts) 
    
    
    
    
    
    
    
    
    
