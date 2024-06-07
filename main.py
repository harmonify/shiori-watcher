import os
import psycopg2
import select
import docker
import logging


DATABASE_CONFIG = {
    "dbname": os.getenv("DB_NAME", "mydb"),
    "user": os.getenv("DB_USER", "myuser"),
    "password": os.getenv("DB_PASSWORD", "mypassword"),
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
}

ARCHIVEBOX_CONTAINER_NAME = os.getenv(
    "ARCHIVEBOX_CONTAINER_NAME", "compose_archivebox_1"
)
DATA_DIR = os.getenv("DATA_DIR", "/data")
LOGS_DIR = os.getenv("LOGS_DIR", "/logs")
LOG_FILE_PATH = os.path.join(LOGS_DIR, "run.log")
URLS_FILE_PATH = os.path.join(DATA_DIR, "new_urls.txt")
ARCHIVEBOX_PUID = os.getenv("ARCHIVEBOX_PUID")
ARCHIVEBOX_PGID = os.getenv("ARCHIVEBOX_PGID")
ARCHIVEBOX_CMD_OPTIONS = os.getenv("ARCHIVEBOX_CMD_OPTIONS")

TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_new_bookmark() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_bookmark', NEW.url);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER = """
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'new_bookmark_trigger') THEN
        CREATE TRIGGER new_bookmark_trigger
        AFTER INSERT ON bookmark
        FOR EACH ROW
        EXECUTE FUNCTION notify_new_bookmark();
    END IF;
END $$;
"""


def initialize_database():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    cursor.execute(TRIGGER_FUNCTION)
    cursor.execute(CREATE_TRIGGER)
    conn.commit()
    cursor.close()
    conn.close()


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE_PATH), logging.StreamHandler()],
    )


def run_archivebox_add(url):
    logging.info(f"Adding URL to ArchiveBox: {url}")
    with open(URLS_FILE_PATH, "a") as file:
        file.write(f"{url}\n")
    client = docker.from_env()
    container = client.containers.get(ARCHIVEBOX_CONTAINER_NAME)
    stream = container.exec_run(
        f"archivebox add {ARCHIVEBOX_CMD_OPTIONS} {url}",
        user=f"{ARCHIVEBOX_PUID}:{ARCHIVEBOX_PGID}",
        environment={"CHROME_USER_DATA_DIR": None},
        stream=True,
    )
    for line in stream[1]:
        logging.info(line.decode("utf-8").strip())

    logging.info(f"Added {url}")
    # Clean up the file
    # with open(URLS_FILE_PATH, "w") as file:
    #     file.write("")


def main():
    ensure_directories()
    setup_logging()
    initialize_database()
    conn = psycopg2.connect(**DATABASE_CONFIG)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("LISTEN new_bookmark;")

    logging.info("Waiting for notifications on channel 'new_bookmark'")
    while True:
        select.select([conn], [], [])
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            url = notify.payload
            logging.info(f"Received URL: {url}")
            run_archivebox_add(url)


if __name__ == "__main__":
    main()
