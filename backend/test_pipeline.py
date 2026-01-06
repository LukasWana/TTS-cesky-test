
from backend.cs_f5_pipeline import preprocess_czech_f5_text

text = "Ahoj světe, toto je zkouška s číslem 123 a zkratkou např. Mám se dobře."
print(f"Original: {text}")

processed = preprocess_czech_f5_text(
    text,
    language="cs",
    enable_dialect_conversion=False
)

print(f"Processed: {processed}")
