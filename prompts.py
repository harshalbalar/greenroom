"""
AutoApply prompt templates.

Design philosophy:
- Each prompt asks for ONE specific output format (JSON or prose, never both).
- JSON prompts include the exact schema to reduce hallucinated fields.
- Prose prompts include word counts to prevent rambling.
- Every prompt reminds the LLM not to fabricate — this is someone's career.
- Resume and cover letter include ATS + anti-AI-detection rules.
"""

# ── Resume Parser ─────────────────────────────────────────────────────

PARSE_RESUME = """You are a resume parser. Extract structured information from the resume below.

RULES:
- Extract ONLY what is explicitly stated. Do not infer or fabricate.
- For skills, include both technical skills and tools/frameworks mentioned.
- For experience, capture each role with its key accomplishments.
- Estimate total years of experience from the work history dates.
- For city, extract ONLY the city name (not street, not postal code).
- For suggested_roles, suggest 3-5 realistic job titles based on the person's skills, experience level, and career trajectory.
- For nearby_cities, suggest 3-4 cities that are within reasonable commuting distance or are major tech hubs near the person's location.

RESUME:
{resume_text}

Respond with ONLY valid JSON matching this schema (no markdown, no backticks):
{{
    "name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "summary": "1-2 sentence professional summary based on the resume",
    "skills": ["skill1", "skill2"],
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "duration": "Start - End",
            "highlights": ["key accomplishment 1", "key accomplishment 2"]
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "School Name",
            "year": "Graduation year or range",
            "details": "Relevant coursework, honors, thesis"
        }}
    ],
    "projects": [
        {{
            "name": "Project Name",
            "description": "What it does in one sentence",
            "technologies": ["tech1", "tech2"]
        }}
    ],
    "years_of_experience": 0,
    "city": "just the city name, e.g. Braunschweig or San Francisco",
    "suggested_roles": ["3-5 job titles this person should target"],
    "nearby_cities": ["3-4 nearby cities or tech hubs within commuting distance"]
}}"""


# ── Job Scorer ────────────────────────────────────────────────────────

SCORE_JOB = """You are a job-match analyst. Score how well this candidate matches this job.

CANDIDATE PROFILE:
- Skills: {skills}
- Years of experience: {years_experience}
- Location: {candidate_location}
- Target roles: {target_roles}
- Preferred locations: {preferred_locations}
- Salary range: {salary_range}
- Remote preference: {remote_preference}

JOB POSTING:
Title: {job_title}
Company: {job_company}
Location: {job_location}
Remote type: {job_remote_type}
Salary: {job_salary}

Full description:
{job_text}

SCORING INSTRUCTIONS:
Score each dimension 0-100:
- skill_match: What percentage of required/preferred skills does the candidate have?
- experience_match: Does their seniority level fit? (junior for senior role = low, etc.)
- location_match: 100 if location matches or job is remote and they want remote. 50 if relocatable. 0 if mismatch.
- salary_fit: 100 if job salary overlaps candidate's range. 50 if close. 0 if way off or unknown (default to 70 if both are unspecified).
- culture_fit: Based on job description tone, company type, and candidate preferences. Default to 60 if insufficient signal.

overall_score = weighted average: skill_match*0.35 + experience_match*0.25 + location_match*0.15 + salary_fit*0.10 + culture_fit*0.15

is_worth_applying: true if overall_score >= {threshold} AND no absolute dealbreakers exist.

Respond with ONLY valid JSON (no markdown, no backticks):
{{
    "overall_score": 0,
    "skill_match": 0,
    "experience_match": 0,
    "location_match": 0,
    "salary_fit": 0,
    "culture_fit": 0,
    "reasoning": "2-3 sentences explaining the score",
    "matching_skills": ["skills the candidate has that the job wants"],
    "missing_skills": ["skills the job wants that the candidate lacks"],
    "is_worth_applying": false
}}"""


# ── Company Researcher ────────────────────────────────────────────────

RESEARCH_COMPANY = """You are a company research analyst preparing intelligence for a job applicant.

Using the search results below, compile a research brief about {company_name}.

SEARCH RESULTS:
{search_results}

Focus on information that helps a candidate:
1. Write a compelling cover letter (recent news, products, mission)
2. Prepare for interviews (culture, tech stack, challenges)
3. Decide if this is a good place to work (reviews, growth, stability)

RULES:
- Only include information supported by the search results.
- If information is unavailable, say "Not found" — do not guess.
- Prioritize recent information (last 12 months).

Respond with ONLY valid JSON (no markdown, no backticks):
{{
    "company_name": "{company_name}",
    "description": "What the company does in 2-3 sentences",
    "industry": "Primary industry",
    "founded": "Year or 'Not found'",
    "employee_count": "Approximate count or range, or 'Not found'",
    "funding_info": "Latest funding round/valuation or 'Not found'",
    "recent_news": ["Recent headline 1", "Recent headline 2", "Recent headline 3"],
    "products_services": ["Main product/service 1", "Main product/service 2"],
    "tech_stack": ["Known technologies they use"],
    "culture_summary": "2-3 sentences about work culture based on available info",
    "key_people": ["CEO/CTO name and title if found"],
    "interview_insights": "Any info about their interview process if available"
}}"""


# ── Resume Tailor (ATS + Humanized) ───────────────────────────────────

TAILOR_RESUME = """You are a professional resume writer who creates ATS-optimized, human-sounding resumes.

ORIGINAL RESUME:
{resume_text}

PARSED SKILLS: {skills}
MATCHING SKILLS (from job analysis): {matching_skills}
MISSING SKILLS: {missing_skills}

TARGET JOB:
Title: {job_title}
Company: {job_company}
Description:
{job_text}

ATS FORMATTING RULES (MANDATORY):
Structure the resume EXACTLY in this order with these EXACT section headings:
1. Candidate name (top, centered)
2. One-line subtitle matching the target job title
3. Contact line: email | phone | location | linkedin | github (pipe-separated)
4. PROFESSIONAL PROFILE — 3-4 sentences as a paragraph, NOT a list
5. TECHNICAL SKILLS — grouped by category (Languages:, Frameworks:, Databases:, Tools:)
6. EXPERIENCE or PROJECTS — reverse chronological, each with bullet points
7. EDUCATION — degree, institution, dates, relevant coursework
8. LANGUAGES — if applicable

Format rules:
- Use ONLY these standard section headings. No creative names.
- NO tables, NO columns, NO text boxes, NO images, NO icons
- Bullet points use simple dashes (-), not special symbols
- Keep to 1 page of content (400-600 words)
- Output in clean Markdown format

ANTI-AI-DETECTION RULES (CRITICAL — the resume will be checked by AI detectors):

1. VARY SENTENCE STARTS — NOT every bullet with a power verb. Mix these structures:
   BAD: "Developed X. Implemented Y. Designed Z. Built A. Created B."
   GOOD: "Built X from scratch. The Y system needed a rethink — redesigned it to handle Z. Took ownership of A."

2. BE SPECIFIC, NOT INFLATED:
   BAD: "Spearheaded the development of a cutting-edge data pipeline"
   GOOD: "Built the data pipeline that processes 2M events/day"

3. BANNED WORDS (never use any of these):
   "Spearheaded", "Leveraged", "Orchestrated", "Facilitated", "Synergy",
   "Cutting-edge", "State-of-the-art", "Best-in-class", "World-class",
   "Passionate", "Self-starter", "Team player", "Go-getter", "Dynamic",
   "Proven track record", "Results-driven", "Detail-oriented",
   "Utilizing", "Impactful", "Innovative solutions"

4. NATURAL LANGUAGE:
   - Mix short bullets with longer ones (not all the same length)
   - Use contractions occasionally in the profile section ("I've built" not "I have built")
   - One bullet can start with context instead of a verb: "After the legacy system failed, rebuilt..."
   - Include actual tech names and versions where relevant

5. KEYWORD PLACEMENT:
   - Mirror the job posting's exact terminology
   - Place top keywords from the job description within the first third of the resume
   - Weave keywords into bullet points naturally, not just the skills list

CONTENT RULES:
- REORDER bullets so the most relevant for THIS role come first
- KEEP all facts identical — same companies, dates, achievements
- DO NOT fabricate experience, skills, or accomplishments
- DO NOT add skills the candidate does not have

Write the ATS-optimized, human-sounding tailored resume now:"""


# ── Cover Letter Writer (Humanized) ──────────────────────────────────

WRITE_COVER_LETTER = """You are writing a cover letter that sounds like a real person wrote it, not AI.

CANDIDATE:
Name: {candidate_name}
Summary: {candidate_summary}
Key matching skills: {matching_skills}

TARGET JOB:
Title: {job_title}
Company: {job_company}
Key requirements from description:
{job_text}

COMPANY RESEARCH:
{company_research}

STRUCTURE:
1. Opening: Show you actually know this company. Reference ONE specific thing — a recent product, a news item, something you noticed. Why THIS company.
2. Middle (1-2 paragraphs): Connect 2-3 of your strongest experiences to what the job needs. Use specific numbers and outcomes.
3. Closing: What you'd bring in your first 90 days. Clear call to action.

ANTI-AI-DETECTION RULES (CRITICAL — this will be checked by AI detectors):

1. BANNED PHRASES (never use any of these):
   "I am writing to express my interest", "passionate self-starter",
   "team player", "hit the ground running", "leverage my skills",
   "dynamic environment", "proven track record", "detail-oriented",
   "I am excited about the opportunity", "I believe I would be a great fit",
   "Furthermore", "Additionally", "Moreover", "In conclusion",
   "I look forward to hearing from you", the word "passionate"

2. NATURAL VOICE:
   - Write like you're emailing a smart colleague, not writing a formal letter
   - Vary paragraph lengths (short, then longer, then medium)
   - Use contractions at least twice ("I've", "it's", "that's", "wasn't")
   - Start one sentence mid-thought: "What stood out to me..." or "The part that grabbed me..."
   - Include ONE moment of genuine opinion or personality

3. AVOID PATTERNS:
   - Don't start 2+ paragraphs the same way
   - Don't use "Furthermore" / "Additionally" / "Moreover" — just start the next thought
   - Don't end with "I look forward to hearing from you"
   - Keep exclamation marks to zero
   - No more than one em dash in the entire letter

4. SPECIFICITY OVER FLATTERY:
   BAD: "I admire your company's innovative approach to technology"
   GOOD: "Your refurbished coffee machine program caught my eye — most competitors wouldn't take that risk"

Under 300 words. Every sentence earns its place.
Do not start with "Dear Hiring Manager" — use "Dear {job_company} team" or the specific team.
DO NOT fabricate anything about the candidate.

Write the cover letter now:"""


# ── Interview Prepper ─────────────────────────────────────────────────

PREP_INTERVIEW = """You are a senior interview coach. Generate a targeted interview prep guide.

CANDIDATE BACKGROUND:
{candidate_summary}
Skills: {skills}
Experience highlights:
{experience_highlights}

TARGET ROLE:
Title: {job_title}
Company: {job_company}
Key requirements:
{job_text}

COMPANY CONTEXT:
{company_context}

Generate an interview prep guide with these sections:

## Likely Technical Questions (5-7 questions)
Based on the job requirements and the candidate's background. Include a brief suggested talking point for each.

## Behavioral Questions (4-5 questions)
"Tell me about a time..." style questions tailored to what this role needs. Include which experience from the candidate's background to reference.

## Company-Specific Questions (3-4 questions)
Questions about the company's products, challenges, or recent developments that show the candidate did their homework.

## Questions YOU Should Ask Them (4-5 questions)
Thoughtful questions that demonstrate genuine interest and help the candidate evaluate fit. NOT generic questions — specific ones based on the research.

## Key Talking Points to Weave In
3-4 themes from the candidate's experience that should come up naturally regardless of what's asked.

Format as clean markdown. Be specific — generic interview advice is worthless."""