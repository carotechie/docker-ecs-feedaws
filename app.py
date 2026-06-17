import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from flask import Flask, render_template
import feedparser

app = Flask(__name__)

AWS_RSS_URL = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"

CATEGORIES = {
    "AI / ML": [
        "bedrock", "sagemaker", "rekognition", "comprehend", "textract",
        "polly", "transcribe", "translate", "kendra", "lex", "forecast",
        "personalize", "deepracer", "neuron", "trainium", "inferentia",
        "generative", "llm", "model", "ai ", "ml ", "machine learning",
        "artificial intelligence", "foundation model", "titan",
    ],
    "Seguridad": [
        "iam", "kms", "secrets manager", "shield", "waf", "guardduty",
        "inspector", "macie", "security hub", "detective", "acm",
        "certificate", "firewall", "access control", "compliance",
        "encryption", "audit", "sso", "identity", "permission",
        "guardrail",
    ],
    "Data": [
        "s3", "redshift", "athena", "glue", "lake formation", "emr",
        "kinesis", "opensearch", "elasticsearch", "rds", "aurora",
        "dynamodb", "timestream", "database", "data lake", "analytics",
        "quicksight", "dms", "migration", "etl", "pipeline", "spark",
    ],
    "FinOps": [
        "cost", "billing", "savings", "pricing", "budget", "reserved",
        "spot instance", "compute optimizer", "trusted advisor",
        "cost explorer", "finops",
    ],
    "CloudOps": [
        "cloudwatch", "cloudtrail", "cloudformation", "systems manager",
        "config", "auto scaling", "elastic", "ec2", "lambda", "ecs",
        "eks", "fargate", "beanstalk", "codepipeline", "codebuild",
        "codecommit", "codedeploy", "devops", "monitoring", "logging",
        "container", "kubernetes", "serverless", "networking", "vpc",
        "route 53", "cloudfront", "api gateway",
    ],
}

CATEGORY_COLORS = {
    "AI / ML":    {"bg": "#6c3afc", "badge": "🤖"},
    "Seguridad":  {"bg": "#e53e3e", "badge": "🔒"},
    "Data":       {"bg": "#2b8a3e", "badge": "🗄️"},
    "FinOps":     {"bg": "#d97706", "badge": "💰"},
    "CloudOps":   {"bg": "#0073bb", "badge": "☁️"},
    "General":    {"bg": "#6b7280", "badge": "🔧"},
}


def strip_html(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_category(title: str, summary: str) -> str:
    haystack = (title + " " + summary).lower()
    for category, keywords in CATEGORIES.items():
        if any(kw in haystack for kw in keywords):
            return category
    return "General"


def parse_published(entry) -> tuple[str, str | None]:
    """Returns (display_string, relative_string)."""
    raw = entry.get("published", "")
    if not raw:
        return "", None
    try:
        dt = parsedate_to_datetime(raw)
        dt_utc = dt.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt_utc
        days = delta.days
        hours = delta.seconds // 3600

        if days == 0 and hours == 0:
            relative = "hace menos de 1 hora"
        elif days == 0:
            relative = f"hace {hours} hora{'s' if hours > 1 else ''}"
        elif days == 1:
            relative = "hace 1 día"
        elif days < 30:
            relative = f"hace {days} días"
        else:
            months = days // 30
            relative = f"hace {months} mes{'es' if months > 1 else ''}"

        display = dt_utc.strftime("%-d %b %Y, %H:%M UTC")
        return display, relative
    except Exception:
        return raw, None


@app.route("/")
def index():
    feed = feedparser.parse(AWS_RSS_URL)
    fetched_at = datetime.now(timezone.utc).strftime("%-d %b %Y a las %H:%M UTC")

    items = []
    for entry in feed.entries[:20]:
        title = entry.title
        raw_summary = entry.get("summary", "")
        clean_summary = strip_html(raw_summary)
        display_date, relative = parse_published(entry)
        category = detect_category(title, clean_summary)

        items.append({
            "title": title,
            "link": entry.link,
            "published": display_date,
            "relative": relative,
            "summary": clean_summary[:280],
            "category": category,
            "cat_color": CATEGORY_COLORS[category]["bg"],
            "cat_badge": CATEGORY_COLORS[category]["badge"],
        })

    return render_template("index.html", items=items, fetched_at=fetched_at)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
