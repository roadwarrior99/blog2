#!/bin/bash
# copy the files from my project box to a local data folder
scp -r project:/var/www/blog/blogdata/ /home/colin/python/blog2/vacuumflask/data/
# read the blog.yml file and export the ids, then remove extra --- values from stream
# and store the ids in a file called blog_ids.txt
yq eval '.id' data/blogdata/blog.yml | sed '/^---$/d' > data/blogdata/blog_ids.txt
# loop through the blog ids and query the sqlite3 database and check and see if they exist
# if they do not exist run the old_blog_loader pythong script to insert the missing record.
while IFS= read -r id
do
  result=$(sqlite3 data/vacuumflask.db "select id from post where old_id='$id';")
  if [ -z "$result" ]; then
    python3 old_blog_loader.py data/blogdata/blog.yml data/vacuumflask.db "$id"
  fi
done < data/blogdata/blog_ids.txt
# clean up blog ids file as it is no longer needed
rm data/blogdata/blog_ids.txt
echo "Done"

