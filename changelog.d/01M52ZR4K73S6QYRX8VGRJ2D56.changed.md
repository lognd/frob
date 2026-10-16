The std tool definitions now live in gob-check, so gob-check no longer depends on gob-packs (fixes the layering break); the dev artifacts and publish jobs also wait for the cone-compare job.
