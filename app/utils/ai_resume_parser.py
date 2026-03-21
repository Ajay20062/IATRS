"""
Advanced AI-powered resume parsing and analysis utilities.
"""
import re
from pathlib import Path
from typing import Optional

try:
    import spacy
    from rank_bm25 import BM25Okapi
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Load spaCy model
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Model not installed, will need to download
        nlp = None
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None


# Common tech skills database
SKILLS_DATABASE = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "go", "rust", "ruby", "php", "swift", "kotlin",
    "scala", "r", "matlab", "sql", "html", "css", "sass", "less",
    
    # Frameworks & Libraries
    "react", "angular", "vue", "svelte", "next.js", "nuxt", "django", "flask", "fastapi",
    "spring", "hibernate", "express", "nest", "laravel", "rails", "tensorflow", "pytorch",
    "keras", "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn",
    
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb",
    "sqlite", "oracle", "mssql", "firebase", "supabase",
    
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins",
    "gitlab ci", "github actions", "circleci", "prometheus", "grafana", "datadog",
    
    # Tools & Platforms
    "git", "svn", "jira", "confluence", "slack", "notion", "figma", "postman",
    "linux", "unix", "windows", "macos",
    
    # Methodologies
    "agile", "scrum", "kanban", "devops", "ci/cd", "tdd", "bdd", "microservices",
    "rest", "graphql", "grpc",
    
    # Soft Skills
    "leadership", "communication", "teamwork", "problem solving", "critical thinking",
    "time management", "adaptability", "creativity", "emotional intelligence",
}

# Education level patterns
EDUCATION_PATTERNS = {
    "phd": r"(ph\.?d|doctor of philosophy|doctorate)",
    "masters": r"(m\.?s\.?|m\.?tech|m\.?eng|masters?|mba|m\.?b\.?a\.?)",
    "bachelors": r"(b\.?s\.?|b\.?tech|b\.?eng|bachelors?|b\.?a\.?|b\.?com)",
    "diploma": r"(diploma|associate)",
    "high_school": r"(high school|secondary|10th|12th)",
}


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return None


def extract_text_from_docx(file_path: str) -> Optional[str]:
    """Extract text from DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception:
        return None


def extract_text_from_file(file_path: str) -> Optional[str]:
    """Extract text from resume file based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".txt":
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def extract_skills(text: str) -> list[str]:
    """Extract skills from resume text."""
    text_lower = text.lower()
    found_skills = []
    
    for skill in SKILLS_DATABASE:
        # Use word boundaries for accurate matching
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    
    return sorted(list(set(found_skills)))


def extract_education(text: str) -> list[dict]:
    """Extract education information from resume text."""
    education_list = []
    
    for level, pattern in EDUCATION_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context (university name, year, etc.)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            education_list.append({
                "level": level,
                "context": context,
                "position": match.start()
            })
    
    # Sort by education level (highest first)
    level_order = {"phd": 0, "masters": 1, "bachelors": 2, "diploma": 3, "high_school": 4}
    education_list.sort(key=lambda x: level_order.get(x["level"], 5))
    
    return education_list


def extract_experience(text: str) -> dict:
    """Extract work experience information."""
    # Look for years of experience patterns
    exp_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?\.?)\s*(?:of\s*)?(?:work|professional|industry)?\s*experience',
        r'(?:work|professional|industry)?\s*experience\s*[:\-]?\s*(\d+)\+?\s*(?:years?|yrs?\.?)',
        r'(\d{4})\s*[-–]\s*(?:present|now|current|\d{4})',
    ]
    
    years = 0
    for pattern in exp_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                try:
                    if len(match) == 4:  # Year format
                        continue
                    years = max(years, int(match))
                except ValueError:
                    continue
    
    # Extract job titles
    job_title_pattern = r'(?:position|title|role)[:\s]+([^\n]+)'
    job_titles = re.findall(job_title_pattern, text, re.IGNORECASE)
    
    # Extract company names (capitalized words followed by Inc, Ltd, etc.)
    company_pattern = r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Ltd|LLC|Corp|Company|Technologies|Solutions))'
    companies = re.findall(company_pattern, text)
    
    return {
        "years": years,
        "job_titles": job_titles[:5],  # Limit to 5
        "companies": list(set(companies))[:5],  # Limit to 5 unique
    }


def extract_contact_info(text: str) -> dict:
    """Extract contact information from resume."""
    # Email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Phone
    phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{6,15}'
    phones = re.findall(phone_pattern, text)
    
    # LinkedIn
    linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/profile\?id=)([A-Za-z0-9_-]+)'
    linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
    
    # GitHub
    github_pattern = r'(?:github\.com/|github\.com/profile\?user=)([A-Za-z0-9_-]+)'
    github = re.findall(github_pattern, text, re.IGNORECASE)
    
    return {
        "emails": list(set(emails)),
        "phones": list(set(phones)),
        "linkedin": linkedin[0] if linkedin else None,
        "github": github[0] if github else None,
    }


def parse_resume(file_path: str) -> dict:
    """Complete resume parsing function."""
    text = extract_text_from_file(file_path)
    if not text:
        return {"error": "Could not extract text from file"}
    
    return {
        "text": text,
        "skills": extract_skills(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
        "contact_info": extract_contact_info(text),
    }


def calculate_resume_score(resume_data: dict) -> int:
    """Calculate a resume score based on extracted information."""
    score = 0
    
    # Skills score (max 40)
    skills_count = len(resume_data.get("skills", []))
    score += min(40, skills_count * 3)
    
    # Education score (max 25)
    education = resume_data.get("education", [])
    if education:
        level_scores = {"phd": 25, "masters": 20, "bachelors": 15, "diploma": 10, "high_school": 5}
        score += level_scores.get(education[0]["level"], 0)
    
    # Experience score (max 25)
    experience = resume_data.get("experience", {})
    years = experience.get("years", 0)
    score += min(25, years * 3)
    
    # Contact info completeness (max 10)
    contact = resume_data.get("contact_info", {})
    if contact.get("emails"):
        score += 3
    if contact.get("phones"):
        score += 3
    if contact.get("linkedin"):
        score += 2
    if contact.get("github"):
        score += 2
    
    return min(100, score)


def calculate_job_candidate_match(job_description: str, resume_data: dict) -> dict:
    """Calculate match score between job description and candidate resume."""
    job_lower = job_description.lower()
    
    # Extract required skills from job description
    required_skills = []
    for skill in SKILLS_DATABASE:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, job_lower):
            required_skills.append(skill)
    
    candidate_skills = set(resume_data.get("skills", []))
    required_skills_set = set(required_skills)
    
    # Calculate skill match percentage
    if required_skills_set:
        matched_skills = candidate_skills.intersection(required_skills_set)
        skill_match_percentage = (len(matched_skills) / len(required_skills_set)) * 100
    else:
        skill_match_percentage = 50  # Default if no specific skills mentioned
    
    # Calculate experience match
    candidate_experience = resume_data.get("experience", {}).get("years", 0)
    
    # Look for experience requirements in job description
    exp_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?\.?)\s*experience', job_lower)
    if exp_matches:
        required_experience = max([int(m) for m in exp_matches])
        experience_match = min(100, (candidate_experience / required_experience) * 100)
    else:
        experience_match = 50  # Default
    
    # Calculate overall match score
    overall_match = (skill_match_percentage * 0.6) + (experience_match * 0.4)
    
    return {
        "match_score": round(overall_match, 2),
        "skill_match_percentage": round(skill_match_percentage, 2),
        "experience_match_percentage": round(experience_match, 2),
        "matched_skills": list(candidate_skills.intersection(required_skills_set)),
        "missing_skills": list(required_skills_set - candidate_skills),
        "candidate_skills": list(candidate_skills),
        "required_skills": list(required_skills_set),
    }


def rank_candidates(job_description: str, candidates_data: list[dict]) -> list[dict]:
    """Rank multiple candidates based on job description using BM25 and cosine similarity."""
    if not candidates_data:
        return []
    
    # Prepare documents for BM25
    documents = []
    for candidate in candidates_data:
        doc_text = " ".join([
            candidate.get("text", ""),
            " ".join(candidate.get("skills", [])),
            candidate.get("experience", {}).get("job_titles", [""])[0] if candidate.get("experience", {}).get("job_titles") else "",
        ])
        documents.append(doc_text)
    
    # BM25 ranking
    bm25 = BM25Okapi([doc.split() for doc in documents])
    query = job_description.split()
    bm25_scores = bm25.get_scores(query)
    
    # TF-IDF + Cosine Similarity
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
        query_vector = vectorizer.transform([job_description])
        cosine_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()
    except Exception:
        cosine_scores = bm25_scores  # Fallback
    
    # Combined score (BM25 + Cosine)
    combined_scores = (bm25_scores + cosine_scores) / 2
    
    # Create ranked results
    ranked_results = []
    for idx, (candidate, score) in enumerate(zip(candidates_data, combined_scores)):
        match_data = calculate_job_candidate_match(job_description, candidate)
        ranked_results.append({
            "candidate_index": idx,
            "combined_score": round(float(score), 4),
            "match_score": match_data["match_score"],
            "skills": candidate.get("skills", []),
            "experience_years": candidate.get("experience", {}).get("years", 0),
            "education": candidate.get("education", []),
        })
    
    # Sort by combined score descending
    ranked_results.sort(key=lambda x: x["combined_score"], reverse=True)
    
    return ranked_results
