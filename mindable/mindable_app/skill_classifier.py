"""
Technology-agnostic technical skill detection for job matching.

Uses a broad lexicon plus simple patterns (languages, frameworks, tools, platforms, domains).
Does not favor a single industry — any listed token can be extended via profile analysis.
"""
from __future__ import annotations

import re
from typing import Iterable

# Broad, multi-domain indicators — extend over time; not an exhaustive ontology.
_TECH_LEXICON: frozenset[str] = frozenset({
    # Languages & runtimes
    "python", "javascript", "typescript", "java", "kotlin", "swift", "scala", "rust", "go", "golang",
    "ruby", "php", "perl", "r", "csharp", "c#", "c++", "cpp", "objective-c", "dart", "elixir", "erlang",
    "haskell", "clojure", "lua", "matlab", "octave", "solidity", "vba", "sql", "plsql", "tsql",
    # Web / mobile
    "html", "html5", "css", "scss", "sass", "less", "react", "reactjs", "react.js", "vue", "vuejs",
    "angular", "svelte", "nextjs", "next.js", "nuxt", "remix",     "webpack", "vite", "babel", "nodejs",
    "node.js", "express", "django", "flask", "fastapi", "rails", "laravel", "symfony", "spring",
    "springboot", "aspnet", ".net", "dotnet", "xamarin", "flutter", "ionic", "electron",
    # Data / ML / AI
    "tensorflow", "pytorch", "keras", "scikit", "sklearn", "pandas", "numpy", "scipy", "spark",
    "pyspark", "hadoop", "kafka", "airflow", "dbt", "snowflake", "databricks", "bigquery", "redshift",
    "etl", "machine", "learning", "deep", "nlp", "llm", "opencv", "xgboost", "jupyter",
    # Infra / cloud / DevOps
    "aws", "gcp", "azure", "kubernetes", "k8s", "docker", "terraform", "ansible", "jenkins", "gitlab",
    "github", "ci", "cd", "devops", "sre", "linux", "unix", "bash", "nginx", "istio", "helm",
    "prometheus", "grafana", "elasticsearch",     "mongodb", "redis", "postgres", "postgresql", "mysql",
    "mariadb", "oracle", "sqlite", "cassandra", "dynamodb", "graphql", "grpc", "rest", "openapi",
    "microservices", "serverless", "lambda", "cloudformation",
    "machine learning", "deep learning", "artificial intelligence", "data science", "computer vision",
    "natural language processing", "reinforcement learning", "feature engineering",
    # Security
    "cybersecurity", "pentesting", "siem", "oauth", "oauth2", "ldap", "vpn", "zerotrust",
    # Design / product (technical tooling)
    "figma", "sketch", "xd", "ux", "ui", "wireframing", "prototyping", "accessibility", "wcag",
    # Engineering disciplines (when they appear as competencies)
    "backend", "frontend", "fullstack", "full-stack", "embedded", "firmware", "robotics", "iot",
    "blockchain", "ethereum", "cad", "fpga", "verilog", "vhdl", "pcb", "api", "sdk", "cli",
})

_TECH_SUFFIX = re.compile(
    r"(\+{2}|#|\.js|\.ts|\.net|\.py|\.rb|\.go|\.rs)$",
    re.IGNORECASE,
)


def _normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", (term or "").strip().lower())


def is_technical_token(term: str) -> bool:
    """
    Return True if the token plausibly denotes a technical / domain-specific competency.
    """
    t = _normalize_term(term)
    if len(t) < 2:
        return False
    if t in _TECH_LEXICON:
        return True
    # Multi-word: technical only if every token is in the lexicon (avoid recursive explosion).
    parts = [p for p in re.split(r"[\s/]+", t) if p]
    if len(parts) > 1 and all(p in _TECH_LEXICON for p in parts):
        return True
    if _TECH_SUFFIX.search(t):
        return True
    # Short codes with digits (e.g. k8s, s3-style) — length 2–6
    if 2 <= len(t) <= 8 and any(ch.isdigit() for ch in t) and re.match(r"^[a-z0-9.\-+]+$", t):
        return True
    return False


def split_technical_general(skills: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split a flat skill list into technical vs general (non-technical) strings."""
    tech: list[str] = []
    general: list[str] = []
    seen_t: set[str] = set()
    seen_g: set[str] = set()
    for raw in skills:
        s = _normalize_term(str(raw))
        if not s or len(s) < 2:
            continue
        if is_technical_token(s):
            if s not in seen_t:
                seen_t.add(s)
                tech.append(s)
        else:
            if s not in seen_g:
                seen_g.add(s)
                general.append(s)
    return tech, general
