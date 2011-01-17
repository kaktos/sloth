require 'appengine-rack'
require 'sinatra'
require 'stringex'
require 'yaml'
require 'ostruct'
require 'builder'
require 'appengine-apis/users'
require 'appengine-apis/logger'

require 'lib/content_for'
require 'lib/models'
require 'lib/core_ext'
require 'lib/paginator'

PAGE_SIZE = 5
PUBLIC_POSTS_MEM_KEY = 'PUBLIC_POSTS'

# CONFIGURATIONS --------------------------------------------------------------------------------------------------
configure do
  enable :method_override
  AppSettings = OpenStruct.new(YAML.load_file("settings.yml"))
end

configure :development do |cfg|
  #require 'sinatra/reloader'
  #cfg.also_reload "lib/models.rb"
end

configure :production do
  error do
    "You have errors: \n" + request.env['sinatra.error'].message + "\n" + request.env['sinatra.error'].backtrace.join("\n")
  end
end


# HELPERS --------------------------------------------------------------------------------------------------
helpers do
  def admin?
    AppEngine::Users.current_user && AppSettings.admins.include?(AppEngine::Users.current_user.email)
  end
  
  def authenticate!
    redirect AppEngine::Users.create_login_url(request.url) unless AppEngine::Users.current_user
    halt(401, "Not authorized") unless AppSettings.admins.include?(AppEngine::Users.current_user.email)
  end
  
  def post_path(post)
    if post.saved?
      "/posts/#{post.id}"
    else
      "/posts"
    end
  end
  
  def tag_links(post)
     bf = []
    (post.tags||[]).each do |tag|
      bf << "<a href='/tags/#{tag}'>#{tag}</a>"    
    end
    bf.join(", ")
  end
end

# FILTERS --------------------------------------------------------------------------------------------------
#before do  
#end


# HANDLERS --------------------------------------------------------------------------------------------------
get '/login' do
  redirect AppEngine::Users.create_login_url("/")
end

get '/logout' do
  redirect AppEngine::Users.create_logout_url(AppEngine::Users.create_login_url("/"))
end

get '/' do
  #@posts = Post.all(:order => [:published_at.desc], :published => true)
  query = AppEngine::Datastore::Query.new('Post').filter('published', AppEngine::Datastore::Query::EQUAL, true)
  query.sort :published_at, AppEngine::Datastore::Query::DESCENDING
  page = params[:page] ? params[:page].to_i : 1
  paginator = Paginator.new(query, PAGE_SIZE, PUBLIC_POSTS_MEM_KEY)
  result = paginator.fetch_page(page)
  @posts = Paginator.to_datamapper(result, Post)
  @has_next_page = paginator.has_page?(page + 1)
  @has_previous_page = (page > 1)
  erb :index
end

get '/posts/:year/:month/:day/:slug/?' do
  post = Post.first(:slug => params[:slug])
  halt 404, "Page not found"  unless post
  @title = post.title
  erb :posts_show, :locals => {:post => post }
end


get '/feed' do
  posts = Post.all(:order => [:published_at.desc], :published => true, :limit => 25)
  content_type 'application/atom+xml', :charset => 'utf-8'
  builder :feed, :locals => {:posts => posts, :xml => Builder::XmlMarkup.new }
end

get '/tags/:tag' do
  @posts = Post.all(:order => [:published_at.desc], :published => true, :tags => params[:tag])
  erb :tagged
end


# only for admin---------------------
get '/posts/new' do
  authenticate!
  @post = Post.new
  erb :post
end

post '/posts' do
  authenticate!
  @post = Post.create :title => params[:title], 
                       :slug => params[:slug], 
                       :tags => params[:tags], 
                       :body => params[:body], 
                       :published=> (params[:submit] == "post" ? true : false)
  if @post.saved?
    if @post.published
      redirect @post.url
    else
      redirect '/posts/draft' 
    end   
  else
    erb :post
  end    
end

get '/posts/:id/edit' do
  authenticate!
  @post = Post.get(params[:id])
  erb :post
end

put '/posts/:id' do
  authenticate!
  @post = Post.get(params[:id])
  if @post.update :title => params[:title], :slug => params[:slug], 
                  :tags => params[:tags], :body => params[:body], 
                  :published=> (params[:submit] == "post" ? true : false)
    redirect '/'
  else
    erb :post
  end  
end

delete '/posts/:id' do
  authenticate!
  post = Post.get(params[:id])
  post.destroy
  redirect '/'
end

get '/posts/draft' do
  authenticate!
  @drafts = Post.all(:published => false)
  erb :draft
end

