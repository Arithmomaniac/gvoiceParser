##gvoiceParser
####a parser for Google Voice Takeout data<br>0.5.0 (2013-12-26)<br>&copy; 2011-2013 Avi Levin, under LGPL v2.1
----

The gvoiceParser project aims to make the thousands of tiny files generated from [Google Voice Takeout][1] more useful. This effort consists of three parts:

 1. A Python library for interpreting the HTML files *(mostly working)*
 2. A SQLite database containing the contents of all the HTML files
 3. A CSV generator based on the SQLite database.

gvoiceParser is a rewrite of my previous [googlevoice-to-sqlite][2] script. Ultimately, gvoiceParser will have feature parity with googlevoice-to-sqlite with more pythonic syntax and packaging.

Note that this is currently a Python 2.7 script, with dependencies on `dateutil` and `html5lib`.
 


  [1]: https://www.google.com/settings/takeout
  [2]: https://code.google.com/p/googlevoice-to-sqlite/