set -e

for i in 1 2 3 4 5; do
    freva --plugin --debug dummyplugin the_number=$i
done
