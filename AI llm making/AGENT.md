# AGENT.md — Person 1 (LLM & Language Processing)

## Project Overview
MindAble is a job-matching platform built specifically for people with mental
disabilities such as autism, ADHD, depression, and dyslexia. The platform
analyzes a user's CV, matches them with suitable job listings scraped from
external sources, and presents those listings in a disability-friendly format.
Your role covers all LLM-based language processing on the platform.

---

## Your Responsibilities
You are responsible for three components:

1. **CV Analysis Engine** — Takes raw CV text submitted by the user and sends
it to an LLM. The model extracts a structured JSON profile containing skills,
preferred work environment, communication style, limitations, and any
accommodations needed. This JSON is handed off to Person 2 for embedding and
matching.

2. **Disability-Friendly Description Rewriter** — Takes a raw job listing and
rewrites it using an LLM into plain, simple, accessible language. Output is
cached per listing in the database and served directly to the frontend.

3. **Interview Preparation Chatbot (Optional)** — A stateful conversational
assistant that helps users prepare for a specific job interview. It is loaded
with the user's CV profile and the target job listing, and guides the user
through mock questions and gentle feedback.

---

## Technology
- **Language:** Python
- **LLM Provider:** Anthropic API (Claude) or OpenAI API (GPT-4) — pick one
  and stay consistent across all three components
- **Django Integration:** You do not connect to Django directly. You expose
  clean Python functions that Person 2 calls from within the Django pipeline
- **Environment Variables:** All API keys must be loaded from environment
  variables using python-dotenv. Never hardcode keys.
- **Output Format:** All structured outputs (CV profile, rewritten listings)
  must be valid JSON. Use Pydantic models to validate all LLM outputs before
  they leave your module.

---

## Behaviour

### CV Analysis Engine
- Extract the following fields from every CV:
  - `skills` (list of strings)
  - `preferred_environment` (e.g. remote, quiet office, structured routine)
  - `communication_style` (e.g. written, one-on-one, avoids large groups)
  - `limitations` (cognitive, physical, or social — only what the user
    mentions)
  - `accommodations_needed` (list of strings)
  - `work_values` (what matters most to the user in a job)
- If a field cannot be determined from the CV, set it to null. Never invent
  information that is not there.
- The tone of the system prompt must be respectful and neutral. Do not frame
  disabilities as deficits in your prompts.

### Disability-Friendly Description Rewriter
- Rewrite every job listing to meet the following standards:
  - Short sentences, maximum 15 words each
  - No corporate jargon or buzzwords
  - Highlight the three most important things about the role at the top
  - Include a short section on what a typical day looks like
  - End with a warm, encouraging closing line
- Cache the rewritten output. Do not call the LLM again for a listing that has
  already been rewritten.

### Interview Preparation Chatbot
- Load the user's CV profile JSON and the target job listing into the system
  prompt at the start of every session
- Ask one question at a time. Never overwhelm the user with multiple questions
  in a single message
- Give feedback gently. Never use words like wrong, incorrect, or failed
- If the user seems distressed or confused, slow down and offer a simpler
  version of the question
- Keep responses short — no more than 4 sentences per turn

---

## Hard Constraints
- **Never expose raw API errors to the user.** Catch all exceptions and return
  a clean, human-readable fallback message
- **Never hallucinate CV data.** If the CV does not mention something, do not
  fill it in. Return null for missing fields
- **Never store raw CV text in logs.** CV content is sensitive personal data
- **All LLM outputs must be validated.** Use Pydantic to enforce the expected
  schema before passing data downstream. If validation fails, retry the LLM
  call once with a corrected prompt before raising an error
- **No prompt injection.** Sanitize all user-submitted text before inserting
  it into a prompt. Strip any instruction-like patterns from CV input
- **Temperature settings:** Use temperature 0.2 for the CV parser and
  description rewriter where consistency matters. Use temperature 0.7 for the
  chatbot where more natural conversation is needed
- **Token limits:** Keep CV analysis prompts under 2000 tokens. Keep rewriter
  prompts under 1500 tokens. The chatbot may use up to 4000 tokens with
  history included

---

## Coding Style
- Use clear, descriptive function names:
  `analyze_cv()`, `rewrite_job_description()`, `chat_interview_response()`
- Each component lives in its own Python file:
  `cv_analyzer.py`, `description_rewriter.py`, `interview_chatbot.py`
- Every function must have a docstring explaining its input, output, and any
  side effects
- Use type hints on all function signatures
- Do not put business logic inside prompt strings. Build prompts from
  structured variables so they are easy to read and update
- Write at least one unit test per function using pytest, mocking the LLM API
  call so tests do not consume real tokens
- Keep all prompt templates in a separate `prompts.py` file. Never scatter
  prompt strings across multiple files