"""
AutoApply prompt templates.

Design philosophy:
- Each prompt asks for ONE specific output format (JSON or prose, never both).
- JSON prompts include the exact schema to reduce hallucinated fields.
- Prose prompts include word counts to prevent rambling.
- Every prompt reminds the LLM not to fabricate — this is someone's career.
"""

# ── Resume Parser ─────────────────────────────────────────────────────

PARSE_RESUME = """You are a resume parser. Extract structured information from the resume below.

RULES:
- Extract ONLY what is explicitly stated. Do not infer or fabricate.
- For skills, include both technical skills and tools/frameworks mentioned.
- For experience, capture each role with its key accomplishments.
- Estimate total years of experience from the work history dates.

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
    "years_of_experience": 0
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


# ── Resume Tailor ─────────────────────────────────────────────────────

TAILOR_RESUME = """You are an expert resume writer. Tailor this resume for a specific job application.

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

TAILORING INSTRUCTIONS:
1. REORDER bullet points so the most relevant accomplishments for THIS role appear first.
2. ADJUST KEYWORDS to match the job description terminology (e.g., if they say "CI/CD" and the resume says "continuous deployment", use "CI/CD").
3. EMPHASIZE projects and experience most relevant to this specific role.
4. STRENGTHEN the summary/objective to target this exact position.
5. KEEP all factual information identical — same companies, same dates, same achievements.

CRITICAL RULES:
- DO NOT fabricate experience, skills, or accomplishments.
- DO NOT remove jobs or education — only reorder and re-emphasize.
- DO NOT add skills the candidate does not have.
- If the candidate is missing key skills, that's fine — a tailored resume highlights strengths, it doesn't lie.
- Output should be in clean markdown format, ready to convert to PDF.
- Keep it to 1 page worth of content (roughly 400-600 words).

Write the tailored resume now:"""


# ── Cover Letter Writer ───────────────────────────────────────────────

WRITE_COVER_LETTER = """You are an expert cover letter writer. Write a personalized cover letter.

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

COVER LETTER REQUIREMENTS:
1. Opening paragraph: Show genuine knowledge of the company. Reference a specific recent development, product, or mission element from the research. Explain why THIS company excites you.
2. Middle paragraph(s): Connect 2-3 of the candidate's strongest relevant experiences directly to the job requirements. Use specific accomplishments with numbers where available.
3. Closing paragraph: Express enthusiasm, mention what you'd bring to the team, and include a call to action.

STYLE RULES:
- Professional but conversational — not stiff or generic.
- Under 350 words. Hiring managers skim.
- No clichés: avoid "I am writing to express my interest", "passionate self-starter", "team player", "hit the ground running".
- Do not start with "Dear Hiring Manager" — use "Dear [Company] team" or the specific team name if known.
- DO NOT fabricate anything about the candidate. Only reference real experience from their resume.

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

## Likely technical questions (5-7 questions)
Based on the job requirements and the candidate's background. Include a brief suggested talking point for each.

## Behavioral questions (4-5 questions)
"Tell me about a time..." style questions tailored to what this role needs. Include which experience from the candidate's background to reference.

## Company-specific questions (3-4 questions)
Questions about the company's products, challenges, or recent developments that show the candidate did their homework.

## Questions YOU should ask them (4-5 questions)
Thoughtful questions that demonstrate genuine interest and help the candidate evaluate if this is the right fit. NOT generic questions like "what's the culture like" — specific ones based on the research.

## Key talking points to weave in
3-4 themes from the candidate's experience that should come up naturally regardless of what's asked.

Format as clean markdown. Be specific — generic interview advice is worthless."""
