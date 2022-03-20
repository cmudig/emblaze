<%!
    # Set the style keyword such as 'atom-one-light' or 'github-gist'
    #     Options: https://github.com/highlightjs/highlight.js/tree/master/src/styles
    #     Demo: https://highlightjs.org/static/demo/
    hljs_style = 'github'

    # Enable offline search using Lunr.js. For explanation of 'fuzziness' parameter, which is
    # added to every query word, see: https://lunrjs.com/guides/searching.html#fuzzy-matches
    # If 'index_docstrings' is False, a shorter index is built, indexing only
    # the full object reference names.
    lunr_search = {'fuzziness': 1, 'index_docstrings': True}
    # lunr_search = None

    # If set, render LaTeX math syntax within \(...\) (inline equations),
    # or within \[...\] or $$...$$ or `.. math::` (block equations)
    # as nicely-formatted math formulas using MathJax.
    # Note: in Python docstrings, either all backslashes need to be escaped (\\)
    # or you need to use raw r-strings.
    latex_math = False
%>