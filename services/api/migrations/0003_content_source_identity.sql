ALTER TABLE content_sources
  ADD CONSTRAINT content_sources_identity_key
  UNIQUE (source_type, name, version);
