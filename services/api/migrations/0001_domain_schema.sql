CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE content_lifecycle AS ENUM ('draft', 'approved', 'retired');
CREATE TYPE review_verdict AS ENUM ('pending', 'approved', 'rejected', 'needs_adjudication');
CREATE TYPE assessment_purpose AS ENUM ('diagnostic', 'practice', 'reassessment');
CREATE TYPE assessment_status AS ENUM ('created', 'in_progress', 'submitted', 'scoring', 'scored', 'expired', 'abandoned', 'failed');
CREATE TYPE evidence_direction AS ENUM ('positive', 'negative', 'omitted');
CREATE TYPE remediation_status AS ENUM ('recommended', 'learning', 'practicing', 'ready_to_reassess', 'reassessing', 'mastered', 'repeat_recommended', 'needs_more_evidence', 'abandoned');

CREATE TABLE subjects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE taxonomy_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  version text NOT NULL,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  published_at timestamptz,
  notes text,
  UNIQUE (subject_id, version)
);

CREATE TABLE skills (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  taxonomy_version_id uuid NOT NULL REFERENCES taxonomy_versions(id),
  external_key text NOT NULL,
  name text NOT NULL,
  definition text NOT NULL,
  instructional_explanation text,
  parent_id uuid REFERENCES skills(id),
  importance_weight numeric(8, 5) NOT NULL DEFAULT 0.5 CHECK (importance_weight >= 0 AND importance_weight <= 1),
  status content_lifecycle NOT NULL DEFAULT 'draft',
  UNIQUE (taxonomy_version_id, external_key)
);

CREATE TABLE skill_prerequisites (
  skill_id uuid NOT NULL REFERENCES skills(id),
  prerequisite_skill_id uuid NOT NULL REFERENCES skills(id),
  strength numeric(8, 5) NOT NULL DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
  reviewed boolean NOT NULL DEFAULT false,
  PRIMARY KEY (skill_id, prerequisite_skill_id),
  CHECK (skill_id <> prerequisite_skill_id)
);

CREATE TABLE content_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type text NOT NULL,
  name text NOT NULL,
  version text,
  rights_status text NOT NULL DEFAULT 'unreviewed',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES content_sources(id),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  external_key text NOT NULL,
  title text NOT NULL,
  profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  UNIQUE (source_id, external_key)
);

CREATE TABLE sections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id uuid NOT NULL REFERENCES tests(id),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  section_order integer NOT NULL CHECK (section_order > 0),
  time_limit_seconds integer CHECK (time_limit_seconds IS NULL OR time_limit_seconds > 0),
  status content_lifecycle NOT NULL DEFAULT 'draft',
  UNIQUE (test_id, section_order)
);

CREATE TABLE passages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES content_sources(id),
  external_key text NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  title text,
  body text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  UNIQUE (source_id, external_key, version)
);

CREATE TABLE questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES content_sources(id),
  passage_id uuid REFERENCES passages(id),
  external_key text NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  stem text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}'::jsonb,
  format text NOT NULL,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  review_status review_verdict NOT NULL DEFAULT 'pending',
  generated_candidate_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, external_key, version)
);

CREATE TABLE answer_choices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid NOT NULL REFERENCES questions(id),
  label text NOT NULL,
  position integer NOT NULL CHECK (position > 0),
  content text NOT NULL,
  is_correct boolean NOT NULL DEFAULT false,
  UNIQUE (question_id, label),
  UNIQUE (question_id, position)
);

CREATE UNIQUE INDEX one_correct_choice_per_question
  ON answer_choices(question_id)
  WHERE is_correct;

CREATE TABLE question_skills (
  question_id uuid NOT NULL REFERENCES questions(id),
  skill_id uuid NOT NULL REFERENCES skills(id),
  role text NOT NULL CHECK (role IN ('primary', 'secondary', 'uncertain')),
  evidence_weight numeric(8, 5) NOT NULL DEFAULT 1 CHECK (evidence_weight >= 0),
  tag_source text NOT NULL,
  tag_confidence numeric(8, 5) CHECK (tag_confidence IS NULL OR (tag_confidence >= 0 AND tag_confidence <= 1)),
  reviewed_by uuid,
  PRIMARY KEY (question_id, skill_id)
);

CREATE TABLE choice_skill_evidence (
  answer_choice_id uuid NOT NULL REFERENCES answer_choices(id),
  skill_id uuid NOT NULL REFERENCES skills(id),
  direction evidence_direction NOT NULL,
  evidence_weight numeric(8, 5) NOT NULL DEFAULT 1 CHECK (evidence_weight >= 0),
  failure_mode text,
  rationale text,
  PRIMARY KEY (answer_choice_id, skill_id)
);

CREATE TABLE assessment_blueprints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  purpose assessment_purpose NOT NULL,
  version text NOT NULL,
  rules jsonb NOT NULL,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  scoring_version text NOT NULL,
  mastery_model_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (subject_id, purpose, version)
);

CREATE TABLE assessment_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  blueprint_id uuid NOT NULL REFERENCES assessment_blueprints(id),
  purpose assessment_purpose NOT NULL,
  status assessment_status NOT NULL DEFAULT 'created',
  started_at timestamptz,
  submitted_at timestamptz,
  scored_at timestamptz,
  model_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX assessment_sessions_student_status_idx ON assessment_sessions(student_id, status);

CREATE TABLE assessment_session_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES assessment_sessions(id),
  question_id uuid NOT NULL REFERENCES questions(id),
  position integer NOT NULL CHECK (position > 0),
  section_position integer,
  exposure_role text NOT NULL DEFAULT 'assessment',
  assigned_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, position),
  UNIQUE (session_id, question_id)
);

CREATE TABLE responses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_item_id uuid NOT NULL UNIQUE REFERENCES assessment_session_items(id),
  student_id uuid NOT NULL,
  answer_choice_id uuid REFERENCES answer_choices(id),
  response_content jsonb,
  is_omitted boolean NOT NULL DEFAULT false,
  client_revision integer NOT NULL DEFAULT 0 CHECK (client_revision >= 0),
  first_viewed_at timestamptz,
  answered_at timestamptz,
  time_spent_ms integer CHECK (time_spent_ms IS NULL OR time_spent_ms >= 0),
  self_reported_confidence integer CHECK (self_reported_confidence IS NULL OR self_reported_confidence BETWEEN 1 AND 5),
  saved_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX responses_student_idx ON responses(student_id);

CREATE TABLE response_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  response_id uuid NOT NULL REFERENCES responses(id),
  event_type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE item_exposures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  question_id uuid NOT NULL REFERENCES questions(id),
  session_id uuid NOT NULL REFERENCES assessment_sessions(id),
  purpose assessment_purpose NOT NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  answered_at timestamptz,
  UNIQUE (student_id, question_id, purpose)
);

CREATE INDEX item_exposures_student_question_idx ON item_exposures(student_id, question_id);

CREATE TABLE session_scores (
  session_id uuid PRIMARY KEY REFERENCES assessment_sessions(id),
  raw_correct integer NOT NULL CHECK (raw_correct >= 0),
  raw_total integer NOT NULL CHECK (raw_total >= 0),
  score_details jsonb NOT NULL,
  scoring_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (raw_correct <= raw_total)
);

CREATE TABLE mastery_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  skill_id uuid NOT NULL REFERENCES skills(id),
  response_id uuid NOT NULL REFERENCES responses(id),
  direction evidence_direction NOT NULL,
  weight numeric(10, 5) NOT NULL CHECK (weight >= 0),
  source_purpose assessment_purpose NOT NULL,
  model_version text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (response_id, skill_id, model_version)
);

CREATE TABLE mastery_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  skill_id uuid NOT NULL REFERENCES skills(id),
  mean numeric(10, 7) NOT NULL CHECK (mean >= 0 AND mean <= 1),
  lower_bound numeric(10, 7) NOT NULL CHECK (lower_bound >= 0 AND lower_bound <= 1),
  upper_bound numeric(10, 7) NOT NULL CHECK (upper_bound >= 0 AND upper_bound <= 1),
  effective_evidence numeric(10, 5) NOT NULL CHECK (effective_evidence >= 0),
  correct_count integer NOT NULL DEFAULT 0 CHECK (correct_count >= 0),
  incorrect_count integer NOT NULL DEFAULT 0 CHECK (incorrect_count >= 0),
  omitted_count integer NOT NULL DEFAULT 0 CHECK (omitted_count >= 0),
  classification text NOT NULL,
  model_version text NOT NULL,
  calculated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (lower_bound <= mean AND mean <= upper_bound)
);

CREATE INDEX mastery_snapshots_student_skill_idx ON mastery_snapshots(student_id, skill_id, calculated_at DESC);

CREATE TABLE recommendation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  trigger_session_id uuid REFERENCES assessment_sessions(id),
  formula_version text NOT NULL,
  inputs jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE recommendations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES recommendation_runs(id),
  skill_id uuid NOT NULL REFERENCES skills(id),
  rank integer NOT NULL CHECK (rank > 0),
  priority_score numeric(10, 7) NOT NULL CHECK (priority_score >= 0),
  weakness_score numeric(10, 7) NOT NULL CHECK (weakness_score >= 0),
  importance_score numeric(10, 7) NOT NULL CHECK (importance_score >= 0),
  confidence_score numeric(10, 7) NOT NULL CHECK (confidence_score >= 0),
  readiness boolean NOT NULL,
  status text NOT NULL DEFAULT 'current',
  explanation text NOT NULL,
  UNIQUE (run_id, rank),
  UNIQUE (run_id, skill_id)
);

CREATE TABLE learning_resources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id uuid NOT NULL REFERENCES skills(id),
  provider text NOT NULL,
  title text NOT NULL,
  url text NOT NULL,
  resource_type text NOT NULL,
  level text,
  mapping_type text NOT NULL DEFAULT 'exact',
  focus_note text,
  status content_lifecycle NOT NULL DEFAULT 'draft',
  last_verified_at timestamptz
);

CREATE TABLE remediation_cycles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  skill_id uuid NOT NULL REFERENCES skills(id),
  recommendation_id uuid REFERENCES recommendations(id),
  status remediation_status NOT NULL DEFAULT 'recommended',
  baseline_snapshot_id uuid REFERENCES mastery_snapshots(id),
  attempt_number integer NOT NULL DEFAULT 1 CHECK (attempt_number > 0),
  started_at timestamptz,
  completed_at timestamptz
);

CREATE TABLE resource_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id uuid NOT NULL REFERENCES remediation_cycles(id),
  resource_id uuid NOT NULL REFERENCES learning_resources(id),
  event_type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE practice_sets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_id uuid NOT NULL REFERENCES remediation_cycles(id),
  status text NOT NULL DEFAULT 'created',
  target_count integer NOT NULL CHECK (target_count > 0),
  assembly_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE practice_set_items (
  practice_set_id uuid NOT NULL REFERENCES practice_sets(id),
  question_id uuid NOT NULL REFERENCES questions(id),
  position integer NOT NULL CHECK (position > 0),
  PRIMARY KEY (practice_set_id, position),
  UNIQUE (practice_set_id, question_id)
);

CREATE TABLE reassessment_links (
  cycle_id uuid NOT NULL REFERENCES remediation_cycles(id),
  assessment_session_id uuid NOT NULL UNIQUE REFERENCES assessment_sessions(id),
  attempt_number integer NOT NULL CHECK (attempt_number > 0),
  PRIMARY KEY (cycle_id, attempt_number)
);

CREATE TABLE generation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id uuid NOT NULL REFERENCES subjects(id),
  skill_id uuid REFERENCES skills(id),
  generator_version text NOT NULL,
  model text,
  prompt_version text,
  request jsonb NOT NULL,
  status text NOT NULL DEFAULT 'started',
  cost numeric(12, 6),
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE generated_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES generation_runs(id),
  external_key text NOT NULL,
  payload jsonb NOT NULL,
  machine_status review_verdict NOT NULL DEFAULT 'pending',
  review_status review_verdict NOT NULL DEFAULT 'pending',
  rejection_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  question_id uuid,
  UNIQUE (run_id, external_key)
);

ALTER TABLE questions
  ADD CONSTRAINT questions_generated_candidate_fk
  FOREIGN KEY (generated_candidate_id) REFERENCES generated_candidates(id);

ALTER TABLE generated_candidates
  ADD CONSTRAINT generated_candidates_question_fk
  FOREIGN KEY (question_id) REFERENCES questions(id);

CREATE TABLE content_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid REFERENCES generated_candidates(id),
  question_id uuid REFERENCES questions(id),
  reviewer_id uuid,
  review_type text NOT NULL,
  verdict review_verdict NOT NULL,
  rubric_version text NOT NULL,
  findings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (candidate_id IS NOT NULL OR question_id IS NOT NULL)
);

CREATE TABLE generator_metrics (
  run_id uuid PRIMARY KEY REFERENCES generation_runs(id),
  candidate_count integer NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
  accepted_count integer NOT NULL DEFAULT 0 CHECK (accepted_count >= 0),
  rejected_count integer NOT NULL DEFAULT 0 CHECK (rejected_count >= 0),
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE analytics_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid,
  anonymous_session_id text,
  event_name text NOT NULL,
  entity_type text,
  entity_id uuid,
  properties jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX analytics_events_name_time_idx ON analytics_events(event_name, occurred_at DESC);

CREATE TABLE issue_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reporter_id uuid,
  entity_type text NOT NULL,
  entity_id uuid,
  category text NOT NULL,
  description text NOT NULL,
  status text NOT NULL DEFAULT 'open',
  resolution text,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);

CREATE TABLE experiment_assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  experiment_key text NOT NULL,
  variant text NOT NULL,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (student_id, experiment_key)
);

CREATE TABLE tutor_skill_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL,
  tutor_id uuid NOT NULL,
  subject_id uuid NOT NULL REFERENCES subjects(id),
  taxonomy_version_id uuid NOT NULL REFERENCES taxonomy_versions(id),
  skill_id uuid NOT NULL REFERENCES skills(id),
  rating integer,
  rank integer,
  confidence integer CHECK (confidence IS NULL OR confidence BETWEEN 1 AND 5),
  sealed_at timestamptz,
  revealed_at timestamptz
);

CREATE INDEX skills_taxonomy_status_idx ON skills(taxonomy_version_id, status);
CREATE INDEX questions_status_review_idx ON questions(status, review_status);
CREATE INDEX question_skills_skill_idx ON question_skills(skill_id);
CREATE INDEX learning_resources_skill_status_idx ON learning_resources(skill_id, status);
CREATE INDEX remediation_cycles_student_status_idx ON remediation_cycles(student_id, status);
