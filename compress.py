import os
import time
import subprocess
import csv
import signal
import sys
from multiprocessing import Pool, cpu_count
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
import argparse

# rich console for fancy output
console = Console()

# config stuff, feel free to tweak
GS_COMMAND = 'gswin64c'  # ghostscript command, adjust if you're on linux/mac
PDF_SETTINGS = '/screen'  # compression level, can try /ebook, /printer, /prepress
REPORT_FILE = 'compression_report.csv'  # csv report file name
HTML_REPORT_FILE = 'compression_report.html'  # html report file name
MAX_RAM_GB = 15  # max ram to use for ghostscript, in GB
GS_MEMORY_SETTINGS = [
    f'-dBufferSpace={int(MAX_RAM_GB * 0.8 * 1024 * 1024 * 1024)}',  # 80% of max ram for buffer
    f'-dMaxBitmap={int(MAX_RAM_GB * 0.2 * 1024 * 1024 * 1024)}',  # 20% of max ram for bitmap
    '-dNumRenderingThreads=4',  # use 4 threads for rendering
]
stop_execution = False  # global flag to handle ctrl+c

# handle ctrl+c like a pro
def signal_handler(sig, frame):
    global stop_execution
    console.print("\n[INFO] ctrl+c detected. stopping gracefully...", style="bold yellow")
    stop_execution = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# dump results into a csv file
def create_csv_report(report_file, data):
    fieldnames = ['File Name', 'Original Size (MB)', 'Compressed Size (MB)', 'Size Reduction (%)', 'Time Taken (seconds)']
    if not os.path.exists(report_file):  # create file with headers if it doesn't exist
        with open(report_file, mode='w', newline='') as file:
            csv.DictWriter(file, fieldnames=fieldnames).writeheader()
    with open(report_file, mode='a', newline='') as file:  # append data to the csv
        csv.DictWriter(file, fieldnames=fieldnames).writerows(data)

# generate a simple html report
def create_html_report(html_file, data):
    html_content = '''
    <html>
    <head>
        <title>PDF Compression Report</title>
        <style>
            table { width: 100%; border-collapse: collapse; }
            table, th, td { border: 1px solid black; }
            th, td { padding: 8px; text-align: left; }
        </style>
    </head>
    <body>
        <h2>PDF Compression Report</h2>
        <table>
            <tr>
                <th>File Name</th>
                <th>File Location</th>
                <th>Original Size (MB)</th>
                <th>Compressed Size (MB)</th>
                <th>Size Reduction (%)</th>
                <th>Time Taken (seconds)</th>
                <th>Compressed PDF</th>
            </tr>
    '''
    for entry in data:  # add a row for each compressed file
        html_content += f'''
        <tr>
            <td>{entry['File Name']}</td>
            <td>{entry['File Location']}</td>
            <td>{entry['Original Size (MB)']}</td>
            <td>{entry['Compressed Size (MB)']}</td>
            <td>{entry['Size Reduction (%)']}</td>
            <td>{entry['Time Taken (seconds)']}</td>
            <td><a href="{entry['Compressed PDF']}">Download</a></td>
        </tr>
        '''
    html_content += '</table></body></html>'  # close the html tags
    with open(html_file, 'w') as file:  # write the html content to a file
        file.write(html_content)

# compress a single pdf using ghostscript
def compress_pdf_with_ghostscript(file_path, dry_run=False):
    if stop_execution:  # stop if ctrl+c was pressed
        return None
    start_time = time.time()  # start the timer
    original_size = os.path.getsize(file_path)  # get the original file size
    original_size_mb = original_size / (1024 * 1024)  # convert to MB
    compressed_file_path = file_path.replace('.pdf', '_compressed.pdf')  # output file path

    if dry_run:  # simulate compression if dry run is enabled
        console.print(f"[DRY RUN] simulating compression for: {file_path}", style="bold blue")
        return {
            'File Name': os.path.basename(file_path),
            'File Location': file_path,
            'Original Size (MB)': f"{original_size_mb:.2f}",
            'Compressed Size (MB)': f"{original_size_mb * 0.8:.2f}",  # simulate 20% reduction
            'Size Reduction (%)': "20.00",
            'Time Taken (seconds)': "0.00",
            'Compressed PDF': f"file://{os.path.abspath(file_path)}"
        }

    # ghostscript command to compress the pdf
    gs_command = [
        GS_COMMAND,
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',  # pdf version
        f'-dPDFSETTINGS={PDF_SETTINGS}',  # compression settings
        '-dNOPAUSE',  # no pause after each page
        '-dQUIET',  # suppress output
        '-dBATCH',  # process all pages
        '-sOutputFile=' + compressed_file_path,  # output file path
        file_path  # input file path
    ] + GS_MEMORY_SETTINGS  # add memory optimization settings

    subprocess.run(gs_command, check=True)  # run the ghostscript command
    new_size = os.path.getsize(compressed_file_path)  # get the compressed file size
    new_size_mb = new_size / (1024 * 1024)  # convert to MB
    size_reduction_percentage = 100 * (1 - new_size / original_size)  # calculate size reduction

    if new_size > original_size:  # warn if compression increased file size
        console.print(f"[WARNING] compression of {file_path} increased the file size.", style="bold yellow")
        console.print(f"    original size: {original_size_mb:.2f} MB", style="yellow")
        console.print(f"    compressed size: {new_size_mb:.2f} MB (larger than original!)", style="yellow")
        console.print(f"    skipping file.", style="yellow")
        os.remove(compressed_file_path)  # delete the compressed file
        return None

    time_taken = time.time() - start_time  # calculate time taken
    os.replace(compressed_file_path, file_path)  # replace the original file with the compressed one

    console.print(f"\n[INFO] compression complete for: {file_path}", style="bold green")
    console.print(f"    original size: {original_size_mb:.2f} MB", style="green")
    console.print(f"    compressed size: {new_size_mb:.2f} MB", style="green")
    console.print(f"    size reduction: {size_reduction_percentage:.2f}%", style="green")
    console.print(f"    time taken: {time_taken:.2f} seconds", style="green")

    return {
        'File Name': os.path.basename(file_path),
        'File Location': file_path,
        'Original Size (MB)': f"{original_size_mb:.2f}",
        'Compressed Size (MB)': f"{new_size_mb:.2f}",
        'Size Reduction (%)': f"{size_reduction_percentage:.2f}",
        'Time Taken (seconds)': f"{time_taken:.2f}",
        'Compressed PDF': f"file://{os.path.abspath(file_path)}"
    }

# compress all pdfs in a directory
def compress_pdfs_in_directory(directory, report_file=REPORT_FILE, html_report_file=HTML_REPORT_FILE, dry_run=False, max_threads=None, min_size=0, log_file=None, verbose=False):
    if log_file:  # redirect output to a log file if specified
        sys.stdout = open(log_file, 'w')

    # find all pdf files in the directory and subdirectories
    pdf_files = [os.path.join(root, file) for root, _, files in os.walk(directory) for file in files if file.lower().endswith('.pdf') and os.path.getsize(os.path.join(root, file)) / (1024 * 1024) >= min_size]

    if not pdf_files:  # exit if no pdfs are found
        console.print("[INFO] no pdf files found to compress.", style="bold yellow")
        return

    results = []  # store compression results
    with Progress(TextColumn("[bold blue]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn(), transient=True) as progress:
        task = progress.add_task("[cyan]compressing pdfs...", total=len(pdf_files))  # progress bar
        with Pool(max_threads or cpu_count()) as pool:  # use multiprocessing
            for result in pool.imap(lambda f: compress_pdf_with_ghostscript(f, dry_run), pdf_files):
                if result:
                    results.append(result)
                progress.update(task, advance=1)  # update progress bar

    create_csv_report(report_file, results)  # generate csv report
    create_html_report(html_report_file, results)  # generate html report
    console.print(f"\n[INFO] compression complete. reports saved to {report_file} and {html_report_file}.", style="bold green")

    # display results in a table
    table = Table(title="Compression Results", show_header=True, header_style="bold magenta")
    table.add_column("File Name", style="dim")
    table.add_column("Original Size (MB)", justify="right")
    table.add_column("Compressed Size (MB)", justify="right")
    table.add_column("Size Reduction (%)", justify="right")
    table.add_column("Time Taken (s)", justify="right")
    for entry in results:
        table.add_row(entry['File Name'], entry['Original Size (MB)'], entry['Compressed Size (MB)'], entry['Size Reduction (%)'], entry['Time Taken (seconds)'])
    console.print(table)

# main entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="compress pdfs in a directory using ghostscript.")
    parser.add_argument('directory', help="directory containing pdfs to compress")
    parser.add_argument('--dry-run', action='store_true', help="simulate compression without modifying files")
    parser.add_argument('--max-threads', type=int, help="max number of concurrent threads")
    parser.add_argument('--min-size', type=int, default=0, help="min file size (in MB) to process")
    parser.add_argument('--log-file', help="log file to save output")
    parser.add_argument('--verbose', action='store_true', help="enable verbose output")
    args = parser.parse_args()
    compress_pdfs_in_directory(args.directory, dry_run=args.dry_run, max_threads=args.max_threads, min_size=args.min_size, log_file=args.log_file, verbose=args.verbose)