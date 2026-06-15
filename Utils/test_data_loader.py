import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
TEST_DATA_PATH = BASE_DIR / "TestData" / "checkpoint_testdata.csv"
BASELINE_IMAGE_DIR = BASE_DIR / "Images"


REQUIRED_COLUMNS = [
    "TC_ID",
    "case_name",
    "case_id",
    "scan_type",
    "entry_flow",
    "caries_count",
    "occlusion_count",
    "baseline_image",
    "diagnosis_name",
    "treatment_name"
]


def parse_baseline_images(value: str) -> list[str]:
    if not value or not value.strip():
        return []

    return [image.strip().strip('"') for image in value.split(",") if image.strip()]


def load_checkpoint_test_data() -> list[dict]:
    with open(TEST_DATA_PATH, newline="", encoding="utf-8-sig") as file:
        rows = [
            row for row in csv.DictReader(file)
            if row.get("TC_ID") and row.get("case_name")
        ]

    if not rows:
        raise ValueError("Checkpoint test data is empty.")

    for column in REQUIRED_COLUMNS:
        if column not in rows[0]:
            raise ValueError(f"Missing required column: {column}")

    for row in rows:
        row["caries_count"] = int(row["caries_count"])
        row["occlusion_count"] = int(row["occlusion_count"])

        baseline_images = parse_baseline_images(row["baseline_image"])
        row["baseline_images"] = baseline_images
        row["baseline_image_paths"] = [
            str(BASELINE_IMAGE_DIR / image)
            for image in baseline_images
        ]

    return rows