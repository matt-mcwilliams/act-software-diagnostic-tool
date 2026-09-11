ALTER TABLE practice_sets
  ADD COLUMN assessment_session_id uuid REFERENCES assessment_sessions(id);

CREATE UNIQUE INDEX practice_sets_assessment_session_idx
  ON practice_sets(assessment_session_id)
  WHERE assessment_session_id IS NOT NULL;
