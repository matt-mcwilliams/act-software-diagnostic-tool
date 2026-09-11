CREATE TABLE import_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  source_path text NOT NULL,
  source_sha256 text NOT NULL UNIQUE,
  schema_version text NOT NULL,
  taxonomy_version text NOT NULL,
  status text NOT NULL DEFAULT 'previewed'
    CHECK (status IN ('previewed', 'imported', 'activated', 'retired', 'failed')),
  row_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  activated_at timestamptz,
  retired_at timestamptz
);

CREATE INDEX import_batches_subject_status_idx ON import_batches(subject_id, status);
