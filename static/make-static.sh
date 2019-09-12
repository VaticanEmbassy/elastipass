#!/bin/bash

cat << EOF
<html>
	<head>
		<title>static files</title>
	</head>
	<body>
		<a href="/">go back</a>
		<br />
		<ul>
EOF


while IFS='' read -r -d '' filename; do
	if [ "$filename" = "./make-static.sh" ] ; then
		continue
	fi
	if [ "$filename" = "./index.html" ] ; then
		continue
	fi
	echo '			<li><a href="/static/'"$(echo ${filename} | cut -c 3-)"'">'${filename}'</a></li>'
done < <(find . -type f -print0)


cat << EOF	
		</ul>
	</body>
</html>
EOF
