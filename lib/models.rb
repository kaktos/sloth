require 'kramdown'
require 'dm-core'
require 'dm-validations'
require 'appengine-apis/datastore'

# Configure DataMapper to use the App Engine datastore 
DataMapper.setup(:default, "appengine://auto")
#Pluralized default engity name is deprecated on App Engine
DataMapper.repository.adapter.singular_naming_convention!

class Post
  include DataMapper::Resource
  property :id,               Serial
  property :author,           Email
  property :last_updated_by,  Email
  property :title,            String
  property :slug,             String
  property :body,             Text
  property :body_html,        Text
  property :published,        Boolean
  property :tags,             List
  property :published_at,     Time
  property :created_at,       Time, :default => lambda { |r, p| Time.now } # must be a Proc 
  property :updated_at,       Time  
  
  validates_presence_of :title, :slug, :body
  validates_uniqueness_of :slug

  before :valid? do
    self.slug = self.title.dup if (self.slug.blank?)
    self.slug = self.slug.to_url
    do_tags   
  end

  before :save do    
    if new? # for new create
      self.author = AppEngine::Users.current_user.email      
    else # for update
      self.last_updated_by = AppEngine::Users.current_user.email
      self.updated_at = Time.now
    end    
    self.published_at = Time.now if self.published
    self.body_html = Kramdown::Document.new(self.body).to_html
  end 

 
  def url
    "/posts/#{created_at.strftime("%Y/%m/%d")}/#{slug}"
  end  
  
  def full_url
    AppSettings.base_url.gsub(/\/$/, '') + url
  end
  
  def short_body
    short_body ||= self.body_html.match(/(<p>.+?<\/p>)/m)
    short_body || self.body_html
  end 
  
  
  def self.draft_count
    #todo: make in memcach
    q = AppEngine::Datastore::Query.new('Post')
    q.filter(:published, AppEngine::Datastore::Query::Constants::EQUAL, false)
    q.count
  end  
  
  private
  def do_tags  
    if self.tags.blank?
      self.tags = []
    else      
      self.tags = self.tags.split(",").reject{|tag| tag !~ /\S/}
      self.tags = self.tags.map {|tag| tag.downcase.strip.gsub(/\s+/,"-")}
      self.tags.uniq!                     
    end 
  end
 
end




#class Tag
#  include DataMapper::Resource
#  property :name,      String, :key => true
#  property :count,     Integer
#end


