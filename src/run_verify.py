"""Point d'entrée pour le workflow de prédiction."""
import sys
from predict import run

if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else "morning"
    if session not in ("morning", "evening"):
        print("Usage: python run_predict.py [morning|evening]")
        sys.exit(1)
    print(f"=== GÉNÉRATION PRONOSTICS [{session.upper()}] ===")
    run(session)
