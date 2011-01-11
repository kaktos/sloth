module Sinatra
  module ContentFor
   
    def content_for(key, content = nil, &block)
      content_blocks[key.to_sym] << (block_given? ? block : Proc.new { content })
    end

 
    def yield_content(key, *args)
      blocks = content_blocks[key.to_sym]
      return nil if blocks.empty?
      blocks.map { |content|
        if respond_to?(:block_is_haml?) && block_is_haml?(content)
          capture_haml(*args, &content)
        else
          content.call(*args) 
        end		  
      }.join      
    end




    private
      def content_blocks
        @content_blocks ||= Hash.new {|h,k| h[k] = [] }
      end
  end

  helpers ContentFor
end