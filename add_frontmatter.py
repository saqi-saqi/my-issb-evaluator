import json
from pathlib import Path

kb_dir = Path("knowledge_base")

# 1. Official files
official_meta = {
    "candidate_guidelines.txt": {
        "source_type": "official",
        "dimension": "general",
        "topic": "candidate_guidelines",
        "authority_level": 1,
        "title": "Official Candidate Guidelines and Core Qualities",
    },
    "four_day_schedule.txt": {
        "source_type": "official",
        "dimension": "general",
        "topic": "testing_schedule",
        "authority_level": 1,
        "title": "Official ISSB Four-Day Selection Schedule",
    },
    "fourteen_olqs.txt": {
        "source_type": "official",
        "dimension": "general",
        "topic": "fourteen_olqs",
        "authority_level": 1,
        "title": "Official ISSB Taxonomy - The 14 Officer Like Qualities (OLQs)",
    },
    "selection_dimensions.txt": {
        "source_type": "official",
        "dimension": "general",
        "topic": "selection_dimensions",
        "authority_level": 1,
        "title": "Official Selection Dimensions - Deputy President and Psychologist",
    },
    "selection_system.txt": {
        "source_type": "official",
        "dimension": "general",
        "topic": "selection_system",
        "authority_level": 1,
        "title": "Official ISSB Selection System and Philosophy",
    },
}

# 2. Academic files
academic_meta = {
    "emotional_regulation_stress.md": {
        "source_type": "academic",
        "dimension": "psychologist",
        "topic": "emotional_regulation_stress",
        "authority_level": 2,
        "title": "Academic Research: Emotional Regulation and Cognitive Resilience Under Stress",
    },
    "leadership_competencies.md": {
        "source_type": "academic",
        "dimension": "deputy_president",
        "topic": "leadership_competencies",
        "authority_level": 2,
        "title": "Academic Research: Leadership Competencies and Small Group Dynamics",
    },
    "military_psychology_and_selection.md": {
        "source_type": "academic",
        "dimension": "general",
        "topic": "military_psychology_and_selection",
        "authority_level": 2,
        "title": "Academic Research: Military Psychology, Assessment Centers and Predictive Validity",
    },
    "situational_judgment_theory.md": {
        "source_type": "academic",
        "dimension": "deputy_president",
        "topic": "situational_judgment_theory",
        "authority_level": 2,
        "title": "Academic Research: Situational Judgment Theory in Officer Selection",
    },
}

# 3. Evaluation files
evaluation_meta = {
    "communication.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "communication",
        "authority_level": 3,
        "title": "Evaluation Rubric: Communication and Expression",
    },
    "confidence_initiative.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "confidence_initiative",
        "authority_level": 3,
        "title": "Evaluation Rubric: Self-Confidence and Initiative",
    },
    "decision_making.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "decision_making",
        "authority_level": 3,
        "title": "Evaluation Rubric: Decision Making and Situational Judgment",
    },
    "general_knowledge_intellect.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "general_knowledge_intellect",
        "authority_level": 3,
        "title": "Evaluation Rubric: General Knowledge and Intellectual Faculty",
    },
    "integrity_responsibility.md": {
        "source_type": "evaluation",
        "dimension": "psychologist",
        "topic": "integrity_responsibility",
        "authority_level": 3,
        "title": "Evaluation Rubric: Integrity, Responsibility and Moral Foundation",
    },
    "leadership.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "leadership",
        "authority_level": 3,
        "title": "Evaluation Rubric: Leadership and Responsibility",
    },
    "motivation.md": {
        "source_type": "evaluation",
        "dimension": "psychologist",
        "topic": "motivation",
        "authority_level": 3,
        "title": "Evaluation Rubric: Service Motivation and Authentic Drive",
    },
    "stress_response.md": {
        "source_type": "evaluation",
        "dimension": "psychologist",
        "topic": "stress_response",
        "authority_level": 3,
        "title": "Evaluation Rubric: Stress Response, Poise and Emotional Stability",
    },
    "teamwork.md": {
        "source_type": "evaluation",
        "dimension": "deputy_president",
        "topic": "teamwork",
        "authority_level": 3,
        "title": "Evaluation Rubric: Teamwork, Social Adaptability and Peer Cohesion",
    },
}

# 4. Preparation files
prep_meta = {
    "dos_and_donts.txt": {
        "source_type": "preparation",
        "dimension": "general",
        "topic": "dos_and_donts",
        "authority_level": 3,
        "title": "ISSB Interview Do's and Don'ts",
    },
    "interview_preparation_guidance.txt": {
        "source_type": "preparation",
        "dimension": "general",
        "topic": "interview_preparation_guidance",
        "authority_level": 3,
        "title": "ISSB Interview Preparation Guidance",
    },
}

def apply_frontmatter(file_path: Path, meta: dict):
    content = file_path.read_text(encoding="utf-8")
    # If frontmatter already exists, strip it
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    frontmatter = "---\n"
    for k, v in meta.items():
        frontmatter += f"{k}: {v}\n"
    frontmatter += "---\n\n"
    
    file_path.write_text(frontmatter + content, encoding="utf-8")
    print(f"Updated frontmatter for {file_path}")

for filename, meta in official_meta.items():
    p = kb_dir / "official" / filename
    if p.exists():
        apply_frontmatter(p, meta)

for filename, meta in academic_meta.items():
    p = kb_dir / "academic" / filename
    if p.exists():
        apply_frontmatter(p, meta)

for filename, meta in evaluation_meta.items():
    p = kb_dir / "evaluation" / filename
    if p.exists():
        apply_frontmatter(p, meta)

for filename, meta in prep_meta.items():
    p = kb_dir / "preparation" / filename
    if p.exists():
        apply_frontmatter(p, meta)

# 5. Current Affairs JSON files: update dimension to general_knowledge
ca_dir = kb_dir / "current_affairs"
for p in ca_dir.glob("*.json"):
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["dimension"] = "general_knowledge"
    data["authority_level"] = 4
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Updated current affairs dimension in {p}")
