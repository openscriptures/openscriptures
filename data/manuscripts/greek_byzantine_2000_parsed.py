#!/usr/bin/env python
# encoding: utf-8

msID = 5

import sys, os, re, unicodedata, urllib, zipfile, StringIO
from datetime import date
from django.core.management import setup_environ
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../')) #There's probably a better way of doing this
from openscriptures import settings
setup_environ(settings)
from openscriptures.data.unbound_bible import UNBOUND_CODE_TO_OSIS_CODE # Why does this have to be explicit?
from openscriptures.core.models import *
from openscriptures.data import import_helpers

# Abort if MS has already been added (and --force not supplied)
import_helpers.abort_if_imported(msID)

# Download the source file
source_url = "http://www.unboundbible.org/downloads/bibles/greek_byzantine_2000_parsed.zip"
import_helpers.download_resource(source_url)

import_helpers.delete_work(msID)
msWork = Work(
    id           = msID,
    title        = "Byzantine/Majority Text (2000)",
    description  = "Includes parsings",
    abbreviation = 'Byz-2000',
    language     = Language('grc'),
    type         = 'Bible',
    osis_slug    = 'Byzantine',
    publish_date = date(2000, 1, 1),
    originality  = 'manuscript-edition',
    creator      = "Maurice A. Robinson and William G. Pierpont.",
    url          = source_url,
    license      = License.objects.get(url="http://creativecommons.org/licenses/publicdomain/")
)
msWork.save()

# The followig regular epression identifies the parts of the following line:
# 40N	1	1		10	Βίβλος G976 N-NSF γενέσεως G1078 N-GSF Ἰησοῦ G2424 N-GSM χριστοῦ G5547 N-GSM , υἱοῦ G5207 N-GSM Δαυίδ G1138 N-PRI , υἱοῦ G5207 N-GSM Ἀβραάμ G11 N-PRI .
lineParser = re.compile(ur"""^
        (?P<book>\d+\w+)\t+         # Unbound Bible Code
        (?P<chapter>\d+)\t+         # Chapter
        (?P<verse>\d+)\t+           # Verse
        \d+\t+                      # Ignore orderby column
        (?P<data>.*?)
    \s*$""",
    re.VERBOSE
)

# Regular expression to parse each individual word on a line (the data group from above)
tokenParser = re.compile(ur"""
        (?P<word>\S+)\s+
        (?P<rawParsing>
            G?\d+
            (?:  \s+G?\d+  |  \s+[A-Z0-9\-:]+  )+
        )
        (?:\s+|$)
    """,
    re.VERBOSE | re.UNICODE)

bookRefs = []
chapterRefs = []
verseRefs = []
tokens = []
previousTokens = []
tokenPosition = 0

zip = zipfile.ZipFile(os.path.basename(source_url))
for verseLine in StringIO.StringIO(zip.read("greek_byzantine_2000_parsed_utf8.txt")):
    if(verseLine.startswith('#')):
        continue
    verseLine = unicodedata.normalize("NFC", unicode(verseLine, 'utf-8'))
    verseInfo = lineParser.match(verseLine)
    if(not verseInfo):
        raise Exception("Parse error on line: " + verseLine)
    if(not verseInfo.group('data') or UNBOUND_CODE_TO_OSIS_CODE[verseInfo.group('book')] not in OSIS_BIBLE_BOOK_CODES):
        continue
    meta = verseInfo.groupdict()
    
    # Create book ref if it doesn't exist
    if(not len(bookRefs) or bookRefs[-1].osis_id != UNBOUND_CODE_TO_OSIS_CODE[meta['book']]):
        print UNBOUND_CODE_TO_OSIS_CODE[meta['book']]
        
        # Reset tokens
        previousTokens = tokens
        tokens = []
        
        # Close book and chapter refs
        if(len(previousTokens)):
            bookRefs[-1].end_token = previousTokens[-1]
            bookRefs[-1].save()
            chapterRefs[-1].end_token = previousTokens[-1]
            chapterRefs[-1].save()
        chapterRefs = []
        verseRefs = []
        
        # Set up the book ref
        bookRef = Ref(
            work = msWork,
            type = Ref.BOOK,
            osis_id = UNBOUND_CODE_TO_OSIS_CODE[meta['book']],
            position = len(bookRefs),
            title = OSIS_BOOK_NAMES[UNBOUND_CODE_TO_OSIS_CODE[meta['book']]]
        )
        #bookRef.save()
        #bookRefs.append(bookRef)
        
    # So here we need to have tokenParser match the entire line
    pos = 0
    verseTokens = []
    while(pos < len(meta['data'])):
        tokenMatch = tokenParser.match(meta['data'], pos)
        if(not tokenMatch):
            #print "%s %02d %02d" % (verseInfo.group('book'), int(verseInfo.group('chapter')), int(verseInfo.group('verse')))
            raise Exception("Unable to parse at position " + str(pos) + ": " + meta['data'])
        
        # Insert token
        token = Token(
            data     = tokenMatch.group('word'),
            type     = Token.WORD,
            work     = msWork,
            position = tokenPosition
        )
        tokenPosition = tokenPosition + 1
        token.save()
        tokens.append(token)
        verseTokens.append(token)
        
        # Token Parsing
        parsing = TokenParsing(
            token = token,
            raw = tokenMatch.group('rawParsing'),
            language = Language('grc'),
            work = msWork
        )
        parsing.save()
        
        # Make this token the first in the book ref, and set the first token in the book
        if len(tokens) == 1:
            bookRef.start_token = tokens[0]
            bookRef.save()
            bookRefs.append(bookRef)
        
        # Set up the Chapter ref
        if(not len(chapterRefs) or chapterRefs[-1].numerical_start != meta['chapter']):
            if(len(chapterRefs)):
                chapterRefs[-1].end_token = tokens[-2]
                chapterRefs[-1].save()
            chapterRef = Ref(
                work = msWork,
                type = Ref.CHAPTER,
                osis_id = ("%s.%s" % (bookRefs[-1].osis_id, meta['chapter'])),
                position = len(chapterRefs),
                parent = bookRefs[-1],
                numerical_start = meta['chapter'],
                start_token = tokens[-1]
            )
            chapterRef.save()
            chapterRefs.append(chapterRef)
        
        pos = tokenMatch.end()
    
    # Create verse ref
    verseRef = Ref(
        work = msWork,
        type = Ref.VERSE,
        osis_id = ("%s.%s.%s" % (bookRefs[-1].osis_id, meta['chapter'], meta['verse'])),
        position = len(verseRefs),
        parent = chapterRefs[-1],
        numerical_start = meta['verse'],
        start_token = verseTokens[0],
        end_token = verseTokens[-1]
    )
    verseRef.save()
    verseRefs.append(verseRef)
    
#Close out the book and chapters
bookRefs[-1].end_token = tokens[-1]
bookRefs[-1].save()
chapterRefs[-1].end_token = tokens[-1]
for chapterRef in chapterRefs:
    chapterRef.save()



