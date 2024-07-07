# gitpy

**gitpy** is a Python clone of the Git version control system, implemented from scratch. This project aims to provide a deeper understanding of how Git works internally by replicating its core features.

## Features

`gitpy` implements the following Git features:

- **init**: Initialize a new, empty repository.
- **hash-object**: Compute and store the object ID for a file.
- **cat-file**: Display the content of an object.
- **add**: Add file contents to the index.
- **ls-files**: Show information about files in the index and the working directory.
- **commit**: Record changes to the repository.
- **checkout**: Switch branches or restore working tree files.
- **status**: Show the working tree status.
- **tag**: Create, list, delete or verify a tag object.
- **branch**: List, or create branches.
- **switch**: Switch branches.
- **config**: add local or global repo config

## Command Spelling Check

`gitpy` includes a spelling check feature for commands entered using the Levenshtein distance algorithm. This helps in detecting and suggesting corrections for misspelled commands.

## Project Outcomes

- Gain a comprehensive understanding of Git and its internal mechanisms.
- Learn how to implement version control functionalities from scratch using Python.
- Enhance problem-solving and coding skills through a practical, hands-on project.

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1. Clone the repository:
   
   ```sh
   git clone https://github.com/yourusername/gitpy.git
   ```
2. Navigate to the project directory:
   
   ```sh
   cd gitpy
   ```

### Usage

Initialize a new repository:

```sh
python gitpy.py init
```
