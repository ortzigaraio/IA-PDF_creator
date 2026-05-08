"""
run_batch.py — Entry point de ejecución.
"""
from dotenv import load_dotenv
load_dotenv()

from src.main import PrismaEngine
from src.config import settings

if __name__ == "__main__":
    motor = PrismaEngine()
    motor.run_batch_json(settings.JSON_PERFILES)
