# Invoice renamer

This script processes a folder of images and PDF files, extracts the company name and the amount charged using the GPT-4O, and renames the files accordingly. It can handle both image files (JPEG, PNG) and PDF files.

## Prerequisites

- Python 3.6+
- OpenAI API key

## Installation

1. Clone the repository or download the script files.
2. Navigate to the project directory.
3. Install the required packages:

```sh
pip install -r requirements.txt
```

4. Set your OpenAI API key as an environment variable:

```sh
export OPENAI_API_KEY='your_openai_api_key'
```

## Usage

1. Run the script:

```sh
python invoice_processing.py ./invoices_April
```

## Notes

- Ensure the OpenAI API key is set in your environment variables.
- The script processes all image and PDF files in the specified folder.
- The filenames will be formatted as `CompanyName -- Amount.pdf`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
