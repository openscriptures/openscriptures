#!/usr/bin/env python
# encoding: utf-8

import re, unicodedata, os, urllib, sys
from openscriptures.core.models import *

def normalize_token(data):
    "Normalize to Unicode NFC, strip out all diacritics, apostrophies, and make lower-case."
    # credit: http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string
    data = unicodedata.normalize('NFC', ''.join((c for c in unicodedata.normalize('NFD', data) if unicodedata.category(c) != 'Mn')).lower())
    data = data.replace(r'\s+', ' ')
    #data = re.sub(ur"['’]", '', data)
    data = data.replace(u"'", '')
    data = data.replace(u"’", '')
    return data

def download_resource(source_url):
    "Download the file in the provided URL if it does not already exist in the working directory."
    if(not os.path.exists(os.path.basename(source_url))):
        if(not os.path.exists(os.path.basename(source_url))):
            print "Downloading " + source_url
            urllib.urlretrieve(source_url, os.path.basename(source_url))


def abort_if_imported(workID):
    "Shortcut see if the provided work ID already exists in the system; if so, then abort unless --force command line argument is supplied"
    if(len(Work.objects.filter(id=workID)) and not (len(sys.argv)>1 and sys.argv[1] == '--force')):
        print " (already imported; pass --force option to delete existing work and reimport)"
        exit()

def delete_work(msID, *varMsIDs):
    "Deletes a work without a greedy cascade"
    tokens = Token.objects.filter(work=msID)
    for token in tokens:
        token.variant_groups.clear()
    tokens.update(unified_token=None)
    
    for varMsID in varMsIDs:
        #VariantGroupToken.objects.filter(work=varMsID).update()
        # delete all VariantGroupTokens which are associated with 
        #VariantGroup.objects.filter(work=varMsID).delete()
        Work.objects.filter(id=varMsID).update(unified=None, base=None)
        Work.objects.filter(id=varMsID).delete()
    
    VariantGroup.objects.filter(work=msID).delete()
    Work.objects.filter(id=msID).update(unified=None)
    Work.objects.filter(id=msID).delete()