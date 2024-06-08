# Bookmark Watcher with ArchiveBox and Go-Shiori

_NOTE: The app currently only supports for Go-Shiori installation with PostgreSQL database._

This project integrates [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) and [Go-Shiori](https://github.com/go-shiori/shiori) by creating a lightweight Docker container that watches a [PostgreSQL](https://www.postgresql.org/) database for new entries in the `bookmarks` table used by [Go-Shiori](https://github.com/go-shiori/shiori). When new entries are added, the container fetches the URLs and adds them to [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) for archiving.

## Notes

For best experience, it is recommended to try install the [Go-Shiori Web Extension](https://github.com/go-shiori/shiori-web-ext) in your browser and configure the key binding to easily store your bookmark.

## Prerequisites

- Docker
- Docker Compose

## Usage

### Step 1: Clone the Repository

```bash
git clone https://github.com/harmonify/shiori-watcher.git
cd shiori-watcher
```

### Step 2: Set up .env file

Copy the `.env.example` file and make adjustments

```bash
cp .env.example .env
```

Refer to the [Configuration](#configuration) section to configure the watcher service.

### Step 3: Build and Run the Docker Containers

Build and start the Docker containers using Docker Compose:

```bash
docker compose up --build
```

This will start the following services:

- **PostgreSQL**: PostgreSQL database for storing bookmarks.
- **ArchiveBox**: Service for archiving URLs.
- **Go-Shiori**: Bookmark manager.
- **Watcher**: Service that watches the bookmarks table and triggers ArchiveBox for new URLs.

### Configuration

The watcher service uses the following environment variables for configuration:

- `DATA_DIR`: Directory for storing temporary URL files (default: `/data`).
- `LOGS_DIR`: Directory for storing log files (default: `/logs`).
- `DB_NAME`: Name of the PostgreSQL database (default: `mydb`).
- `DB_USER`: PostgreSQL user (default: `myuser`).
- `DB_PASSWORD`: PostgreSQL password (default: `mypassword`).
- `DB_HOST`: PostgreSQL host (default: `postgres`).
- `DB_PORT`: PostgreSQL port (default: `5432`).
- `ARCHIVEBOX_CONTAINER_NAME`: Name of the ArchiveBox container (default: `archivebox`).
- `ARCHIVEBOX_PUID`: PUID of the ArchiveBox container
- `ARCHIVEBOX_PGID`: PGID of the ArchiveBox container
- `ARCHIVEBOX_CMD_OPTIONS`: Raw string provided into ArchiveBox CLI inside of its container
- `APPRISE_URLS`: Space separated push notification service URLs. See <https://github.com/caronc/apprise/wiki> for more information.

## Contributing

Contributions are welcome! Follow these steps to contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes and push your branch to GitHub.
4. Open a pull request describing your changes.

### Development Setup

To set up a development environment:

1. Clone the repository:

   ```bash
   git clone https://github.com/harmonify/shiori-watcher.git
   cd shiori-watcher
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the watcher script locally:

   ```bash
   python main.py
   ```

Ensure you have a PostgreSQL instance running and accessible with the required database and table set up by Go-Shiori.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
