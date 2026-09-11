import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

const files = [
  "content/exports/master-output-english.json",
  "content/exports/master-output-math.json",
];
const optionIds = new Set(["A", "B", "C", "D"]);

const fail = (file, message) => {
  throw new Error(`${file}: ${message}`);
};

function assertCount(file, label, actual, expected) {
  if (actual !== expected) fail(file, `${label} count is ${actual}; metadata says ${expected}`);
}

function validateSkills(file, data) {
  const ids = new Set();
  for (const skill of data.skills) {
    if (!skill.id || !skill.name || !skill.definition) fail(file, "every skill needs id, name, and definition");
    if (ids.has(skill.id)) fail(file, `duplicate skill id ${skill.id}`);
    ids.add(skill.id);
  }
  assertCount(file, "skill", data.skills.length, data.metadata.skillCount);
  return ids;
}

function validateQuestions(file, data, skillIds) {
  const ids = new Set();
  for (const question of data.questions) {
    const id = `${question.testKey}:${question.questionNumber}`;
    if (ids.has(id)) fail(file, `duplicate question ${id}`);
    ids.add(id);
    if (!question.stem || !question.correctOption || !optionIds.has(question.correctOption)) {
      fail(file, `${id} needs a stem and one correct option A-D`);
    }
    for (const option of ["A", "B", "C", "D"]) {
      if (typeof question[`option${option}`] !== "string" || !question[`option${option}`].trim()) {
        fail(file, `${id} is missing option ${option}`);
      }
    }
    const referencedSkillIds = new Set(question.skillIds ?? []);
    for (const classification of Object.values(question.wrongAnswerClassifications ?? {})) {
      for (const skillId of classification.skillIds ?? []) referencedSkillIds.add(skillId);
    }
    for (const skillId of referencedSkillIds) {
      if (!skillIds.has(skillId)) fail(file, `${id} references unknown skill ${skillId}`);
    }
  }
  assertCount(file, "question", data.questions.length, data.metadata.questionCount);
}

for (const file of files) {
  const raw = await readFile(file, "utf8");
  const data = JSON.parse(raw);
  if (!data.metadata || !Array.isArray(data.skills) || !Array.isArray(data.tests) || !Array.isArray(data.questions)) {
    fail(file, "expected metadata, skills, tests, and questions arrays");
  }
  if (!data.metadata.taxonomyVersion || !data.metadata.subject) fail(file, "metadata needs subject and taxonomyVersion");
  const skillIds = validateSkills(file, data);
  validateQuestions(file, data, skillIds);
  assertCount(file, "test", data.tests.length, data.metadata.testCount);
  const hash = createHash("sha256").update(raw).digest("hex").slice(0, 12);
  console.log(`${data.metadata.subject}: ${data.skills.length} skills, ${data.tests.length} tests, ${data.questions.length} questions (source ${hash})`);
}

console.log("Content validation passed. Dry-run only; no database rows were written.");
