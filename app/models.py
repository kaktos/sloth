# -*- coding: utf-8 -*-

'''
model class 
'''
from google.appengine.ext import db
from datetime import datetime
import re
import logging



class Category(db.Model):
    name            = db.StringProperty()
    created_at      = db.DateTimeProperty(auto_now_add=True)


class Post(db.Model):
    author          = db.EmailProperty()
    last_updated_by = db.EmailProperty()
    title           = db.StringProperty()
    slug            = db.StringProperty()
    body            = db.TextProperty()
    body_html       = db.TextProperty()
    published       = db.BooleanProperty()
    published_at    = db.DateTimeProperty()
    created_at      = db.DateTimeProperty(auto_now_add=True)
    updated_at      = db.DateTimeProperty(auto_now=True)
    
    # tags            = db.StringListProperty(default=[]) 
    category        = db.ReferenceProperty(Category, collection_name='posts')

    #ptag_regex = re.compile("<p>.*?<\/p>", re.DOTALL)
     
    @property
    def url(self):
        return "/posts/%s/%s" % (self.published_at.strftime("%Y/%m/%d"), self.slug)
        
    @property    
    def summary(self):        
        pos = self.body_html.find("</p>")
        if pos == -1:
            return self.body_html
        else:
            return self.body_html[:pos+4]

    # def do_tags(self, raw_tags):
    #     if raw_tags:            
    #         self.tags = [re.sub(r'\s+','-',t.strip()) for t in raw_tags.split(",")]
    #         for tag_name in self.tags:
    #             tag = Tag(key_name = tag_name) 
    #             tag.put()  
                
    def do_category(self, cat_name):
        if cat_name:
            category = Category.all().filter('name = ', cat_name).get()
            if not category:
                   category = Category(name = cat_name)          
                   category.put()
            self.category = category
        else:
            self.category = None    


# class Tag(db.Model):
#     created_at      = db.DateTimeProperty(auto_now_add=True)

#     @property
#     def posts(self):
#         return Post.gql("WHERE tags = :1", self.key().name())