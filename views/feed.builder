xml.instruct! :xml, :version => '1.0'
xml.feed "xmlns" => "http://www.w3.org/2005/Atom" do
  xml.title AppSettings.title
  xml.id AppSettings.base_url
  xml.updated posts.first.created_at.iso8601 if posts.any?
  xml.author { xml.name AppSettings.author }
  
  posts.each do |post|
    xml.entry do
      xml.title post[:title]
      xml.link "rel" => "alternate", "href" => post.full_url
      xml.id post.full_url
      xml.published post.published_at.iso8601 unless post.published_at.blank?
      xml.updated post.updated_at.iso8601 unless post.updated_at.blank?
      xml.author { xml.name AppSettings.author }
      xml.content post.body_html, "type" => "html"
    end
  end
end
