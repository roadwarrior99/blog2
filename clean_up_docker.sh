#!/bin/bash
set -eu

# Keep only the last 2 container instances per image (running containers are always kept)
echo "=== Pruning old container instances (keep last 2 per image) ==="
docker ps -a --format "{{.Image}}" | sort -u | while read -r image; do
    # Get exited containers for this image, newest first, skip first 2
    docker ps -a --filter "ancestor=$image" --filter "status=exited" \
        --format "{{.ID}}" | tail -n +3 | while read -r id; do
        echo "Removing old container $id (image: $image)"
        docker container rm "$id"
    done
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