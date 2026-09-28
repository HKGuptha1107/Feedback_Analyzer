"""Synthetic sample feedback data generator for FlowDesk demo.
Generates realistic temporal patterns demonstrating the core before-and-after story:
- Pre-Release (Sep 1 - Oct 14, 2026): High frequency of upload latency and timeout complaints.
- Release Date (Oct 15, 2026): Release 3.2: Chunked Upload Optimizer.
- Post-Release (Oct 16 - Nov 15, 2026): Upload complaints drop drastically; positive praises for upload speeds; emerging requests for Dark Mode and CSV Export.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

CUSTOMERS = [
    ("cust-101", "Sarah Connor", "Cyberdyne Systems", "Enterprise"),
    ("cust-102", "Alex Rivera", "Rivera Media Labs", "Pro"),
    ("cust-103", "Chloe Bennett", "Starlight Visuals", "Enterprise"),
    ("cust-104", "Marcus Vance", "Vance Logic Corp", "Pro"),
    ("cust-105", "Elena Rostova", "Rostova Dynamics", "Enterprise"),
    ("cust-106", "David Kim", "Apex Automation", "Pro"),
    ("cust-107", "Maya Lin", "Zenith Design", "Free"),
    ("cust-108", "Liam O'Connor", "Emerald Cloud", "Enterprise"),
    ("cust-109", "Sophia Patel", "NexGen FinTech", "Pro"),
    ("cust-110", "Lucas Silva", "Horizon Logistics", "Free"),
    ("cust-111", "Amara Okafor", "Sahara Systems", "Enterprise"),
    ("cust-112", "Thomas Becker", "Bavaria Tech", "Pro"),
    ("cust-113", "Rachel Green", "Central Perk Studios", "Free"),
    ("cust-114", "Kenji Sato", "Tokyo Digital", "Enterprise"),
    ("cust-115", "Fatima Al-Sayed", "Gulf Analytics", "Pro"),
]

SOURCES = ["Support Ticket", "App Review", "Survey", "Email", "Feature Request", "Interview"]

# 1. Early Period Upload Complaints (Sep 1 - Oct 14)
EARLY_UPLOAD_COMPLAINTS = [
    ("Uploading 200MB video presentations fails consistently at 98%. We lost our client pitch deck.", 1, "Performance", "negative", -0.9),
    ("Large file uploads are painfully slow. Takes over 20 minutes for a 50MB PDF report.", 1, "Performance", "negative", -0.85),
    ("Upload failed: 'Network connection dropped' error message appears repeatedly when uploading design assets.", 2, "Performance", "negative", -0.75),
    ("Why does uploading screen recordings crash the tab? This is a severe blocker for our team.", 1, "Performance", "negative", -0.9),
    ("File uploads timeout after 60 seconds without giving any option to resume.", 1, "Performance", "negative", -0.8),
    ("Huge bottleneck trying to upload weekly marketing video assets. Speed is under 200kbps.", 2, "Performance", "negative", -0.75),
    ("Support ticket: Uploading files larger than 100MB constantly yields 504 Gateway Timeout.", 1, "Performance", "negative", -0.95),
    ("The dashboard is sleek, but file uploads are frustratingly sluggish.", 2, "Performance", "negative", -0.6),
    ("Can you please add a progress indicator or resume capability for large file uploads? It fails halfway through.", 2, "Feature Request", "negative", -0.5),
    ("Upload speeds degrade severely during peak working hours. It took 35 mins to upload our project zip.", 1, "Performance", "negative", -0.85),
    ("Uploading raw audio files failed three times today. Please fix the file transfer pipeline.", 1, "Performance", "negative", -0.9),
    ("We are on the Enterprise plan and file uploads keep timing out. Considering switching tools.", 1, "Performance", "negative", -0.95),
]

# 2. General Feedback throughout both periods
GENERAL_FEEDBACK = [
    ("Love the real-time collaboration canvas. Editing alongside my team is seamless.", 5, "Collaboration", "positive", 0.9),
    ("Slack integration works wonderfully for task assignment alerts.", 5, "Integrations", "positive", 0.85),
    ("The user interface is very clean and intuitive for onboarding new hires.", 4, "UI", "positive", 0.7),
    ("Search filters are quick and accurate when looking through archived tickets.", 5, "Search", "positive", 0.8),
    ("Pricing feels a bit steep for smaller startup teams under 10 members.", 3, "Pricing", "neutral", 0.0),
    ("Customer support responded within 15 minutes and resolved our billing inquiry.", 5, "Support", "positive", 0.9),
    ("Notifications can be slightly noisy during active brainstorming sessions.", 3, "Notifications", "neutral", -0.1),
    ("Would appreciate more webhook triggers for custom third-party integrations.", 4, "Feature Request", "positive", 0.5),
    ("Mobile responsive layout works well on iPad and tablet screens.", 4, "UI", "positive", 0.75),
    ("Occasional minor lag when loading 500+ items in a single kanban board.", 3, "Performance", "neutral", -0.3),
    ("The calendar sync with Google Workspace works without any hitches.", 5, "Integrations", "positive", 0.85),
    ("Role-based permission controls are straightforward to configure.", 4, "Security", "positive", 0.65),
]

# 3. Post-Release Upload Praises (Oct 16 - Nov 15)
POST_RELEASE_UPLOAD_FEEDBACK = [
    ("Tested the new file upload engine today with a 1.2GB video file. Uploaded in 18 seconds! Incredible improvement.", 5, "Performance", "positive", 0.95),
    ("Uploads are blazing fast now. The chunked upload optimization completely solved our team's timeout issues.", 5, "Performance", "positive", 0.9),
    ("Whatever you guys did to the upload pipeline in Release 3.2, thank you! It just works seamlessly.", 5, "Performance", "positive", 0.9),
    ("Uploading 500MB zip archives used to fail every time; now it finishes before I even switch tabs.", 5, "Performance", "positive", 0.85),
    ("The progress bar for multipart uploads is super smooth and reliable.", 4, "Performance", "positive", 0.8),
    ("Upload speed is finally at enterprise grade. Kudos to the engineering team.", 5, "Performance", "positive", 0.9),
]

# 4. Emerging Post-Release Requests (Oct 16 - Nov 15)
POST_RELEASE_EMERGING_REQUESTS = [
    ("We desperately need bulk CSV export for monthly analytics reports.", 2, "Reporting", "negative", -0.5),
    ("Please add dark mode! Late-night triage in FlowDesk is blindingly bright.", 3, "UI", "neutral", -0.2),
    ("Feature request: Bulk export of all ticket feedback to CSV or Parquet.", 4, "Feature Request", "positive", 0.4),
    ("Dark mode toggle would be a huge quality of life upgrade for developers.", 4, "UI", "positive", 0.5),
    ("Need the ability to export filtered views directly to CSV for executive presentations.", 3, "Reporting", "neutral", -0.1),
    ("Dark mode please! It is our entire design team's #1 requested feature.", 3, "UI", "neutral", -0.2),
]


def generate_dataset(output_path: Path):
    rows = []
    
    # 1. Early Period: Sep 1, 2026 to Oct 14, 2026 (44 days)
    start_date = date(2026, 9, 1)
    end_early = date(2026, 10, 14)
    early_days = (end_early - start_date).days

    # Generate 90 early upload complaints
    for _ in range(90):
        day_offset = random.randint(0, early_days)
        fb_date = start_date + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(EARLY_UPLOAD_COMPLAINTS)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # Generate 60 general feedback items in early period
    for _ in range(60):
        day_offset = random.randint(0, early_days)
        fb_date = start_date + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(GENERAL_FEEDBACK)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # 2. Post-Release Period: Oct 16, 2026 to Nov 15, 2026 (30 days)
    post_start = date(2026, 10, 16)
    post_end = date(2026, 11, 15)
    post_days = (post_end - post_start).days

    # Post-release praises for upload optimization (35 rows)
    for _ in range(35):
        day_offset = random.randint(0, post_days)
        fb_date = post_start + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(POST_RELEASE_UPLOAD_FEEDBACK)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # Lingering or minor upload complaints (only 6 rows, proving sharp decline!)
    for _ in range(6):
        day_offset = random.randint(0, post_days)
        fb_date = post_start + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(EARLY_UPLOAD_COMPLAINTS)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # Emerging requests: Dark Mode and Bulk Export (45 rows)
    for _ in range(45):
        day_offset = random.randint(0, post_days)
        fb_date = post_start + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(POST_RELEASE_EMERGING_REQUESTS)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # General feedback post-release (40 rows)
    for _ in range(40):
        day_offset = random.randint(0, post_days)
        fb_date = post_start + timedelta(days=day_offset)
        cust = random.choice(CUSTOMERS)
        text, rating, cat, sent, score = random.choice(GENERAL_FEEDBACK)
        source = random.choice(SOURCES)
        rows.append({
            "customer_id": cust[0],
            "customer_name": cust[1],
            "source": source,
            "feedback_text": text,
            "rating": rating,
            "category": cat,
            "sentiment": sent,
            "sentiment_score": score,
            "date": fb_date.isoformat(),
            "product": "flowdesk",
        })

    # Sort rows chronologically
    rows.sort(key=lambda r: r["date"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "customer_id",
                "customer_name",
                "source",
                "feedback_text",
                "rating",
                "category",
                "sentiment",
                "sentiment_score",
                "date",
                "product",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} curated sample feedback records to {output_path}")


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent / "sample_feedback.csv"
    generate_dataset(out_file)
