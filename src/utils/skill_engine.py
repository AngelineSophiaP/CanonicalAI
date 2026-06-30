import re
from typing import List

# Centralized Taxonomy
CANONICAL_TAXONOMY = {
    # Languages
    "python", "java", "sql", "postgresql", "mongodb", "hadoop", 
    "docker", "git", "snowflake", "apache kafka", "tableau", 
    "power bi", "qlik sense", "esp32", "tinyml", "javascript", 
    "typescript", "react", "aws", "azure", "gcp", "linux", 
    "kubernetes", "r", "perl", "scala", "c++", "rust", "go", 
    "swift", "kotlin", "dart", "html", "css", "php", "c#", 
    "csharp", "cpp", "golang", "ruby", "rails", "ruby on rails",
    
    # Frameworks & Libraries
    "next.js", "nextjs", "angular", "angularjs", "vue", "vue.js", 
    "vuejs", "svelte", "react native", "node.js", "nodejs", "node", 
    "express.js", "express", "nestjs", "nest.js", "django", "flask", 
    "fastapi", "spring boot", "spring", "asp.net", "laravel",
    
    # Databases & Big Data
    "mysql", "sqlite", "redis", "cassandra", "elasticsearch", 
    "neo4j", "mariadb", "dynamodb", "oracle", "mssql", "sql server", 
    "firestore", "supabase", "bigquery", "redshift", "apache spark", 
    "spark", "hive", "pig", "flink", "dbt", "airflow", "apache airflow", 
    "kafka",
    
    # Machine Learning & AI
    "machine learning", "deep learning", "data mining", "signal processing",
    "natural language processing", "nlp", "computer vision", "pattern recognition",
    "artificial intelligence", "ai", "reinforcement learning", "generative ai",
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", 
    "numpy", "scipy", "matplotlib", "seaborn", "langchain", "llamaindex", 
    "transformers", "huggingface", "openai", "spacy", "nltk", "opencv",
    
    # DevOps, Cloud & Systems
    "jenkins", "github actions", "gitlab ci", "ansible", "terraform",
    "cloudformation", "ubuntu", "debian", "redhat", "centos", "nginx", 
    "apache", "prometheus", "grafana", "elk stack", "datadog",
    
    # Hardware, IoT & Tools
    "arduino", "raspberry pi", "microcontrollers", "iot", 
    "embedded systems", "verilog", "vhdl", "looker", "excel", 
    "jupyter", "jupyter notebook"
}

def extract_canonical_skills(text: str) -> List[str]:
    """
    Strict rule-based matching: returns canonical skills found in the text.
    Uses custom boundaries that support special characters (like +, #).
    """
    if not text:
        return []
        
    text_lower = text.lower()
    found_canonical = set()
    
    # Sort taxonomy by length (descending) to match multi-word phrases before sub-parts
    sorted_taxonomy = sorted(CANONICAL_TAXONOMY, key=len, reverse=True)
    
    remaining_text = text_lower
    for skill in sorted_taxonomy:
        escaped_skill = re.escape(skill)
        # Boundary pattern: starts with a word boundary, ends with string boundary or non-skill char
        pattern = rf"\b{escaped_skill}(?=$|[^a-zA-Z0-9_#+])"
        
        if re.search(pattern, remaining_text):
            found_canonical.add(skill)
            # Consume the matched term to prevent sub-part matching
            remaining_text = re.sub(pattern, " ", remaining_text)
            
    return sorted(list(found_canonical))