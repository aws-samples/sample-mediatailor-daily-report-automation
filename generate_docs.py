#!/usr/bin/env python3
"""
Generate PDF documentation from markdown files.
Usage: python generate_docs.py [--output-dir OUTPUT_DIR] [--customer-guide-only]
"""

import argparse
import sys
from pathlib import Path
from markdown import markdown
from weasyprint import HTML


def generate_pdf(md_file: Path, output_dir: Path) -> None:
    """Convert markdown file to PDF with professional styling."""
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html_body = markdown(md_content, extensions=['fenced_code', 'tables', 'nl2br'])
    
    # Add content-start class to first h2 after ToC (Overview section)
    html_body = html_body.replace('<h2 id="overview">Overview</h2>', 
                                   '<h2 id="overview" class="content-start">Overview</h2>')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            @page :first {{
                margin: 0;
                @bottom-right {{
                    content: none;
                }}
            }}
            @page content {{
                @bottom-right {{
                    content: "Page " counter(page);
                    font-size: 9pt;
                    color: #666;
                }}
            }}
            .title-page {{
                page: first;
                text-align: center;
            }}
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #232F3E;
                font-size: 11pt;
            }}
            h1 {{
                color: #232F3E;
                border-bottom: 3px solid #FF9900;
                padding-bottom: 10px;
                margin-top: 30px;
                margin-bottom: 20px;
                font-size: 24pt;
                page-break-after: avoid;
            }}
            h2 {{
                color: #232F3E;
                border-bottom: 1px solid #FF9900;
                padding-bottom: 5px;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 18pt;
                page-break-after: avoid;
            }}
            h3 {{
                color: #146EB4;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 14pt;
                page-break-after: avoid;
            }}
            h4 {{
                color: #232F3E;
                margin-top: 15px;
                margin-bottom: 8px;
                font-size: 12pt;
                font-weight: bold;
            }}
            p {{
                margin: 10px 0;
                text-align: justify;
            }}
            code {{
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                color: #c7254e;
            }}
            pre {{
                background: #f8f8f8;
                border: 1px solid #ddd;
                border-left: 3px solid #FF9900;
                padding: 15px;
                border-radius: 4px;
                overflow-x: auto;
                margin: 15px 0;
                page-break-inside: avoid;
                word-wrap: break-word;
                white-space: pre-wrap;
            }}
            pre code {{
                background: none;
                padding: 0;
                color: #232F3E;
                font-size: 8.5pt;
                word-wrap: break-word;
                white-space: pre-wrap;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
                page-break-inside: avoid;
            }}
            th {{
                background: #232F3E;
                color: white;
                padding: 10px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
            tr:nth-child(even) {{
                background: #f9f9f9;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            li {{
                margin: 5px 0;
            }}
            blockquote {{
                border-left: 4px solid #FF9900;
                padding-left: 15px;
                margin: 15px 0;
                color: #666;
                font-style: italic;
            }}
            hr {{
                border: none;
                border-top: 2px solid #FF9900;
                margin: 30px 0;
            }}
            .page-break {{
                page-break-before: always;
            }}
            .content-start {{
                page: content;
                counter-reset: page 1;
            }}
            strong {{
                color: #232F3E;
                font-weight: bold;
            }}
            a {{
                color: #146EB4;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    output_file = output_dir / f"{md_file.stem}.pdf"
    HTML(string=html_content).write_pdf(output_file)
    print(f"Generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate PDF documentation')
    parser.add_argument('--output-dir', default='docs/pdf', help='Output directory for PDFs')
    parser.add_argument('--customer-guide-only', action='store_true', 
                       help='Generate only the customer installation guide')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine which files to generate
    if args.customer_guide_only:
        md_files = [Path('docs/INSTALLATION_GUIDE.md')]
        print("Generating customer installation guide...")
    else:
        docs_dir = Path('docs')
        md_files = list(docs_dir.glob('*.md')) + [Path('README.md')]
        print("Generating all documentation...")
    
    if not md_files:
        print("No markdown files found")
        sys.exit(1)
    
    generated_count = 0
    for md_file in md_files:
        if md_file.exists():
            generate_pdf(md_file, output_dir)
            generated_count += 1
    
    print(f"\n✓ Successfully generated {generated_count} PDF document(s) in {output_dir}")
    
    if args.customer_guide_only:
        print(f"\n📄 Customer Installation Guide: {output_dir}/INSTALLATION_GUIDE.pdf")


if __name__ == '__main__':
    main()
