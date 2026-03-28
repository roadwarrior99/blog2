#!/bin/bash
set -eu

# Remove stopped containers older than a week
echo "=== Removing old stopped containers ==="
docker ps -a --filter "status=exited" --filter "until=168h" --format "{{.ID}}" | while read -r id; do
    echo "Removing container $id"
    docker container rm "$id"
done

# Remove dangling images (<none>:<none>)
echo "=== Removing dangling images ==="
docker image prune -f

# Remove named images that are not used by any container (running or stopped)
echo "=== Removing unused named images ==="
in_use=$(docker ps -a --format "{{.Image}}")
docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | grep -v "^<none>" | while read -r tag id; do
    if ! echo "$in_use" | grep -qF "$tag"; then
        echo "Removing unused image $tag ($id)"
        docker image rm "$id" || echo "  skipped $tag (may be referenced by another tag)"
    fi
done

echo "=== Done ==="
docker system df