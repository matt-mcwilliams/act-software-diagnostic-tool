import "server-only";

import type {
  AssessmentPurpose,
  ChoiceId,
  PrivateQuestion,
  PublicQuestion,
  Skill,
  Subject,
} from "./types";

const choices = (items: [string, string, string, string]) =>
  items.map((text, index) => ({
    id: ["A", "B", "C", "D"][index] as ChoiceId,
    text,
  }));

const question = (
  item: Omit<PrivateQuestion, "choices"> & {
    choices: [string, string, string, string];
  },
): PrivateQuestion => ({
  ...item,
  choices: choices(item.choices),
});

export const SKILLS: Skill[] = [
  {
    id: "ENG-CS-PUNC-001",
    subject: "english",
    name: "Unnecessary Punctuation",
    category: "Conventions of Standard English",
    definition: "Use punctuation only when the sentence structure calls for it.",
    whyItMatters: "Clear punctuation helps a reader see which ideas belong together.",
    importance: 0.9,
    resources: [
      {
        title: "Khan Academy: Punctuation",
        url: "https://www.khanacademy.org/humanities/grammar/punctuation",
        type: "lesson",
        note: "Focus on commas that separate complete ideas from optional information.",
      },
    ],
  },
  {
    id: "ENG-CS-SS-002",
    subject: "english",
    name: "Run-on Sentences",
    category: "Conventions of Standard English",
    definition: "Join independent clauses with a complete, appropriate connection.",
    whyItMatters: "Recognizing sentence boundaries makes revisions more precise and readable.",
    importance: 0.88,
    resources: [
      {
        title: "Khan Academy: Syntax",
        url: "https://www.khanacademy.org/humanities/grammar/syntax",
        type: "lesson",
        note: "Review how periods, semicolons, and conjunctions connect independent clauses.",
      },
    ],
  },
  {
    id: "ENG-KL-002",
    subject: "english",
    name: "Eliminating Redundancy",
    category: "Knowledge of Language",
    definition: "Remove words that repeat information without adding meaning.",
    whyItMatters: "Concise writing gives the reader the important idea without clutter.",
    importance: 0.72,
    resources: [
      {
        title: "Khan Academy: Style",
        url: "https://www.khanacademy.org/humanities/grammar/style",
        type: "lesson",
        note: "Look for repeated meanings, not just repeated words.",
      },
    ],
  },
  {
    id: "ENG-PW-OU-004",
    subject: "english",
    name: "Transition Words",
    category: "Production of Writing",
    definition: "Choose transitions that accurately show the relationship between ideas.",
    whyItMatters: "The right transition lets a reader follow the writer's logic quickly.",
    importance: 0.78,
    resources: [
      {
        title: "Khan Academy: Cohesion",
        url: "https://www.khanacademy.org/humanities/grammar/usage-and-style",
        type: "lesson",
        note: "Name the relationship between the two sentences before choosing a transition.",
      },
    ],
  },
  {
    id: "MATH-PHM-AF-004",
    subject: "math",
    name: "Rate, Proportion, Percent, and Estimation",
    category: "Preparing for Higher Mathematics",
    definition: "Use proportional relationships and percent change to model real situations.",
    whyItMatters: "Rates and percentages appear in everyday and ACT word problems.",
    importance: 0.9,
    resources: [
      {
        title: "Khan Academy: Ratios, rates, and percentages",
        url: "https://www.khanacademy.org/math/pre-algebra/rates-and-ratios",
        type: "lesson",
        note: "Translate the words into a ratio before calculating.",
      },
    ],
  },
  {
    id: "MATH-PHM-ALG-002",
    subject: "math",
    name: "One-Step Equations",
    category: "Preparing for Higher Mathematics",
    definition: "Solve an equation by undoing one operation while preserving equality.",
    whyItMatters: "One-step equations are the smallest building block for algebraic modeling.",
    importance: 0.84,
    resources: [
      {
        title: "Khan Academy: One-step equations",
        url: "https://www.khanacademy.org/math/algebra-basics/basic-equations-inequalities",
        type: "lesson",
        note: "Apply the inverse operation to both sides and check the result.",
      },
    ],
  },
  {
    id: "MATH-PHM-FUN-003",
    subject: "math",
    name: "Evaluating Functions",
    category: "Preparing for Higher Mathematics",
    definition: "Substitute an input into a function and simplify the resulting expression.",
    whyItMatters: "Function notation connects an algebraic rule to a specific output.",
    importance: 0.82,
    resources: [
      {
        title: "Khan Academy: Evaluating functions",
        url: "https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:functions",
        type: "lesson",
        note: "Replace every input variable before simplifying in the correct order.",
      },
    ],
  },
  {
    id: "MATH-PHM-SP-017",
    subject: "math",
    name: "Mean, Median, and Mode",
    category: "Preparing for Higher Mathematics",
    definition: "Calculate and interpret common measures of center.",
    whyItMatters: "Choosing the right measure of center helps describe data accurately.",
    importance: 0.76,
    resources: [
      {
        title: "Khan Academy: Statistics intro",
        url: "https://www.khanacademy.org/math/statistics-probability/summarizing-quantitative-data",
        type: "lesson",
        note: "Sort the data for median; add and divide for mean; count frequency for mode.",
      },
    ],
  },
];

const ENGLISH_DIAGNOSTIC: PrivateQuestion[] = [
  question({
    id: "eng-d-001",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-CS-PUNC-001",
    context: "The neighborhood garden, which opened in 2018 provides vegetables to local families.",
    prompt: "Which choice best completes the sentence?",
    choices: [
      "garden, which opened in 2018 provides",
      "garden which opened in 2018, provides",
      "garden, which opened in 2018, provides",
      "garden which opened in 2018 provides",
    ],
    correctChoiceId: "C",
    explanation: "The nonessential clause begins and ends with commas.",
    failureModeByChoice: { A: "missing_closing_comma", B: "misplaced_commas" },
  }),
  question({
    id: "eng-d-002",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-CS-PUNC-001",
    context: "After the storm the crew inspected every bridge before reopening the road.",
    prompt: "Which choice is the clearest punctuation for the sentence?",
    choices: [
      "After the storm the crew",
      "After the storm, the crew",
      "After, the storm the crew",
      "After the storm; the crew",
    ],
    correctChoiceId: "B",
    explanation: "A comma follows the introductory phrase ‘After the storm.’",
    failureModeByChoice: { A: "missing_introductory_comma", D: "incorrect_clause_boundary" },
  }),
  question({
    id: "eng-d-003",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-CS-SS-002",
    context: "The library extended its hours, students can now study there after work.",
    prompt: "Which choice best fixes the sentence boundary?",
    choices: [
      "hours, students",
      "hours; students",
      "hours students",
      "hours, and students can now",
    ],
    correctChoiceId: "B",
    explanation: "A semicolon correctly joins two closely related independent clauses.",
    failureModeByChoice: { A: "comma_splice", C: "missing_boundary" },
  }),
  question({
    id: "eng-d-004",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-CS-SS-002",
    context: "The trail is short, it climbs steadily toward the overlook.",
    prompt: "Which choice produces a complete, correct sentence?",
    choices: [
      "short, it climbs",
      "short; it climbs",
      "short it climbs",
      "short, climbing",
    ],
    correctChoiceId: "B",
    explanation: "The semicolon separates the two complete thoughts without adding a conjunction.",
    failureModeByChoice: { A: "comma_splice", C: "run_together_clauses" },
  }),
  question({
    id: "eng-d-005",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-KL-002",
    context: "The committee reached a unanimous consensus after a long discussion.",
    prompt: "Which choice is most concise without changing the meaning?",
    choices: ["unanimous consensus", "consensus", "unanimous agreement consensus", "long discussion"],
    correctChoiceId: "B",
    explanation: "Consensus already means general agreement, so ‘unanimous’ repeats the idea.",
    failureModeByChoice: { A: "repeated_meaning", C: "added_redundancy" },
  }),
  question({
    id: "eng-d-006",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-KL-002",
    context: "The unexpected surprise delighted the audience.",
    prompt: "Which choice removes the unnecessary word?",
    choices: ["unexpected surprise", "unexpected", "surprise audience", "delighted audience"],
    correctChoiceId: "B",
    explanation: "A surprise is already unexpected, so keeping ‘unexpected’ is enough.",
    failureModeByChoice: { A: "repeated_meaning", C: "changes_sentence_meaning" },
  }),
  question({
    id: "eng-d-007",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-PW-OU-004",
    context: "The first plan would reduce costs immediately. ___, it would delay the project by several months.",
    prompt: "Which transition best shows the relationship between the ideas?",
    choices: ["For example", "However", "Similarly", "Therefore"],
    correctChoiceId: "B",
    explanation: "‘However’ signals the contrast between lower costs and a longer schedule.",
    failureModeByChoice: { A: "adds_example_instead_of_contrast", D: "claims_cause" },
  }),
  question({
    id: "eng-d-008",
    subject: "english",
    purpose: "diagnostic",
    skillId: "ENG-PW-OU-004",
    context: "The city planted trees along the hottest streets. ___, shaded sidewalks now stay cooler in summer.",
    prompt: "Which transition best completes the paragraph?",
    choices: ["As a result", "In contrast", "For instance", "Meanwhile"],
    correctChoiceId: "A",
    explanation: "The second sentence describes the result of planting trees.",
    failureModeByChoice: { B: "claims_contrast", C: "adds_example_instead_of_result" },
  }),
];

const MATH_DIAGNOSTIC: PrivateQuestion[] = [
  question({
    id: "math-d-001",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-AF-004",
    prompt: "A $40 jacket is discounted by 25%. What is the sale price?",
    choices: ["$10", "$15", "$30", "$50"],
    correctChoiceId: "C",
    explanation: "A 25% discount is $10, so the sale price is $40 − $10 = $30.",
    failureModeByChoice: { A: "finds_discount_not_sale_price", B: "subtracts_incorrect_percent", D: "adds_discount" },
  }),
  question({
    id: "math-d-002",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-AF-004",
    prompt: "A recipe uses 3 cups of flour for 12 muffins. How many cups are needed for 20 muffins?",
    choices: ["4", "5", "6", "8"],
    correctChoiceId: "B",
    explanation: "The rate is 3/12 = 1/4 cup per muffin, so 20 × 1/4 = 5 cups.",
    failureModeByChoice: { A: "uses_wrong_scale_factor", C: "doubles_original_amount" },
  }),
  question({
    id: "math-d-003",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-ALG-002",
    prompt: "What is the value of x if x + 7 = 19?",
    choices: ["10", "12", "26", "133"],
    correctChoiceId: "B",
    explanation: "Subtract 7 from both sides: x = 19 − 7 = 12.",
    failureModeByChoice: { A: "subtracts_incorrectly", C: "adds_instead_of_subtracting" },
  }),
  question({
    id: "math-d-004",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-ALG-002",
    prompt: "What is the value of y if 5y = 35?",
    choices: ["5", "7", "30", "175"],
    correctChoiceId: "B",
    explanation: "Divide both sides by 5: y = 35 ÷ 5 = 7.",
    failureModeByChoice: { A: "divides_incorrectly", C: "subtracts_instead_of_dividing" },
  }),
  question({
    id: "math-d-005",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-FUN-003",
    prompt: "If f(x) = 2x + 3, what is f(4)?",
    choices: ["8", "10", "11", "14"],
    correctChoiceId: "C",
    explanation: "Substitute 4 for x: f(4) = 2(4) + 3 = 11.",
    failureModeByChoice: { A: "omits_constant", B: "adds_instead_of_multiplying" },
  }),
  question({
    id: "math-d-006",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-FUN-003",
    prompt: "If g(t) = t² − 1, what is g(3)?",
    choices: ["5", "6", "8", "9"],
    correctChoiceId: "C",
    explanation: "g(3) = 3² − 1 = 9 − 1 = 8.",
    failureModeByChoice: { A: "subtracts_before_squaring", D: "omits_subtraction" },
  }),
  question({
    id: "math-d-007",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-SP-017",
    prompt: "What is the mean of 4, 6, 7, and 11?",
    choices: ["6", "7", "8", "28"],
    correctChoiceId: "B",
    explanation: "The sum is 28 and there are 4 values, so the mean is 28 ÷ 4 = 7.",
    failureModeByChoice: { A: "divides_by_wrong_count", D: "reports_sum_instead_of_mean" },
  }),
  question({
    id: "math-d-008",
    subject: "math",
    purpose: "diagnostic",
    skillId: "MATH-PHM-SP-017",
    prompt: "What is the median of 2, 4, 9, 10, and 13?",
    choices: ["4", "8", "9", "10"],
    correctChoiceId: "C",
    explanation: "The values are already ordered; the middle value is 9.",
    failureModeByChoice: { A: "selects_lower_neighbor", B: "averages_without_even_count", D: "selects_upper_neighbor" },
  }),
];

const ENGLISH_PRACTICE: PrivateQuestion[] = [
  question({ id: "eng-p-punc-001", subject: "english", purpose: "practice", skillId: "ENG-CS-PUNC-001", context: "The museum's main gallery which opened last year attracts hundreds of visitors.", prompt: "Which choice correctly punctuates the nonessential clause?", choices: ["gallery which opened last year, attracts", "gallery, which opened last year, attracts", "gallery, which opened last year attracts", "gallery which opened last year attracts"], correctChoiceId: "B", explanation: "The nonessential clause needs a comma on both sides.", failureModeByChoice: { A: "missing_opening_comma", C: "missing_closing_comma" } }),
  question({ id: "eng-p-punc-002", subject: "english", purpose: "practice", skillId: "ENG-CS-PUNC-001", context: "Before sunrise the hikers reached the summit.", prompt: "Which choice best punctuates the opening phrase?", choices: ["Before sunrise, the hikers", "Before, sunrise the hikers", "Before sunrise; the hikers", "Before sunrise the hikers"], correctChoiceId: "A", explanation: "A comma separates the introductory phrase from the main clause.", failureModeByChoice: { C: "incorrect_clause_boundary", D: "missing_introductory_comma" } }),
  question({ id: "eng-p-run-001", subject: "english", purpose: "practice", skillId: "ENG-CS-SS-002", context: "The forecast changed, the event moved indoors.", prompt: "Which choice correctly separates the complete ideas?", choices: ["changed, the event", "changed; the event", "changed the event", "changed, moving the event"], correctChoiceId: "B", explanation: "A semicolon joins the two independent clauses.", failureModeByChoice: { A: "comma_splice", C: "missing_boundary" } }),
  question({ id: "eng-p-run-002", subject: "english", purpose: "practice", skillId: "ENG-CS-SS-002", context: "The team practiced every afternoon, it improved its passing.", prompt: "Which revision fixes the run-on?", choices: ["afternoon, it improved", "afternoon; it improved", "afternoon it improved", "afternoon, improving"], correctChoiceId: "B", explanation: "A semicolon separates two complete clauses.", failureModeByChoice: { A: "comma_splice", C: "missing_boundary" } }),
  question({ id: "eng-p-red-001", subject: "english", purpose: "practice", skillId: "ENG-KL-002", context: "The two twins shared the same identical backpack.", prompt: "Which words should be removed?", choices: ["two", "twins", "same", "identical"], correctChoiceId: "C", explanation: "‘Same’ and ‘identical’ repeat the same meaning; removing ‘same’ leaves a clear sentence.", failureModeByChoice: { A: "changes_quantity", D: "keeps_redundancy" } }),
  question({ id: "eng-p-red-002", subject: "english", purpose: "practice", skillId: "ENG-KL-002", context: "The final outcome surprised the researchers.", prompt: "Which word is unnecessary?", choices: ["final", "outcome", "surprised", "researchers"], correctChoiceId: "A", explanation: "An outcome is already the final result, so ‘final’ adds no needed meaning.", failureModeByChoice: { B: "removes_core_noun", C: "removes_main_verb" } }),
  question({ id: "eng-p-trans-001", subject: "english", purpose: "practice", skillId: "ENG-PW-OU-004", context: "The new route is longer. ___, it avoids the steepest hill.", prompt: "Which transition signals the contrast?", choices: ["Therefore", "For example", "However", "Likewise"], correctChoiceId: "C", explanation: "‘However’ introduces a contrast with the first sentence.", failureModeByChoice: { A: "claims_cause", B: "adds_example" } }),
  question({ id: "eng-p-trans-002", subject: "english", purpose: "practice", skillId: "ENG-PW-OU-004", context: "The class measured the soil. ___, students recorded the results in a table.", prompt: "Which transition best shows the next step?", choices: ["Next", "Instead", "Nevertheless", "For instance"], correctChoiceId: "A", explanation: "‘Next’ shows that recording follows measuring in the process.", failureModeByChoice: { B: "claims_replacement", C: "claims_contrast" } }),
];

const MATH_PRACTICE: PrivateQuestion[] = [
  question({ id: "math-p-rate-001", subject: "math", purpose: "practice", skillId: "MATH-PHM-AF-004", prompt: "A $60 item is 15% off. What is the sale price?", choices: ["$9", "$45", "$51", "$69"], correctChoiceId: "C", explanation: "15% of $60 is $9, and $60 − $9 = $51.", failureModeByChoice: { A: "finds_discount_not_price", B: "uses_wrong_discount", D: "adds_discount" } }),
  question({ id: "math-p-rate-002", subject: "math", purpose: "practice", skillId: "MATH-PHM-AF-004", prompt: "A car travels 180 miles in 3 hours at a constant rate. How far will it travel in 5 hours?", choices: ["60 miles", "300 miles", "540 miles", "900 miles"], correctChoiceId: "B", explanation: "The rate is 180 ÷ 3 = 60 miles per hour; 60 × 5 = 300.", failureModeByChoice: { A: "reports_rate", C: "multiplies_by_wrong_factor" } }),
  question({ id: "math-p-eq-001", subject: "math", purpose: "practice", skillId: "MATH-PHM-ALG-002", prompt: "What is the value of x if x − 9 = 4?", choices: ["−13", "−5", "5", "13"], correctChoiceId: "D", explanation: "Add 9 to both sides: x = 4 + 9 = 13.", failureModeByChoice: { A: "changes_sign_wrongly", C: "subtracts_instead_of_adding" } }),
  question({ id: "math-p-eq-002", subject: "math", purpose: "practice", skillId: "MATH-PHM-ALG-002", prompt: "What is the value of z if z/4 = 6?", choices: ["1.5", "2", "10", "24"], correctChoiceId: "D", explanation: "Multiply both sides by 4: z = 24.", failureModeByChoice: { A: "divides_again", C: "adds_instead_of_multiplying" } }),
  question({ id: "math-p-fun-001", subject: "math", purpose: "practice", skillId: "MATH-PHM-FUN-003", prompt: "If h(x) = 3x − 2, what is h(5)?", choices: ["8", "13", "15", "17"], correctChoiceId: "B", explanation: "Substitute 5: 3(5) − 2 = 13.", failureModeByChoice: { A: "subtracts_before_multiplying", C: "omits_constant" } }),
  question({ id: "math-p-fun-002", subject: "math", purpose: "practice", skillId: "MATH-PHM-FUN-003", prompt: "If p(n) = n² + 2, what is p(4)?", choices: ["6", "14", "16", "18"], correctChoiceId: "D", explanation: "p(4) = 4² + 2 = 18.", failureModeByChoice: { A: "adds_before_squaring", C: "omits_constant" } }),
  question({ id: "math-p-stat-001", subject: "math", purpose: "practice", skillId: "MATH-PHM-SP-017", prompt: "What is the mean of 5, 7, and 9?", choices: ["6", "7", "8", "21"], correctChoiceId: "B", explanation: "The sum is 21; divide by 3 values to get 7.", failureModeByChoice: { A: "divides_by_wrong_count", D: "reports_sum" } }),
  question({ id: "math-p-stat-002", subject: "math", purpose: "practice", skillId: "MATH-PHM-SP-017", prompt: "What is the mode of 2, 3, 3, 4, and 5?", choices: ["2", "3", "4", "5"], correctChoiceId: "B", explanation: "The mode is the value that appears most often: 3.", failureModeByChoice: { A: "selects_first_value", C: "selects_neighbor" } }),
];

const ENGLISH_REASSESSMENT: PrivateQuestion[] = [
  question({ id: "eng-r-punc-001", subject: "english", purpose: "reassessment", skillId: "ENG-CS-PUNC-001", context: "The old theater which reopened in May now hosts concerts.", prompt: "Which choice correctly punctuates the sentence?", choices: ["theater, which reopened in May, now", "theater which reopened in May, now", "theater, which reopened in May now", "theater which reopened in May now"], correctChoiceId: "A", explanation: "The nonessential clause is enclosed by commas.", failureModeByChoice: { B: "missing_opening_comma", C: "missing_closing_comma" } }),
  question({ id: "eng-r-punc-002", subject: "english", purpose: "reassessment", skillId: "ENG-CS-PUNC-001", context: "During the winter the pond freezes completely.", prompt: "Which choice best punctuates the introductory phrase?", choices: ["During the winter, the pond", "During, the winter the pond", "During the winter; the pond", "During the winter the pond"], correctChoiceId: "A", explanation: "A comma follows the introductory phrase.", failureModeByChoice: { C: "incorrect_clause_boundary", D: "missing_introductory_comma" } }),
  question({ id: "eng-r-run-001", subject: "english", purpose: "reassessment", skillId: "ENG-CS-SS-002", context: "The signal appeared, the machine stopped.", prompt: "Which choice fixes the sentence?", choices: ["appeared, the machine", "appeared; the machine", "appeared the machine", "appeared, stopping the machine"], correctChoiceId: "B", explanation: "A semicolon correctly joins the two independent clauses.", failureModeByChoice: { A: "comma_splice", C: "missing_boundary" } }),
  question({ id: "eng-r-run-002", subject: "english", purpose: "reassessment", skillId: "ENG-CS-SS-002", context: "The room was quiet, everyone was concentrating.", prompt: "Which choice correctly separates the clauses?", choices: ["quiet, everyone", "quiet; everyone", "quiet everyone", "quiet, concentrating everyone"], correctChoiceId: "B", explanation: "A semicolon separates the two complete thoughts.", failureModeByChoice: { A: "comma_splice", C: "missing_boundary" } }),
  question({ id: "eng-r-red-001", subject: "english", purpose: "reassessment", skillId: "ENG-KL-002", context: "The small miniature model fit on the shelf.", prompt: "Which word is unnecessary?", choices: ["small", "miniature", "model", "shelf"], correctChoiceId: "A", explanation: "A miniature model is already small, so ‘small’ is redundant.", failureModeByChoice: { B: "keeps_redundancy", C: "removes_core_noun" } }),
  question({ id: "eng-r-red-002", subject: "english", purpose: "reassessment", skillId: "ENG-KL-002", context: "The reason is because the roads are icy.", prompt: "Which choice is most concise?", choices: ["reason is because", "reason is that", "reason because is", "reason for because"], correctChoiceId: "B", explanation: "‘The reason is that’ expresses the relationship without redundancy.", failureModeByChoice: { A: "keeps_redundant_pair", C: "incorrect_word_order" } }),
  question({ id: "eng-r-trans-001", subject: "english", purpose: "reassessment", skillId: "ENG-PW-OU-004", context: "The first experiment failed. ___, the team revised the procedure and tried again.", prompt: "Which transition best completes the sentence?", choices: ["As a result", "For example", "In contrast", "Similarly"], correctChoiceId: "A", explanation: "The revision and second attempt follow from the first experiment's failure.", failureModeByChoice: { B: "adds_example", C: "claims_contrast" } }),
  question({ id: "eng-r-trans-002", subject: "english", purpose: "reassessment", skillId: "ENG-PW-OU-004", context: "The road is narrow. ___, it carries more traffic than any other road in the area.", prompt: "Which transition shows contrast?", choices: ["Therefore", "However", "For instance", "Next"], correctChoiceId: "B", explanation: "‘However’ contrasts the road's narrowness with its high traffic.", failureModeByChoice: { A: "claims_cause", C: "adds_example" } }),
];

const MATH_REASSESSMENT: PrivateQuestion[] = [
  question({ id: "math-r-rate-001", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-AF-004", prompt: "A $50 meal has a 20% tip. What is the total cost?", choices: ["$10", "$40", "$60", "$70"], correctChoiceId: "C", explanation: "A 20% tip is $10, so the total is $50 + $10 = $60.", failureModeByChoice: { A: "finds_tip_not_total", B: "subtracts_tip", D: "uses_wrong_percent" } }),
  question({ id: "math-r-rate-002", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-AF-004", prompt: "A machine makes 48 parts in 6 minutes. At this rate, how many parts in 10 minutes?", choices: ["8", "60", "80", "96"], correctChoiceId: "C", explanation: "The rate is 48 ÷ 6 = 8 parts per minute; 8 × 10 = 80.", failureModeByChoice: { A: "reports_rate", B: "uses_wrong_scale_factor", D: "adds_rate" } }),
  question({ id: "math-r-eq-001", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-ALG-002", prompt: "What is the value of a if a + 11 = 20?", choices: ["9", "11", "31", "220"], correctChoiceId: "A", explanation: "Subtract 11 from both sides: a = 9.", failureModeByChoice: { B: "reports_addend", C: "adds_instead_of_subtracting" } }),
  question({ id: "math-r-eq-002", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-ALG-002", prompt: "What is the value of b if 3b = 27?", choices: ["8", "9", "24", "81"], correctChoiceId: "B", explanation: "Divide both sides by 3: b = 9.", failureModeByChoice: { A: "divides_incorrectly", C: "subtracts_instead_of_dividing" } }),
  question({ id: "math-r-fun-001", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-FUN-003", prompt: "If q(x) = 4x + 1, what is q(2)?", choices: ["6", "8", "9", "12"], correctChoiceId: "C", explanation: "q(2) = 4(2) + 1 = 9.", failureModeByChoice: { A: "omits_multiplication", B: "omits_constant" } }),
  question({ id: "math-r-fun-002", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-FUN-003", prompt: "If r(t) = t² + 3, what is r(2)?", choices: ["5", "7", "8", "10"], correctChoiceId: "B", explanation: "r(2) = 2² + 3 = 7.", failureModeByChoice: { A: "omits_constant", C: "adds_before_squaring" } }),
  question({ id: "math-r-stat-001", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-SP-017", prompt: "What is the median of 1, 5, 6, 9, and 12?", choices: ["5", "6", "7", "9"], correctChoiceId: "B", explanation: "The middle value in the ordered list is 6.", failureModeByChoice: { A: "selects_lower_neighbor", D: "selects_upper_neighbor" } }),
  question({ id: "math-r-stat-002", subject: "math", purpose: "reassessment", skillId: "MATH-PHM-SP-017", prompt: "What is the mean of 3, 8, and 10?", choices: ["6", "7", "8", "21"], correctChoiceId: "B", explanation: "The sum is 21; 21 ÷ 3 = 7.", failureModeByChoice: { A: "divides_by_wrong_count", D: "reports_sum" } }),
];

const QUESTIONS_BY_PURPOSE: Record<AssessmentPurpose, PrivateQuestion[]> = {
  diagnostic: [...ENGLISH_DIAGNOSTIC, ...MATH_DIAGNOSTIC],
  practice: [...ENGLISH_PRACTICE, ...MATH_PRACTICE],
  reassessment: [...ENGLISH_REASSESSMENT, ...MATH_REASSESSMENT],
};

export function getSkills(subject?: Subject): Skill[] {
  return subject ? SKILLS.filter((skill) => skill.subject === subject) : SKILLS;
}

export function getQuestions(subject: Subject, purpose: AssessmentPurpose): PrivateQuestion[] {
  return QUESTIONS_BY_PURPOSE[purpose].filter((question) => question.subject === subject);
}

export function getQuestion(questionId: string): PrivateQuestion | undefined {
  return Object.values(QUESTIONS_BY_PURPOSE)
    .flat()
    .find((question) => question.id === questionId);
}

export function toPublicQuestion(question: PrivateQuestion): PublicQuestion {
  return {
    id: question.id,
    subject: question.subject,
    purpose: question.purpose,
    skillId: question.skillId,
    ...(question.context ? { context: question.context } : {}),
    prompt: question.prompt,
    choices: question.choices,
  };
}

export function getPublicQuestions(subject: Subject, purpose: AssessmentPurpose): PublicQuestion[] {
  return getQuestions(subject, purpose).map(toPublicQuestion);
}
