The Dockerfile adapter now records `USER`, `EXPOSE` and `HEALTHCHECK` instructions as stage attributes, so changing them changes the stage's Attr facet.
