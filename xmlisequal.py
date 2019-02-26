"""Module for checking whether two XML records are the same. Ignores
comments and stray whitespace.

>>> import xmlisequal
>>> xml1 = "<xml><mytag>Hello</mytag><mytag>World</mytag></xml><!-- my comment-->"
>>> xml2 = "<xml> <mytag>Hello</mytag> <mytag>World</mytag> </xml>"
>>> xmlisequal.xmlIsEqual(xml1, xml2)
True
>>>

Doe NOT ignore differences in order:

>>> import xmlisequal
>>> xml1 = "<xml> <mytag>Hello</mytag> <mytag>World</mytag> </xml>"
>>> xml2 = "<xml> <mytag>World</mytag> <mytag>Hello</mytag> </xml>"
>>> xmlisequal.xmlIsEqual(xml1, xml2)
False
>>> 

"""
from xmldiff import main as xmldiffmain
import xmldiff
import re
import logging

def xmlIsEqual(old, new, pid=''):
    diff = xmldiffmain.diff_texts(old, new, diff_options={'F': 0.5, 'ratio_mode': 'fast'})
    diffFiltered = []
    for difference in diff:
        if type(difference) is xmldiff.diff.InsertComment:
            logging.debug("Comment, ignore this one %s" % str(difference))
        elif type(difference) is xmldiff.diff.UpdateTextIn:
            # Is this a for-reals difference or just some stray whitespace?
            if difference.text is not None:
                textNoWhiteSpace = re.sub(r'\s+', '', difference.text)
                if len(textNoWhiteSpace) > 0:
                    logging.debug("Difference is not just stray whitespace, adding %s" % str(difference))
                    diffFiltered.append(difference)
                else:
                    logging.debug("Stray whitespace, ignore this one %s" % str(difference))
            else:
                logging.debug("Difference is None, ignore this one %s" % str(difference))
        else:
            logging.debug("This one didn't match any of my filters, adding %s" % str(difference))
            diffFiltered.append(difference)

    if len(diffFiltered) > 0:
        for difference in diffFiltered:
            logging.info("Difference %s: %s" % (pid,str(difference)))
        return False
    else:
        return True

if __name__ == "__main__":
    import doctest
    doctest.testmod()
