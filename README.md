# DocNotes

Read and review research papers together!


## Application Features

- Users can create an account and log in to the application.
- Users can add, edit and delete their research paper information.
- Users can attach a PDF file to a research paper.
- Users can view research papers added to the application as PDF files.
- Users can classify their research papers (e.g. field, topic, ...)
- Users can search for research papers by keyword, title, username.
- Users have profile pages that display statics and research papers they have added.
- Users can add comments to their own and others users' research papers.

## Installation

Minimal requirements:

```sh
sudo apt install sqlite3
pip install flask
```

Generate the database:

```sh

sqlite3 database.db < schema.sql
```
Create a `SECRET_KEY` into environment

```sh
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(256))')"
```

Run the application with

```sh
flask run
```

## Data simulation

Use `seed.py` to fill the database with 1 000 users, 100 000 PDFs (with keywords
and classifications) and 1 000 000 comments.

```sh
python3 seed.py
```

With simulated data the Measured Largest Contentful Paint (LCP) seems to max out at 0.24s when hosted locally.

## Code quality

The Pylint report can be found here
[pylint-report.md](pylint-report.md).
