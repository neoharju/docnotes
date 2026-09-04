# DocNotes (Proof-of-Concept)

Read and review research papers together!

## Application Features

- Users can create an account and log in to the application.
- Users can add, edit and delete their research paper information.
- Users can attach a PDF file to a research paper.
- Users can view research papers added to the application and read their PDF files.
- Users can classify their research papers (e.g. field, topic, ...)
- Users can search for research papers by keyword and tags.
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

Run the application with

```sh
flask run
```
