# central/backend/run_consumer.py
import logging
from services.kafka_consumer_service import CoreEventConsumer
from services.escalation_service import EscalationWorker

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    escalation_worker = EscalationWorker(timeout_seconds=15)
    escalation_worker.start()
    
    # Run the ingestion loop
    worker = CoreEventConsumer()

    try:
        worker.run()
    except KeyboardInterrupt:
        logging.info("Shutting down core services...")
    finally:
        escalation_worker.stop()