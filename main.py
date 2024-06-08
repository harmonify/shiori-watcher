import os
import psycopg2
import select
import docker
import logging
import apprise
from logging.handlers import RotatingFileHandler


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
__ARCHIVEBOX_CMD_OPTIONS = os.getenv("ARCHIVEBOX_CMD_OPTIONS")
ARCHIVEBOX_CMD_OPTIONS = __ARCHIVEBOX_CMD_OPTIONS if __ARCHIVEBOX_CMD_OPTIONS is not None else ""
__APPRISE_URLS = os.getenv("APPRISE_URLS")
APPRISE_URLS = tuple(__APPRISE_URLS.split(" ")) if __APPRISE_URLS is not None else tuple()

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


def initialize_database(conn):
    cursor = conn.cursor()
    cursor.execute(TRIGGER_FUNCTION)
    cursor.execute(CREATE_TRIGGER)
    conn.commit()
    cursor.close()


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logging():
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=1,
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[file_handler, logging.StreamHandler()],
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


def execute():
    setup_logging()
    ensure_directories()

    conn = psycopg2.connect(**DATABASE_CONFIG)
    initialize_database(conn)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("LISTEN new_bookmark;")
    
    apobj = apprise.Apprise(APPRISE_URLS)

    logging.info("Now listening for new bookmarks...")
    while True:
        select.select([conn], [], [])
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            url = notify.payload
            logging.info(f"Received URL: {url}")
            try:
                run_archivebox_add(url)
                if len(apobj.servers) > 0:
                    apobj.notify(
                        title="Archived ✅",
                        body=url,
                    )
            except Exception as e:
                if len(apobj.servers) > 0:
                    apobj.notify(
                        title="Failed to archive ❌",
                        body=url,
                    )


def main():
    try:
        execute()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt. Exiting...")
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    main()
