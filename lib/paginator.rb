# from https://github.com/joshsmoore/appengine-paginator and
# http://code.google.com/p/he3-appengine-lib/wiki/PagedQuery

require 'appengine-apis/memcache'

#
# Two values store into memcache,
# one is the page cursor, the second
# is the query count
# 
class Paginator
  attr_reader :query, :page_size, :query_mem_key

  # creates a paginator object
  # * query - an instance of AppEngine::Datastore::Query
  # * page_size - number of items per page
  # * query_mem_key - memcache key of this type of query 
  def initialize(query, page_size, query_mem_key)
    @query   = query
    @page_size   = page_size
    @query_mem_key = query_mem_key
    @page_cursors = AppEngine::Memcache.new.get(@query_mem_key) || {}
    @last_page_cursors = @page_cursors.dup
    @query_count = AppEngine::Memcache.new.get("#{@query_mem_key}_COUNT")
  end

  def fetch_page(page_num = 1)      
    fetchOptions = @query.convert_options(:limit => @page_size)[1]
    
    if @page_cursors && @page_cursors[page_num]
      puts "************************* hit cached cursor :page#{page_num}, cursor: #{ @page_cursors[page_num] }"
      cursor_str = @page_cursors[page_num]
      java_cursor = Cursor.parse(cursor_str).to_java
      fetchOptions.cursor(java_cursor)
    else
      fetchOptions.offset(@page_size * (page_num -1)) unless page_num == 1          
    end
    
    #result = @query.fetch(fetchOptions)
    @result = @query.pquery.as_query_result_list(fetchOptions)  
    
    update_cursors(page_num, @result) 
        
    @result
  end
  
  
  def update_cursors(page_num, result)
    if result.length == @page_size
      #persist the cursor (but only if a full page of results has been returned
      @page_cursors[page_num + 1] = result.cursor.to_web_safe_string
    elsif result.empty?
      @page_cursors.delete page_num + 1
    end
    unless @last_page_cursors == @page_cursors
      puts "***********************persist cursors cache"
      AppEngine::Memcache.new.set(@query_mem_key, @page_cursors)
    end
  end
  
  
  def has_page?(page_num)
    page_num > 0 and (@page_cursors.length > page_num or page_num <= page_count)
  end

  def page_count    
    unless @query_count
      @query_count = @query.count #TODO using more elegent count method
      puts "***********************persist query count"
      AppEngine::Memcache.new.set("#{@query_mem_key}_COUNT", @query_count)
    end    
    full_pages, modulus = @query_count.divmod(@page_size)
    modulus == 0 ? full_pages : full_pages + 1
  end
  
  #------------------------------------------------------------------------------------


  #to clear the memcache after update model at anytime
  def self.clear(mem_key)
    AppEngine::Memcache.new.delete mem_key
    AppEngine::Memcache.new.delete "#{mem_key}_COUNT"
  end
  
  #to data mapper objects
  def self.to_datamapper(search_result, dm_model)
    dm = Struct.new(:repository, :fields, :reload?).new(DataMapper::repository, dm_model.properties, false)
    search_result.collect { |e| dm_model.load([Paginator.entity_to_hash(e, dm_model.properties)], dm)}.flatten
  end  
  
  #This should be moved to the Adapter
  def self.entity_to_hash(entity, properties)
    return if entity.nil?
    key  = entity.get_key
    hash = {}
    properties.each do |property|
      name = property.field
      if property.key?
        hash[name] = if property.kind_of? DataMapper::Property::Key
                       key
                     elsif property.serial?
                       key.get_id
                     elsif property.kind_of? DataMapper::Property::String
                       key.get_name
                     else
                       key
                     end
      else
        value      = entity.get_property(name)
        if property.kind_of?(DataMapper::Property::Decimal) && value
          value = Lexidecimal.string_to_decimal(entity.get_property(name))
        end
        hash[name] = value
      end
    end
    hash
  end

end













  class Cursor

    def initialize(cursor)
      @_cursor = cursor
    end

    # Converts the cursor to a string encoded in base64.
    def to_s
      @_cursor.to_web_safe_string
    end


    # Converts the cursor from a base 64 encoded string and returns the cursor object
    #
    # * must be a base 64 encoded cursor
    def self.parse(cursor_string)
      if cursor_string.nil?
        nil
      else
        Cursor.new Java::comGoogleAppengineApiDatastore::Cursor.from_web_safe_string(cursor_string)
      end
    end

    # returns the actual Java cursor (instance of com.google.appengine.api.datastore.Cursor
    def to_java
      @_cursor
    end
  end