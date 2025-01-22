## usage 🎯

this script leverages **ghostscript** under the hood, using its `pdfwrite` device to optimize pdfs by downsampling images, stripping metadata, and re-encoding content for smaller file sizes.

### basic usage
compress all pdfs in a folder:
```bash
$ python compress.py /path/to/your/pdf/folder
```

### advanced options
- **dry run**: simulate compression without modifying files.
```bash
$ python compress.py /path/to/your/pdf/folder --dry-run
```

- **max threads**: limit the number of concurrent threads.
```bash
$ python compress.py /path/to/your/pdf/folder --max-threads 4
```

- **min size**: skip files smaller than the specified size (in mb).
```bash
$ python compress.py /path/to/your/pdf/folder --min-size 10
```

- **log file**: save output to a log file.
```bash
$ python compress.py /path/to/your/pdf/folder --log-file output.log
```

- **verbose mode**: enable detailed output.
```bash
$ python compress.py /path/to/your/pdf/folder --verbose
```
