Sloth
=========
a Minimal Personal Writing System On GAE.  
Modern browsers are required to support the all **html5** and
**CSS3** features of the default template.

##Features
* Ruby powered(Sinatra, Datamapper), thanks the [JRuby on Google App Engine](http://code.google.com/p/appengine-jruby/);
* CSS3 and HTML5 goodness;
* Support Markdown markup; 
* Live preview what you'r writing. Inspired by [Blogcast](http://techoctave.com/blogcast/);
* SEO url for Unicode title(abc 囧->/abc-jiong);
* Comment system using [DISQUS](http://disqus.com/);
* No admin dashboard :);


##Installation  
	git clone git://github.com/shuhao/sloth  
	cd sloth

make sure you have ruby **MRI 1.8.7** installed in your system.  
install the all-in-one SDK for jruby on GAE  

	gem install google-appengine


install bundled gems:  

	appcfg.rb bundle .	


##Config

	mv settings.yml.sample settings.yml
	mv WEB-INF/app.yaml.sample WEB-INF/app.yaml

modify settings.yml with your customized settings,
such as blog tile,disqus shorname, make sure add your gmail address 
as admins;   
modify app.yaml with your applied GAE appid.

##Run dev server
    #this command will auto-download the bundled gems
	 for you and after that, launch the server
	dev_appserver.rb .

open http://localhost:8080 to see.  
click the name on page bottom to login, or directly open http://localhost:8080/login


##Upload

	appcfg.rb upload .


##Codes
* Some codes copy from [Scanty](https://github.com/adamwiggins/scanty)
* Buiding on [JRuby On GAE](http://code.google.com/p/appengine-jruby/)
* Using the simple ruby web framework [Sinatra](http://sinatrarb.com)
* Javascript libraries: [Markdown in Javascript ](http://attacklab.net/showdown/), [Textarea Auto Resize](http://www.unwrongest.com/projects/elastic/)
* Iconset [iconic](http://somerandomdude.com/projects/iconic/)

##TODOs

* pagination
* tag count


##Copyright

