"""Write the last inline <script> of a page to a .js file (for node --check). python extract_js.py <page.html> <out.js>"""
import re, sys
h = open(sys.argv[1]).read(); m = re.findall(r'<script>(.*?)</script>', h, re.S)
open(sys.argv[2], 'w').write(m[-1]); print(sys.argv[1], len(h) // 1024, 'kB')
