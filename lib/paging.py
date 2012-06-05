'''
This module contains classes for managing paging. 
'''
import google.appengine.ext.db as db
import google.appengine.api.memcache as memcache
import logging
import pickle

namespace = 'he3'

class PagedQuery(object):
	'''
	This class is a facade to a db.Query object that offers additional
	functionality to enable paging operations on query datasets. This class
	uses the cursor functionality introduced recently into Google App Engine
	to provide a full paging abstraction.
	
	Note that support for all Query and GqlQuery methods is provided, although
	executing a method not supported by GqlQuery will raise an error on 
	PagedQuery objects instantiated with a GqlQuery object.
	
	Of course, the cursor() and with_cursor() methods should only be used 
	rarely since most uses of cursors duplicates the functionality (and defeats
	the purpose) of this facade. The cursor methods are provided for 
	completeness.  
	
	USAGE:
	
	Instantiate a PagedQuery with an existing db.Query or db.GqlQuery and a 
	page size:
	
	myPagedQuery = PagedQuery(myEntity.all(), 10)
	
	PagedQuery supports the filter and ordering methods of db.Query if you 
	instantiate the object with a db.Query (not db.GqlQuery). You can apply
	these methods before or after instancing the PagedQuery. Eg.
	
	myQuery = myEntity.all().filter('myPropName >', my_prop_value)
	myPagedQuery = PagedQuery(myQuery, 10)
	myPagedQuery.order('-myPropName')
	
	This is fine. 
	
	To fetch the first page of the results:
	myResults = myPagedQuery.fetch_page()
	
	To fetch any particular page, use a page number:
	myResults = myPagedQuery.fetch_page(3)
	
	On a subsequent request, recreate the same query and PagedQuery object, and
	request another page:
	myResults = myPagedQuery.fetch_page(4)
	
	To determine whether a particular page exists:
	nextPageExists = myPagedQuery.has_page(5)
	
	To get a count of the number of pages available with the dataset:
	num_pages = myPagedQuery.page_count()
	
	Some necessary implementation details: 
	
	Cursor Limits: This class works using the Cursor features introduced in the
	Google App Engine SDK 1.3.1. All cursor restrictions apply. In particular
	, pages will not re-order if changes are made to the query results prior 
	to current page. Some query features (IN and != filters) will not work and
	sorting on multi-value fields will be unreliable. 
	
	See http://code.google.com/appengine/docs/python/datastore/queriesandindexes.html#Query_Cursors  
	for more information 
	
	Efficient Use: The most efficent way to use PagedQuery is to retrieve
	one successive page after another. Access to any previous page is just as
	efficient. Avoid calling the page_count() method or requesting pages more
	than one in advance of the highest page yet requested.
	
	Memcache: Internally PagedQuery persists information to memcache. The
	information cached includes a query identifier and a hash of pages and
	cursors. Due to the unreliable nature of memcache, persistence can not be
	ensured. PagedQuery will handle memcache misses, at a reduced
	performance profile. 
	
	Data Updates: Because of the cached nature of the internal cursors, if you
	need to ensure the most up to data is retrieve, clear all cached data:
	
	myPagedQuery.clear()
	
	myPagedQuery.fetch_page() (which returns the first page) also clears the
	cached data.  
	
	Mutating the query in any way (using .filter(), order() or
	similiar) also clears the cache. 
	
	Note that when retrieving a page for a second time, the internal cursors
	are checked for changes. If changes exist, the cursors corresponding to all
	subsequent pages are cleared from the cache. 
	'''

	def __init__(self, query, page_size):
		'''
		Constructor for a paged query.
		@param query: a google.appengine.ext.db.query object
		@param page_size: a positive non-zero integer defining the size of 
		each page.
		
		@raise TypeError: raised if query is not an instance of db.Query or 
		db.GqlQuery 
		'''
		
		self._query = query
		self._page_size = page_size
		self._page_cursors = [None]
		self._page_count = None
		self._id = None
		self._last_persisted_as = None

		self._num_offset_queries = 0
		self._num_cursor_queries = 0
		self._num_page1_queries = 0
		self._num_count_calls = 0
		self._num_persist = 0
		self._num_restore = 0
		
		#find out if we are dealing with another facade object
		if query.__dict__.has_key('_query'): query_to_check = query._query
		else: query_to_check  = query
								
		if isinstance(query_to_check, db.Query): self._query_type = 'Query'
		elif isinstance(query_to_check, db.GqlQuery): self._query_type = 'GqlQuery'
		else: raise TypeError('Query type not supported: '\
			 + type(query).__name__)
		
		self._check_page_size(page_size)
			
	def fetch_page(self, page_number=1, clear=False):
		'''Fetches a single page of results from the datastore. A page in the
		datastore starts at a specific position equal to 
		(page_size x page_number) - page_size (zero-based). If the page does
		not exist (not enough results to support it), an empty list is returned
		
		@param page_number: The number of the page to return. If None or no
		parameter is specified for page_number, page 1 is returned and cache
		cleared. 
		@return: A list of all entities on the specified page.
		'''
		
		if clear:
			self.clear()
		else:
			self.id #force id to be assigned now	
			self._restore_if_required()	
		
		self._check_page_number(page_number)	

		if self._has_cursor_for_page(page_number):
			offset = 0
			self._query.with_cursor(self._get_cursor_for_page(page_number))
			self._num_cursor_queries += 1 
		elif page_number > 1:
			
			#if we can not use a cursor, we need to use the offset method
			#the offset method errors if it is out of range. Therefore:
			#if page_number > 1 and page_number > self.page_count(): return []
			
			self._query.with_cursor(None)			
			offset = (self.page_size * (page_number -1))
			
			#record that we did an offset query. Useful for testing
			self._num_offset_queries += 1
		else:
			self._num_page1_queries += 1
			self._query.with_cursor(None)
			offset= 0

		results = self.fetch(limit=self.page_size, offset=offset)
		
		self._update_cursors_with_results(page_number, results)
		
		self._query.with_cursor(None)
		self._persist_if_required()

		return results
	
	def clear(self):
		'''Clears the cached data for the current query'''
		memcache.Client().delete(self._get_memcache_key())
		self._page_cursors = [None]
		self._page_count = None
		self._last_persisted_as = None
		self._id = None
				
	def page_count(self):
		'''Returns the number of pages that can be returned by the query
		@return: an integer value of 0 or higher indicating the total number
		of pages available, up to limit
		@warning: The maximum number of pages return is equal to 1000/page_size
		or the maximum number of pages returned by fetch_page(), whichever is greater.
		'''
		if not self._page_count:
			result_count = self._query.count()
			
			(full_pages, remainder) = divmod(result_count, self.page_size)
			self._page_count = full_pages if remainder == 0 else full_pages + 1
			
			#Record we did a query.count() call 
			self._num_count_calls += 1
		return self._page_count 
				
	def has_page(self, page_number):
		'''Returns True if the requested page exists for the current 
		PagedQuery object. Note that calling this method for a page at or below 
		that for whose page has already been fetched is cheaper performance-
		wise than calling it for a page not yet visited. Of course, if another
		action causes a full count() of the query then this action is cheap 
		regardless.
		@param page_number: Page number to test the existence of
		@return: True of false depending on whether the page exists. ie
		has_page(n) == len(fetch_page(n)) > 0'''
		
		#we might be able to avoid an unneccesary query.count() if we can see
		#a cursor already exists for page-number or a higher page.
		
		return page_number > 0 and (len(self._page_cursors) > page_number or page_number <= self.page_count())

	def fetch(self, limit, offset=0):
		''' executes query against datastore as per db.Query.fetch()
		@param limit: Maximum amount of results to retrieve as per 
		db.Query.fetch()
		@param offset: Number of results to skip prior to returning resultset.
		As per db.Query.fetch().
		
		@return: A list of entity results, as per db.Query.fetch()

		
		NOTE: this method should match the corresponding signature of 
		db.Query.fetch() precisely.
		@see: http://code.google.com/appengine/docs/python/datastore/queryclass.html
		'''
		
		return self._query.fetch(limit,offset)
	
	def filter(self, property_operator, value):
		'''Adds a property condition filter to the query. Only entities with
		properties that meet all of the conditions will be returned by the 
		query. This method should behave identically to the db.Query.filter()
		method. Using this method also clears any caching of the object.
		@attention: This method is only available for Queries used
		to initalise the PagedQuery of type db.Query
		@see: http://code.google.com/appengine/docs/python/datastore/queryclass.html
		
		@param property_operator: A string containing the property name, and an 
		optional comparison operator
		@param value: The value to use in the comparison on the right-hand side
		of the expression
		@return: The query with filter added
		@raise TypeError: raised if the query not the correct type
		'''
		self._check_query_type_is('Query')
		self.clear()
		self._query = self._query.filter(property_operator, value)
		return self 
		
	
	def order(self, property):
		'''Adds an ordering for the results. Results are ordered starting with
		the first order added. This method should behave identically to the 
		db.Query.order() method. Using this method also clears any caching of 
		the object.
		
		@attention: This method is only available for Queries used
		to initalise the PagedQuery of type db.Query
		@see: http://code.google.com/appengine/docs/python/datastore/queryclass.html
		
		@param property: A string, the name of the property to order
		@return: The query with order added
		@raise TypeError: raised if the query not the correct type
		'''
		self._check_query_type_is('Query')
		self.clear()
		self._query.order(property)
		return self
	
	def ancestor(self, ancestor):
		'''Adds an ancestor condition filter to the query. Only entities with
		the given entity as an ancestor (anywhere in its path) will be returned 
		by the query. This method should behave identically to the 
		db.Query.ancestor() method. Using this method also clears any caching of 
		the object.
		
		
		@attention: This method is only available for Queries used
		to initalise the PagedQuery of type db.Query
		@see: http://code.google.com/appengine/docs/python/datastore/queryclass.html
		
		@param ancestor: A Model instance or Key instance representing the 
		ancestor.
		@return: Itself after ancestor condition has been added
		@raise TypeError: raised if the query not the correct type
		'''
		self._check_query_type_is('Query')
		self.clear()
		self._query.ancestor(ancestor)
		return self
	
	def count(self, limit=1000):
		'''Returns the number of results this query fetches. This method should
		behave identically to the method of the same name of db.Query and 
		db.GqlQuery
		
		@see: http://code.google.com/appengine/docs/python/datastore/queryclass.html
		
		@param limit: The maximum number of results to count.
		@return: Returns the number of result this query fetches
		'''
		return self._query.count(limit)		

	def _get_page_size(self):
		'''Returns the page size set during instantiation or using 
		set_page_size()
		@return: An integer greater than zero indicating the number of results
		to be returned on each page.
		'''
		return self._page_size
	
	def _set_page_size(self, new_page_size):
		'''Sets the page size of the PagedQuery. If the new page_size differs 
		from the existing page size, the cache is cleared.
		
		@param new_page_size: an integer greater than zero indicating the number
		of results to be returned on each page. 
		@return: void  
		'''
		self._check_page_size(new_page_size)
		if new_page_size != self._page_size:
			self.clear()
			self._page_size = new_page_size
	
	def _has_cursor_for_page(self, page_number):
		'''Returns True if a page_cursor is available for a specific page, False
		otherwise
		@param page_number: The non-zero positive integer page number for which 
		to check the cursor for
		@return: True if a cursor exists for the page number, or false if not
		''' 		
		return (len(self._page_cursors) >= page_number\
			and self._page_cursors[page_number-1])
	
	def _set_cursor_for_page(self, page_number, cursor):
		'''Sets a cursor for a specific page.
		@param page_number: The non-zero positive integer page number to set the
		the cursor for
		@param cursor: the string cursor generated by query.cursor() to set for 
		the supplied page number 
		@return: void
		'''
		#append None values to page_cursors if required
		while len(self._page_cursors) < page_number:
			self._page_cursors.append(None)
		self._page_cursors[page_number-1] = cursor		
		
	def _get_cursor_for_page(self, page_number):
		'''Returns the cursor a for a page. Page must be known to exist prior
		to calling. If the page does not exist an exception will be raised.
		@param page_number: The non-zero positive integer page number to 
		to return the cursor for
		@return: The cursor for the page number specified
		@raise unknown: If the page number does not exist
		'''
		return self._page_cursors[page_number-1]
	
	def _get_query_id(self):
		'''Returns the ID of the query. This id is unique to the query. Whenever
		a query is rebuilt the same way (ie semantically identical) the ID will
		be the same
		@return: a string ID
		@todo: initial version cached id value. For some reason this caused 
		unexplainable errors in test cases. Cause unknown 
		'''
		if not self._id:
			self._id = self._generate_query_id()
		return self._id 
			
	def _generate_query_id(self):
		'''Generates a query ID for the PagedQuery from scratch
		@return: a string ID
		'''
		return str(hash(pickle.dumps(self._query,2)))
		
			
	def _check_query_type_is(self, required_query_type):
		'''This is a helper method to assert that the query the PagedQuery was
		initialised with is of the correct type.
		
		@param required_query_type: Value of self._query_type expected (
		currently only 'Query' or 'GqlQuery')
		@return: nothing 
		@raise TypeError: raised if the query not the correct type
		'''
		
		if self._query_type != required_query_type:
			raise TypeError('Operation not allowed for query type ('\
				+ type(self._query).__name__)
	
	def _check_page_number(self, page_number):
		'''This is a helper method to assert that the page_number provided is 
		of the correct type and value
		@param page_size: page_number value to check
		@return: nothing
		@raise: TypeError if the page_number is not a positive integer over 0
		'''
		if type(page_number) != int or page_number < 1:
			raise TypeError(
						'A page number must be a positive integer greater than 0')

	
	def _check_page_size(self, page_size):
		'''This is a helper method to check the type and value of a page_size
		parameter to ensure it is valid. If it is not valid a TypeError is
		thrown
		@param page_size: page_size value to check
		@return: nothing
		@raise: TypeError if the page_size is not a positive integer over 0
		''' 
		if type(page_size) != int or page_size < 1:
			raise TypeError(
						'A page size must be a positive integer greater than 0')
	
	def _update_cursors_with_results(self, page_number, results):
		'''Updates the cached page cursors with information inferred from the
		page_number and the contents of that page number.
		@param page_number: non-zero positive integer page number that generated
		the results.
		@param results: List of entities returned by a Query or GQL querty for 
		a specific page. 
		@return: Nothing
		''' 
		
		if len(results) == self.page_size:
			#persist the cursor (but only if a full page of results has been 
			#returned)
			self._set_cursor_for_page(
						page_number = page_number + 1,
						cursor = self._query.cursor())
		elif len(results) == 0:
			#remove the cursor for the current page
			self._set_cursor_for_page(
						page_number = page_number,
						cursor = None)
	def _persist_if_required(self):
		'''Persists the persistable cached elements of the object for retrieval
		in a separate request only if conditions are appropriate. 
		@return: nothing
		'''
		persisted_form = self._get_persisted_form()
		
		if (not self._last_persisted_as)\
			or self._last_persisted_as != persisted_form:
			
			self._persist(persisted_form)
			self._last_persisted_as = persisted_form
			
	def _persist(self, persisted_form):
		'''Persists the provided persisted form to the memcache peristence layer
		@param persisted_form: object to persist
		@return: nothing
		''' 
		memcache.Client().set(self._get_memcache_key(), persisted_form)
		self._num_persist += 1
			
	def _restore_if_required(self):
		'''Restores the persisted version of the PagedQuery if required.
		'''
		if not self._last_persisted_as:
			self._last_persisted_as = self._restore()
	
	def _restore(self):
		'''Restored any persisted version of the query to the correct values
		within the query and returns the persisted form
		@return: The persisted form 
		'''
		persisted_form = memcache.Client().get(self._get_memcache_key())
		
		if persisted_form:
			self._page_cursors = [s for s in persisted_form['page_cursors']]
			self._page_count = persisted_form['page_count']
			self._num_restore += 1
		return persisted_form
	
	def _get_memcache_key(self):
		'''Returns the correct memcache key used to identify this query in
		the memcache system
		@return: A string memcache key to use
		'''		
		return namespace + '_PagedQuery-persistence_' + str(self.id)
			
	def _get_persisted_form(self):
		'''Returns the form the PagedQuery information is persisted in
		@return an object
		'''
		return {
			'page_cursors':[s for s in self._page_cursors],
			'page_count':self._page_count
			}
									
	page_size = property(fget=_get_page_size, fset=_set_page_size, 
						doc='Configured page size of the PagedQuery')

	id = property(fget=_get_query_id, doc='unique id of this query')


class PageLinks:
	'''This is an object representing a list of hyperlinks to a set of
	pages.
	'''
	
	def __init__(self, page, page_count, url_root, page_field, page_range= 10):
		'''intialises the PageLinks object with the information required
		to generate the page link set
		@param page: The current page
		@param page_count: The total number of pages
		@param url_root: The start of the URL assigned to each page.
		@param page_field: The name of the URL parameter to use for pages
		@param page_range: number of pages in total to show, excluding previous
		, next and current page. rounded down for odd numbers. Must be positive
		and non-zero.
		'''
		
		self.page = page
		self.page_count = page_count
		self.url_root = url_root
		self.page_field = page_field
		self.page_range = page_range
		
	def get_links(self):
		'''uses the initialisation information to return a list of links
		@return: A list of text and url pairs
		'''
		#find the number of items to show either side (if possible)
		i_side_range = self.page_range//2
		#create the appropriate page range to show
		if self.page < i_side_range + 1: 
			pages = range(1, 
				self.page_count + 1 if self.page_count < (2*i_side_range) else (2*i_side_range)+1)
		else:
			pages = range(self.page - i_side_range
				, self.page_count + 1 if self.page_count < (self.page + i_side_range) 
				else (self.page + i_side_range + 1))
		
		#determine whether parameters are already present in URL and set first 
		#symbol appropriately.
		first_symbol = '&' if self.url_root.count('?') else '?'
		

		#use page range to construct list
		page_links =\
			[(str(p),'%s%s%s=%d' % (self.url_root, first_symbol,self.page_field,p)) for p in pages]

		#add a prev link if required
		if self.page > 1:
			prev_link  = ('Prev', '%s%s%s=%d' % 
						(self.url_root, first_symbol, self.page_field, self.page - 1) )
			page_links.insert(0,prev_link)
		
		#add a next link if required
		if self.page < self.page_count:
			next_link = ('Next', '%s%s%s=%d' % 
						(self.url_root, first_symbol, self.page_field, self.page + 1) )
			page_links.append(next_link)
		
		return page_links
				