The state store now retries reads that hit a Windows replace window (PermissionDenied or sharing violation) with a short bounded backoff and reports a miss instead of an error.
